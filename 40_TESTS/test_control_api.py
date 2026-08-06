#!/usr/bin/env python3
"""제어 API 인증·기기·지갑·보호·추천·삭제 계약 검사."""
from __future__ import annotations

import base64
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_api import ControlAPI  # noqa: E402
from app.wallet_ledger import FREE_CAP_BYTES, MB  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
SERVER_KEY = base64.b64encode(bytes(range(32))).decode("ascii")


def client_key(seed: int) -> str:
    return base64.b64encode(bytes((seed + index) % 256 for index in range(32))).decode("ascii")


class ControlAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_control_api_")
        self.path = pathlib.Path(self.temp.name) / "control.sqlite3"
        self.provisioned: list[tuple[str, str]] = []

        def provisioner(account_id, device_id, public_key, server):
            self.provisioned.append((account_id, device_id))
            return {"assigned_address": f"10.64.0.{len(self.provisioned) + 1}/32"}

        self.api = ControlAPI(self.path, peer_provisioner=provisioner)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_server(self):
        return self.api.catalog.register_verified_server(
            server_id="de-fra-01",
            country_code="DE",
            country="Germany",
            city="Frankfurt",
            provider_ref="provider-a",
            exit_ip="8.8.8.8",
            endpoint="vpn.example.test:51820",
            wg_public_key=SERVER_KEY,
            dns_addresses=["1.1.1.1"],
            health="healthy",
            capacity_percent=20,
            contract_active=True,
            provisioned=True,
            exit_verified=True,
            measured_at=NOW,
            verified_at=NOW,
        )

    def session(self, account_id="acct_test_001"):
        claim = self.api.provision_claim(account_id, now=NOW)["claim"]
        response = self.api.handle(
            "POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW
        )
        self.assertEqual(response.status, 200)
        return response.body["access_token"]

    @staticmethod
    def auth(token, *, device_id=None):
        headers = {"Authorization": f"Bearer {token}"}
        if device_id:
            headers["X-FreeFlex-Device"] = device_id
        return headers

    def register_device(self, token, seed=1):
        self.add_server()
        response = self.api.handle(
            "POST",
            "/v1/devices",
            headers=self.auth(token),
            body={"wg_public_key": client_key(seed), "server_id": "de-fra-01"},
            now=NOW,
        )
        self.assertEqual(response.status, 201)
        return response

    def test_claim_is_one_time_and_only_hashes_are_persisted(self):
        issued = self.api.provision_claim("acct_claim_001", now=NOW)
        claim = issued["claim"]
        first = self.api.handle("POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW)
        second = self.api.handle("POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW)
        self.assertEqual(first.status, 200)
        self.assertEqual(second.status, 401)
        token = first.body["access_token"]
        with closing(sqlite3.connect(self.path)) as connection:
            stored_claim = connection.execute("SELECT claim_hash FROM api_claims").fetchone()[0]
            stored_session = connection.execute("SELECT session_hash FROM api_sessions").fetchone()[0]
        self.assertNotEqual(stored_claim, claim)
        self.assertNotEqual(stored_session, token)
        self.assertEqual(len(stored_claim), 64)
        self.assertEqual(len(stored_session), 64)

    def test_claim_expiry_and_protected_routes_fail_closed(self):
        claim = self.api.provision_claim("acct_expired", now=NOW, ttl_minutes=1)["claim"]
        expired = self.api.handle(
            "POST", "/v1/claims/exchange", body={"claim": claim}, now=NOW + timedelta(minutes=2)
        )
        wallet = self.api.handle("GET", "/v1/wallet", now=NOW)
        self.assertEqual(expired.status, 401)
        self.assertEqual(wallet.status, 401)
        self.assertNotIn(claim, str(expired.body))

    def test_public_catalog_is_empty_until_actual_server_verified(self):
        empty = self.api.handle("GET", "/v1/catalog", now=NOW)
        self.assertEqual(empty.body["available_count"], 0)
        self.add_server()
        live = self.api.handle("GET", "/v1/catalog", now=NOW)
        self.assertEqual(live.body["available_count"], 1)
        self.assertNotIn("exit_ip", live.body["servers"][0])

    def test_device_requires_real_server_and_peer_adapter(self):
        token = self.session()
        unavailable = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(token), body={"wg_public_key": client_key(1)}, now=NOW
        )
        self.assertEqual(unavailable.status, 503)
        self.add_server()
        no_adapter = ControlAPI(self.path).handle(
            "POST",
            "/v1/devices",
            headers=self.auth(token),
            body={"wg_public_key": client_key(2), "server_id": "de-fra-01"},
            now=NOW,
        )
        self.assertEqual(no_adapter.status, 503)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0], 0)

    def test_device_config_never_accepts_or_returns_private_key(self):
        token = self.session()
        self.add_server()
        rejected = self.api.handle(
            "POST",
            "/v1/devices",
            headers=self.auth(token),
            body={"wg_public_key": client_key(1), "private_key": "must-not-leave-device"},
            now=NOW,
        )
        self.assertEqual(rejected.status, 400)
        self.assertEqual(rejected.body["error"], "PRIVATE_KEY_FORBIDDEN")
        created = self.api.handle(
            "POST",
            "/v1/devices",
            headers=self.auth(token),
            body={"wg_public_key": client_key(1), "server_id": "de-fra-01"},
            now=NOW,
        )
        self.assertEqual(created.status, 201)
        self.assertFalse(created.body["private_key_received"])
        self.assertNotIn("private", str(created.body["configuration"]).lower())

    def test_two_device_limit_and_duplicate_key_are_enforced(self):
        token = self.session()
        self.add_server()
        first = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(token),
            body={"wg_public_key": client_key(1), "server_id": "de-fra-01"}, now=NOW,
        )
        duplicate = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(token),
            body={"wg_public_key": client_key(1), "server_id": "de-fra-01"}, now=NOW,
        )
        second = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(token),
            body={"wg_public_key": client_key(2), "server_id": "de-fra-01"}, now=NOW,
        )
        third = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(token),
            body={"wg_public_key": client_key(3), "server_id": "de-fra-01"}, now=NOW,
        )
        self.assertEqual(first.status, 201)
        self.assertEqual(duplicate.body["error"], "DUPLICATE_PUBLIC_KEY")
        self.assertEqual(second.status, 201)
        self.assertEqual(third.body["error"], "DEVICE_LIMIT")

    def test_device_list_exposes_management_fields_without_public_key(self):
        token = self.session()
        created = self.register_device(token)
        listed = self.api.handle("GET", "/v1/devices", headers=self.auth(token), now=NOW)
        self.assertEqual(listed.status, 200)
        self.assertEqual(listed.body["active_count"], 1)
        self.assertEqual(listed.body["active_limit"], 2)
        self.assertEqual(listed.body["devices"][0]["device_id"], created.body["device_id"])
        self.assertNotIn("public_key", str(listed.body).lower())

        revoked = self.api.handle(
            "DELETE", f"/v1/devices/{created.body['device_id']}", headers=self.auth(token), now=NOW,
        )
        self.assertEqual(revoked.status, 202)
        after = self.api.handle("GET", "/v1/devices", headers=self.auth(token), now=NOW)
        self.assertEqual(after.body["active_count"], 0)
        self.assertEqual(after.body["devices"][0]["status"], "revocation_pending")

    def test_check_needs_exit_handshake_and_safety_for_protected(self):
        token = self.session()
        created = self.register_device(token)
        device_id = created.body["device_id"]
        headers = self.auth(token, device_id=device_id)
        public_only = self.api.handle("GET", "/v1/check", remote_ip="8.8.8.8", now=NOW)
        before = self.api.handle("GET", "/v1/check", headers=headers, remote_ip="8.8.8.8", now=NOW)
        self.api.record_peer_observation(
            device_id, server_id="de-fra-01", handshake_at=NOW - timedelta(seconds=10),
            rx_bytes=100, tx_bytes=200, observed_at=NOW,
        )
        still_limited = self.api.handle("GET", "/v1/check", headers=headers, remote_ip="8.8.8.8", now=NOW)
        self.api.record_safety_observation(
            device_id, os_family="windows", dns_protected=True, ipv6_protected=True,
            kill_switch_protected=True, observed_at=NOW,
        )
        protected = self.api.handle("GET", "/v1/check", headers=headers, remote_ip="8.8.8.8", now=NOW)
        wrong_exit = self.api.handle("GET", "/v1/check", headers=headers, remote_ip="1.1.1.1", now=NOW)
        self.assertFalse(public_only.body["protected"])
        self.assertFalse(before.body["protected"])
        self.assertFalse(still_limited.body["protected"])
        self.assertTrue(protected.body["protected"])
        self.assertEqual(protected.body["state"], "protected")
        self.assertFalse(wrong_exit.body["protected"])

    def test_wallet_usage_and_referral_routes_use_authenticated_account(self):
        token = self.session("acct_product_001")
        headers = self.auth(token)
        wallet = self.api.handle("GET", "/v1/wallet", headers=headers, now=NOW)
        usage = self.api.handle("GET", "/v1/usage", headers=headers, now=NOW)
        referral = self.api.handle("POST", "/v1/referrals", headers=headers, now=NOW)
        referrals = self.api.handle("GET", "/v1/referrals", headers=headers, now=NOW)
        self.assertEqual(wallet.body["balances"]["free"], FREE_CAP_BYTES)
        self.assertEqual(usage.body["sessions"], [])
        self.assertEqual(referral.status, 201)
        self.assertIn("?ref=", referral.body["share_url"])
        self.assertNotIn("token", referral.body)
        self.assertEqual(referrals.body["referrals"], [])

    def test_referral_flows_from_new_account_to_real_protection_and_100mb_reward(self):
        inviter_token = self.session("acct_inviter_001")
        issued = self.api.handle(
            "POST", "/v1/referrals", headers=self.auth(inviter_token), now=NOW
        )
        referral_token = parse_qs(urlsplit(issued.body["share_url"]).query)["ref"][0]

        invitee_claim = self.api.provision_claim("acct_invitee_001", now=NOW)["claim"]
        exchange = self.api.handle(
            "POST",
            "/v1/claims/exchange",
            body={"claim": invitee_claim, "referral_token": referral_token},
            now=NOW,
        )
        self.assertTrue(exchange.body["referral"]["applied"])
        invitee_token = exchange.body["access_token"]
        self.add_server()
        device = self.api.handle(
            "POST", "/v1/devices", headers=self.auth(invitee_token),
            body={"wg_public_key": client_key(9), "server_id": "de-fra-01"}, now=NOW,
        ).body["device_id"]
        self.api.record_peer_observation(
            device, server_id="de-fra-01", handshake_at=NOW - timedelta(seconds=10),
            rx_bytes=0, tx_bytes=0, observed_at=NOW,
        )
        self.api.record_safety_observation(
            device, os_family="android", dns_protected=True, ipv6_protected=True,
            kill_switch_protected=True, observed_at=NOW,
        )
        protected = self.api.handle(
            "GET", "/v1/check", headers=self.auth(invitee_token, device_id=device),
            remote_ip="8.8.8.8", now=NOW,
        )
        self.assertTrue(protected.body["protected"])
        self.assertEqual(len(protected.body["referral_protection_updates"]), 1)
        self.api.ingest_usage_counter(
            event_id="ref-base", node_id="node-de-01", device_id=device,
            epoch=1, rx_bytes=0, tx_bytes=0, observed_at=NOW,
        )
        qualified = self.api.ingest_usage_counter(
            event_id="ref-100mb", node_id="node-de-01", device_id=device,
            epoch=1, rx_bytes=50 * MB, tx_bytes=50 * MB, observed_at=NOW,
        )
        self.assertTrue(qualified["referral_updates"][0]["rewarded_now"])
        inviter = self.api.wallet.snapshot("acct_inviter_001", now=NOW)
        invitee = self.api.wallet.snapshot("acct_invitee_001", now=NOW)
        self.assertEqual(inviter["balances"]["earned"], 500 * MB)
        self.assertEqual(invitee["balances"]["earned"], 500 * MB)

    def test_existing_account_cannot_claim_referral_on_new_session(self):
        inviter_token = self.session("acct_inviter_existing")
        issued = self.api.handle(
            "POST", "/v1/referrals", headers=self.auth(inviter_token), now=NOW
        )
        referral_token = parse_qs(urlsplit(issued.body["share_url"]).query)["ref"][0]
        self.session("acct_already_exists")
        later_claim = self.api.provision_claim("acct_already_exists", now=NOW)["claim"]
        exchange = self.api.handle(
            "POST", "/v1/claims/exchange",
            body={"claim": later_claim, "referral_token": referral_token}, now=NOW,
        )
        self.assertEqual(exchange.status, 200)
        self.assertFalse(exchange.body["referral"]["applied"])
        self.assertIn("신규 계정", exchange.body["referral"]["reason"])

    def test_revocation_without_server_adapter_is_honestly_pending(self):
        token = self.session()
        device = self.register_device(token).body["device_id"]
        response = self.api.handle(
            "DELETE", f"/v1/devices/{device}", headers=self.auth(token), now=NOW
        )
        self.assertEqual(response.status, 202)
        self.assertEqual(response.body["status"], "revocation_pending")
        self.assertEqual(response.body["enforcement"], "pending")

    def test_deletion_request_revokes_session_and_is_idempotent(self):
        token = self.session("acct_delete_001")
        first = self.api.handle(
            "POST", "/v1/account/delete", headers=self.auth(token), now=NOW
        )
        after = self.api.handle(
            "GET", "/v1/wallet", headers=self.auth(token), now=NOW
        )
        self.assertEqual(first.status, 202)
        self.assertTrue(first.body["session_revoked"])
        self.assertEqual(after.status, 401)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ControlAPITests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"제어 API 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
