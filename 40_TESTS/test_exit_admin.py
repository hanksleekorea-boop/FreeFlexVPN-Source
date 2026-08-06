#!/usr/bin/env python3
"""exit-node 관리 CLI의 할당·readback·폐기·계측 검사."""
from __future__ import annotations

import base64
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra import exit_admin as ea  # noqa: E402


ACCOUNT = "a" * 64
DEVICE = "b" * 32
KEY = base64.b64encode(bytes(range(1, 33))).decode("ascii")
OTHER_KEY = base64.b64encode(bytes(range(33, 65))).decode("ascii")


def observed(key=KEY, ip="10.66.0.2", rx=100, tx=200, handshake=0):
    return {
        key: {
            "allowed_ip": ip,
            "rx_bytes": rx,
            "tx_bytes": tx,
            "total_bytes": rx + tx,
            "latest_handshake_epoch": handshake,
        }
    }


class ExitAdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_exit_admin_")
        root = pathlib.Path(self.temp.name)
        self.state = root / "admin" / "state.json"
        self.quota = root / "quota" / "state.json"
        self.health = root / "health" / "latest.json"
        self.public_key = root / "wg0.pub"
        self.boot_id = root / "boot_id"
        self.boot_id.write_text("boot-test-001\n", encoding="ascii")
        self.public_key.write_text(KEY + "\n", encoding="ascii")
        self.admin = ea.ExitAdmin(
            node_id="exit-de-01", state_path=self.state, quota_path=self.quota,
            health_path=self.health, server_public_key_path=self.public_key,
            boot_id_path=self.boot_id,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def provision(self):
        with (
            mock.patch.object(ea.qa, "read_wg", side_effect=[{}, observed()]),
            mock.patch.object(ea.qa, "sync_firewall"),
            mock.patch.object(ea.qa, "sync_wireguard"),
        ):
            return self.admin.provision(ACCOUNT, DEVICE, KEY)

    def test_provision_allocates_first_safe_ip_and_confirms_readback(self):
        result = self.provision()
        self.assertEqual(result["assigned_address"], "10.66.0.2/32")
        self.assertTrue(result["runtime_confirmed"])
        state = ea.load_state(self.state, "exit-de-01")
        self.assertEqual(state["peers"][DEVICE]["status"], "active")
        self.assertNotIn("private", json.dumps(state).lower())

    def test_provision_retry_is_idempotent(self):
        self.provision()
        with (
            mock.patch.object(ea.qa, "read_wg", side_effect=[observed(), observed()]),
            mock.patch.object(ea.qa, "sync_firewall"),
            mock.patch.object(ea.qa, "sync_wireguard"),
        ):
            second = self.admin.provision(ACCOUNT, DEVICE, KEY)
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["assigned_address"], "10.66.0.2/32")

    def test_readback_mismatch_never_marks_active_negative_control(self):
        with (
            mock.patch.object(ea.qa, "read_wg", side_effect=[{}, {}]),
            mock.patch.object(ea.qa, "sync_firewall"),
            mock.patch.object(ea.qa, "sync_wireguard"),
        ):
            with self.assertRaises(RuntimeError):
                self.admin.provision(ACCOUNT, DEVICE, KEY)
        state = ea.load_state(self.state, "exit-de-01")
        self.assertEqual(state["peers"][DEVICE]["status"], "provisioning")

    def test_device_id_payload_change_and_key_reuse_are_rejected(self):
        self.provision()
        with self.assertRaises(ValueError):
            self.admin.provision(ACCOUNT, DEVICE, OTHER_KEY)
        with self.assertRaises(ValueError):
            self.admin.provision(ACCOUNT, "c" * 32, KEY)

    def test_revoke_confirms_absence_and_keeps_address_reserved(self):
        self.provision()
        with (
            mock.patch.object(ea.qa, "read_wg", side_effect=[observed(), {}]),
            mock.patch.object(ea.qa, "sync_firewall"),
            mock.patch.object(ea.qa, "sync_wireguard"),
        ):
            result = self.admin.revoke(DEVICE)
        self.assertTrue(result["runtime_confirmed"])
        state = ea.load_state(self.state, "exit-de-01")
        self.assertEqual(state["peers"][DEVICE]["status"], "revoked")
        self.assertEqual(state["peers"][DEVICE]["allowed_ip"], "10.66.0.2")

    def test_revoke_readback_failure_stays_revoking(self):
        self.provision()
        with (
            mock.patch.object(ea.qa, "read_wg", side_effect=[observed(), observed()]),
            mock.patch.object(ea.qa, "sync_firewall"),
            mock.patch.object(ea.qa, "sync_wireguard"),
        ):
            with self.assertRaises(RuntimeError):
                self.admin.revoke(DEVICE)
        self.assertEqual(ea.load_state(self.state, "exit-de-01")["peers"][DEVICE]["status"], "revoking")

    def test_counters_map_public_key_to_device_without_key_disclosure(self):
        self.provision()
        handshake = int(datetime(2026, 8, 2, tzinfo=timezone.utc).timestamp())
        with mock.patch.object(ea.qa, "read_wg", return_value=observed(handshake=handshake)):
            result = self.admin.counters()
        self.assertEqual(result["samples"][0]["device_id"], DEVICE)
        self.assertEqual(result["samples"][0]["rx_bytes"], 100)
        self.assertNotIn(KEY, json.dumps(result))

    def test_health_readback_is_strict_and_contains_public_key_only(self):
        self.health.parent.mkdir(parents=True)
        self.health.write_text(
            json.dumps({"status": "ok", "checked_at": "2026-08-02T00:00:00Z", "failures": ""}),
            encoding="utf-8",
        )
        result = self.admin.health()
        self.assertEqual(result["health"], "healthy")
        self.assertEqual(result["server_public_key"], KEY)

    def test_corrupt_admin_state_is_preserved(self):
        self.state.parent.mkdir(parents=True)
        original = b"{broken"
        self.state.write_bytes(original)
        with self.assertRaises(ea.qa.QuotaStateError):
            ea.load_state(self.state, "exit-de-01")
        self.assertEqual(self.state.read_bytes(), original)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExitAdminTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"exit admin 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
