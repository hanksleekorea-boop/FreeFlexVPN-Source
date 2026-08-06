#!/usr/bin/env python3
"""FreeFlexVPN 실제 서버 카탈로그 계약과 음성 대조."""
from __future__ import annotations

import base64
import pathlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "20_SRC"))

from app.server_catalog import ServerCatalog  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
WG_KEY = base64.b64encode(bytes(range(32))).decode("ascii")


class ServerCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_catalog_")
        self.path = pathlib.Path(self.temp.name) / "control.sqlite3"
        self.catalog = ServerCatalog(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_server(self, **changes):
        values = {
            "server_id": "de-fra-01",
            "country_code": "DE",
            "country": "Germany",
            "city": "Frankfurt",
            "provider_ref": "provider-a",
            "exit_ip": "8.8.8.8",
            "endpoint": "vpn.example.test:51820",
            "wg_public_key": WG_KEY,
            "dns_addresses": ["1.1.1.1"],
            "health": "healthy",
            "capacity_percent": 21,
            "contract_active": True,
            "provisioned": True,
            "exit_verified": True,
            "measured_at": NOW,
            "verified_at": NOW,
        }
        values.update(changes)
        return self.catalog.register_verified_server(**values)

    def test_empty_by_default_instead_of_demo_locations(self):
        result = self.catalog.public_catalog(now=NOW)
        self.assertEqual(result["servers"], [])
        self.assertEqual(result["available_count"], 0)

    def test_only_fully_verified_live_server_is_public(self):
        result = self.add_server()
        self.assertTrue(result["applied"])
        public = self.catalog.public_catalog(now=NOW)
        self.assertEqual(public["available_count"], 1)
        self.assertEqual(public["servers"][0]["server_id"], "de-fra-01")
        self.assertNotIn("exit_ip", public["servers"][0])
        self.assertNotIn("provider_ref", public["servers"][0])
        self.assertNotIn("endpoint", public["servers"][0])

    def test_unverified_seoul_placeholder_is_hidden_negative_control(self):
        with self.assertRaises(ValueError):
            self.add_server(
                server_id="kr-seoul-demo",
                country_code="KR",
                country="South Korea",
                city="Seoul",
                exit_verified=False,
                verified_at=None,
            )
        self.assertEqual(self.catalog.public_catalog(now=NOW)["servers"], [])

    def test_inactive_unprovisioned_and_unhealthy_are_hidden(self):
        cases = (
            {"server_id": "de-fra-a", "contract_active": False},
            {"server_id": "de-fra-b", "provisioned": False},
            {"server_id": "de-fra-c", "health": "maintenance"},
            {"server_id": "de-fra-d", "health": "unavailable"},
        )
        for case in cases:
            self.add_server(**case)
        self.assertEqual(self.catalog.public_catalog(now=NOW)["servers"], [])

    def test_stale_health_is_hidden(self):
        self.add_server(measured_at=NOW - timedelta(seconds=121))
        self.assertEqual(self.catalog.public_catalog(now=NOW)["available_count"], 0)

    def test_future_health_is_hidden_negative_control(self):
        self.add_server(measured_at=NOW + timedelta(seconds=31))
        self.assertEqual(self.catalog.public_catalog(now=NOW)["available_count"], 0)

    def test_control_plane_can_resolve_exit_and_connection_config(self):
        self.add_server()
        self.assertEqual(self.catalog.server_for_exit_ip("8.8.8.8", now=NOW)["server_id"], "de-fra-01")
        config = self.catalog.connection_config("de-fra-01", now=NOW)
        self.assertEqual(config["server_public_key"], WG_KEY)
        self.assertEqual(config["dns"], ["1.1.1.1"])

    def test_private_or_reserved_exit_ip_is_rejected(self):
        for value in ("127.0.0.1", "10.0.0.1", "192.0.2.1", "not-an-ip"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.add_server(exit_ip=value)

    def test_invalid_wireguard_key_and_dns_are_rejected(self):
        with self.assertRaises(ValueError):
            self.add_server(wg_public_key="demo-key")
        with self.assertRaises(ValueError):
            self.add_server(dns_addresses=["10.0.0.53"])

    def test_storage_failure_fails_closed_and_preserves_file(self):
        self.add_server()
        before = self.path.read_bytes()
        with mock.patch.object(self.catalog, "_connect", side_effect=OSError("blocked")):
            public = self.catalog.public_catalog(now=NOW)
        self.assertEqual(public["servers"], [])
        self.assertEqual(public["persistence_status"], "unavailable")
        self.assertIn("공개하지 않습니다", public["warning"])
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ServerCatalogTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"서버 카탈로그 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
