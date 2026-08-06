#!/usr/bin/env python3
"""strict SSH exit 어댑터와 제어 API 실제 연결 계약 검사."""
from __future__ import annotations

import base64
import json
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_api import ControlAPI  # noqa: E402
from app.ssh_node_adapter import NodeAdapterError, SSHNodeAdapter, SSHNodeSpec  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
SERVER_KEY = base64.b64encode(bytes(range(32))).decode("ascii")
CLIENT_KEY = base64.b64encode(bytes(range(32, 64))).decode("ascii")
ACCOUNT = "a" * 64


class FakeSSH:
    def __init__(self):
        self.commands: list[list[str]] = []
        self.counter_total = 0
        self.fail = False
        self.key_match = True
        self.include_measured_at = True
        self.measured_at = NOW

    def __call__(self, command):
        self.commands.append(command)
        if self.fail:
            return subprocess.CompletedProcess(command, 23, "", "secret-like remote error")
        parts = shlex.split(command[-1])
        if "health" in parts:
            payload = {
                "node_id": "exit-de-01",
                "health": "healthy",
                "failures": "",
                "server_public_key": SERVER_KEY if self.key_match else CLIENT_KEY,
            }
            if self.include_measured_at:
                payload["measured_at"] = self.measured_at.isoformat()
        elif "provision" in parts:
            device_id = parts[parts.index("--device-id") + 1]
            payload = {
                "applied": True,
                "node_id": "exit-de-01",
                "device_id": device_id,
                "assigned_address": "10.66.0.2/32",
                "runtime_confirmed": True,
            }
        elif "revoke" in parts:
            device_id = parts[parts.index("--device-id") + 1]
            payload = {
                "applied": True,
                "node_id": "exit-de-01",
                "device_id": device_id,
                "runtime_confirmed": True,
            }
        elif "counters" in parts:
            payload = {
                "node_id": "exit-de-01",
                "observed_at": NOW.isoformat(),
                "samples": [
                    {
                        "device_id": self.device_id,
                        "epoch": 101,
                        "rx_bytes": self.counter_total // 2,
                        "tx_bytes": self.counter_total - self.counter_total // 2,
                        "handshake_at": NOW.isoformat(),
                    }
                ],
            }
        else:
            raise AssertionError(parts)
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")


class SSHNodeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_ssh_adapter_")
        root = pathlib.Path(self.temp.name)
        self.db = root / "control.sqlite3"
        identity = root / "id_ed25519"
        known_hosts = root / "known_hosts"
        identity.write_text("test-placeholder-not-used", encoding="ascii")
        known_hosts.write_text("vpn.example.test ssh-ed25519 test", encoding="ascii")
        self.spec = SSHNodeSpec(
            server_id="de-fra-01", node_id="exit-de-01", host="vpn.example.test",
            ssh_user="freeflex", ssh_port=22, identity_file=identity,
            known_hosts_file=known_hosts, country_code="DE", country="Germany",
            city="Frankfurt", provider_ref="provider-a", exit_ip="8.8.8.8",
            endpoint="vpn.example.test:51820", server_public_key=SERVER_KEY,
            dns_addresses=("1.1.1.1",), exit_verified=True, verified_at=NOW,
            capacity_percent=20,
        )
        self.fake = FakeSSH()
        self.adapter = SSHNodeAdapter(self.db, [self.spec], runner=self.fake)
        self.api = ControlAPI(
            self.db, peer_provisioner=self.adapter.provision, peer_revoker=self.adapter.revoke
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def session(self):
        claim = self.api.provision_claim(ACCOUNT, now=NOW)["claim"]
        return self.api.handle("POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW).body["access_token"]

    def create_device(self):
        self.adapter.poll_health(self.api, now=NOW)
        token = self.session()
        response = self.api.handle(
            "POST", "/v1/devices", headers={"Authorization": f"Bearer {token}"},
            body={"wg_public_key": CLIENT_KEY, "server_id": "de-fra-01"}, now=NOW,
        )
        self.assertEqual(response.status, 201)
        self.fake.device_id = response.body["device_id"]
        return token, response.body["device_id"]

    def test_health_registers_only_matching_verified_node(self):
        result = self.adapter.poll_health(self.api, now=NOW)
        catalog = self.api.catalog.public_catalog(now=NOW)
        self.assertTrue(result[0]["healthy"])
        self.assertEqual(catalog["available_count"], 1)
        self.assertNotIn("exit_ip", catalog["servers"][0])

    def test_server_key_mismatch_hides_catalog_negative_control(self):
        self.fake.key_match = False
        result = self.adapter.poll_health(self.api, now=NOW)
        self.assertFalse(result[0]["healthy"])
        self.assertEqual(self.api.catalog.public_catalog(now=NOW)["servers"], [])

    def test_missing_future_or_stale_health_time_hides_catalog_negative_control(self):
        self.fake.include_measured_at = False
        self.assertFalse(self.adapter.poll_health(self.api, now=NOW)[0]["healthy"])
        self.fake.include_measured_at = True
        self.fake.measured_at = NOW + timedelta(seconds=31)
        self.assertFalse(self.adapter.poll_health(self.api, now=NOW)[0]["healthy"])
        self.fake.measured_at = NOW - timedelta(seconds=121)
        self.assertFalse(self.adapter.poll_health(self.api, now=NOW)[0]["healthy"])
        self.assertEqual(self.api.catalog.public_catalog(now=NOW)["servers"], [])

    def test_ssh_command_enforces_identity_known_hosts_and_batch_mode(self):
        self.adapter.poll_health(self.api, now=NOW)
        command = self.fake.commands[0]
        joined = " ".join(command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn("UserKnownHostsFile=", joined)
        self.assertNotIn("StrictHostKeyChecking=no", joined)

    def test_control_api_provisions_and_revokes_only_after_remote_readback(self):
        token, device_id = self.create_device()
        revoked = self.api.handle(
            "DELETE", f"/v1/devices/{device_id}",
            headers={"Authorization": f"Bearer {token}"}, now=NOW,
        )
        self.assertEqual(revoked.status, 200)
        self.assertEqual(revoked.body["enforcement"], "confirmed")

    def test_remote_failure_returns_generic_503_without_stderr_echo(self):
        self.adapter.poll_health(self.api, now=NOW)
        token = self.session()
        self.fake.fail = True
        response = self.api.handle(
            "POST", "/v1/devices", headers={"Authorization": f"Bearer {token}"},
            body={"wg_public_key": CLIENT_KEY, "server_id": "de-fra-01"}, now=NOW,
        )
        self.assertEqual(response.status, 503)
        self.assertEqual(response.body["error"], "PEER_ADAPTER_FAILED")
        self.assertNotIn("secret-like", str(response.body))
        self.assertNotIn(ACCOUNT, str(response.body))

    def test_counter_poll_is_idempotent_and_updates_wallet_and_handshake(self):
        token, device_id = self.create_device()
        self.fake.counter_total = 0
        baseline = self.adapter.poll_counters(self.api)
        self.fake.counter_total = 100
        charged = self.adapter.poll_counters(self.api)
        duplicate = self.adapter.poll_counters(self.api)
        wallet = self.api.handle(
            "GET", "/v1/wallet", headers={"Authorization": f"Bearer {token}"}, now=NOW
        )
        self.assertTrue(baseline[0]["usage_applied"])
        self.assertTrue(charged[0]["usage_applied"])
        self.assertTrue(duplicate[0]["duplicate"])
        self.assertEqual(wallet.body["balances"]["free"], 1_000_000_000 - 100)
        self.assertEqual(device_id, charged[0]["device_id"])

    def test_node_reboot_epoch_allows_counter_reset_but_old_epoch_rejected(self):
        _, device_id = self.create_device()
        self.fake.counter_total = 100
        self.adapter.poll_counters(self.api)
        self.api.record_peer_observation(
            device_id, server_id="de-fra-01", epoch=102, handshake_at=NOW,
            rx_bytes=1, tx_bytes=1, observed_at=NOW,
        )
        with self.assertRaises(ValueError):
            self.api.record_peer_observation(
                device_id, server_id="de-fra-01", epoch=101, handshake_at=NOW,
                rx_bytes=200, tx_bytes=200, observed_at=NOW,
            )

    def test_invalid_kr_node_and_missing_known_hosts_are_rejected(self):
        with self.assertRaises(ValueError):
            SSHNodeSpec(**{**self.spec.__dict__, "country_code": "KR"}).validated()
        with self.assertRaises(ValueError):
            SSHNodeSpec(
                **{**self.spec.__dict__, "known_hosts_file": pathlib.Path(self.temp.name) / "missing"}
            ).validated()

    def test_direct_adapter_rejects_non_hmac_account(self):
        with self.assertRaises(NodeAdapterError):
            self.adapter.provision("friendly-account", "b" * 32, CLIENT_KEY, {"server_id": "de-fra-01"})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SSHNodeAdapterTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"SSH node adapter 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
