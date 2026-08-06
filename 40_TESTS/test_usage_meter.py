#!/usr/bin/env python3
"""WireGuard 누적 카운터→v2 지갑·세션 영수증 연결 검사."""
from __future__ import annotations

import base64
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_api import ControlAPI  # noqa: E402
from app.usage_meter import UsageRejected  # noqa: E402
from app.wallet_ledger import FREE_CAP_BYTES  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
SERVER_KEY = base64.b64encode(bytes(range(32))).decode("ascii")
CLIENT_KEY = base64.b64encode(bytes(range(32, 64))).decode("ascii")


class UsageMeterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_usage_meter_")
        self.path = pathlib.Path(self.temp.name) / "control.sqlite3"

        def provisioner(account_id, device_id, public_key, server):
            return {"assigned_address": "10.64.0.2/32"}

        self.api = ControlAPI(self.path, peer_provisioner=provisioner)
        self.api.catalog.register_verified_server(
            server_id="de-fra-01", country_code="DE", country="Germany", city="Frankfurt",
            provider_ref="provider-a", exit_ip="8.8.8.8", endpoint="vpn.example.test:51820",
            wg_public_key=SERVER_KEY, dns_addresses=["1.1.1.1"], health="healthy",
            capacity_percent=20, contract_active=True, provisioned=True, exit_verified=True,
            measured_at=NOW, verified_at=NOW,
        )
        claim = self.api.provision_claim("acct_meter_001", now=NOW)["claim"]
        token = self.api.handle("POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW).body["access_token"]
        device = self.api.handle(
            "POST", "/v1/devices", headers={"Authorization": f"Bearer {token}"},
            body={"wg_public_key": CLIENT_KEY, "server_id": "de-fra-01"}, now=NOW,
        )
        self.token = token
        self.device_id = device.body["device_id"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def ingest(self, event_id, epoch, rx, tx):
        return self.api.ingest_usage_counter(
            event_id=event_id, node_id="node-de-01", device_id=self.device_id,
            epoch=epoch, rx_bytes=rx, tx_bytes=tx, observed_at=NOW,
        )

    def test_first_sample_is_baseline_then_only_growth_is_charged(self):
        baseline = self.ingest("sample-001", 1, 100, 200)
        charged = self.ingest("sample-002", 1, 150, 250)
        self.assertTrue(baseline["baseline"])
        self.assertEqual(baseline["charged_bytes"], 0)
        self.assertEqual(charged["observed_delta_bytes"], 100)
        self.assertEqual(charged["charged_bytes"], 100)
        self.assertEqual(charged["balances"]["free"], FREE_CAP_BYTES - 100)

    def test_duplicate_event_is_idempotent_across_restart(self):
        self.ingest("sample-dupe-base", 1, 0, 0)
        first = self.ingest("sample-dupe", 1, 50, 50)
        reopened = ControlAPI(self.path)
        second = reopened.ingest_usage_counter(
            event_id="sample-dupe", node_id="node-de-01", device_id=self.device_id,
            epoch=1, rx_bytes=50, tx_bytes=50, observed_at=NOW,
        )
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["balances"], second["balances"])

    def test_same_counter_sample_with_new_event_id_is_not_charged_twice(self):
        self.ingest("sample-payload-base", 1, 0, 0)
        first = self.ingest("sample-payload-a", 1, 40, 60)
        second = self.ingest("sample-payload-b", 1, 40, 60)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertTrue(second["duplicate_sample"])
        self.assertEqual(first["balances"], second["balances"])

    def test_same_event_id_with_different_payload_is_rejected(self):
        self.ingest("sample-collision", 1, 0, 0)
        with self.assertRaises(UsageRejected):
            self.ingest("sample-collision", 1, 1, 0)

    def test_same_epoch_counter_decrease_is_rejected_without_charge(self):
        self.ingest("sample-high", 1, 100, 100)
        before = self.api.wallet.snapshot("acct_meter_001", now=NOW)["balances"]
        with self.assertRaises(UsageRejected):
            self.ingest("sample-lower", 1, 99, 100)
        after = self.api.wallet.snapshot("acct_meter_001", now=NOW)["balances"]
        self.assertEqual(before, after)

    def test_new_epoch_charges_new_counter_from_zero(self):
        self.ingest("sample-epoch-base", 1, 500, 500)
        restarted = self.ingest("sample-epoch-2", 2, 10, 20)
        self.assertEqual(restarted["observed_delta_bytes"], 30)
        self.assertEqual(restarted["charged_bytes"], 30)

    def test_excess_traffic_charges_available_then_blocks_without_negative_balance(self):
        self.ingest("sample-exhaust-base", 1, 0, 0)
        result = self.ingest("sample-exhaust", 1, FREE_CAP_BYTES, 100)
        self.assertEqual(result["charged_bytes"], FREE_CAP_BYTES)
        self.assertEqual(result["unbilled_bytes"], 100)
        self.assertTrue(result["blocked"])
        self.assertEqual(sum(result["balances"].values()), 0)

    def test_usage_route_aggregates_poll_events_into_one_session(self):
        self.ingest("sample-session-base", 7, 0, 0)
        self.ingest("sample-session-a", 7, 20, 30)
        self.ingest("sample-session-b", 7, 50, 70)
        response = self.api.handle(
            "GET", "/v1/usage", headers={"Authorization": f"Bearer {self.token}"}, now=NOW
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.body["sessions"]), 1)
        self.assertEqual(response.body["sessions"][0]["charged_bytes"], 120)
        self.assertEqual(response.body["monthly_total_bytes"], 120)

    def test_storage_failure_is_fail_closed_before_charging(self):
        before = self.api.wallet.snapshot("acct_meter_001", now=NOW)["balances"]
        with mock.patch.object(self.api.usage_meter, "_connect", side_effect=OSError("blocked")):
            result = self.ingest("sample-storage-fail", 1, 10, 10)
        after = self.api.wallet.snapshot("acct_meter_001", now=NOW)["balances"]
        self.assertFalse(result["applied"])
        self.assertTrue(result["blocked"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UsageMeterTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"사용량 계측 연결 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
