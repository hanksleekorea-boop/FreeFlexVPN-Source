#!/usr/bin/env python3
"""R6 2공급자 실서버 사전점검 계약과 음성 대조."""
from __future__ import annotations

import base64
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.r6_preflight import (  # noqa: E402
    evaluate_configuration_preflight,
    evaluate_node_topology,
    evaluate_r6_preflight,
)
from app.ssh_node_adapter import SSHNodeSpec  # noqa: E402

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


class R6PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_r6_preflight_")
        root = pathlib.Path(self.temp.name)
        self.identity = root / "id_ed25519"
        self.known = root / "known_hosts"
        self.identity.write_text("test-only", encoding="ascii")
        self.known.write_text("example.test ssh-ed25519 test-only", encoding="ascii")

    def tearDown(self):
        self.temp.cleanup()

    def node(self, suffix: int, **changes) -> SSHNodeSpec:
        values = {
            "server_id": f"exit-node-{suffix}", "node_id": f"exit-node-{suffix}",
            "host": f"vpn{suffix}.example.test", "ssh_user": "freeflex", "ssh_port": 22,
            "identity_file": self.identity, "known_hosts_file": self.known,
            "country_code": "DE" if suffix == 1 else "SG",
            "country": "Germany" if suffix == 1 else "Singapore",
            "city": "Frankfurt" if suffix == 1 else "Singapore",
            "provider_ref": f"provider-{suffix}", "exit_ip": "8.8.8.8" if suffix == 1 else "9.9.9.9",
            "endpoint": f"vpn{suffix}.example.test:51820",
            "server_public_key": base64.b64encode(bytes([suffix]) * 32).decode("ascii"),
            "dns_addresses": ("1.1.1.1",), "exit_verified": True,
            "verified_at": NOW, "capacity_percent": 10,
        }
        values.update(changes)
        return SSHNodeSpec(**values).validated()

    def live(self, nodes, *, runtime_changes=None, catalog_changes=None):
        runtime = {
            "health": [{"server_id": node.server_id, "healthy": True, "catalog_applied": True} for node in nodes],
            "counters": [], "counter_error": None,
        }
        catalog = {"servers": [{"server_id": node.server_id} for node in nodes], "persistence_status": "persistent"}
        runtime.update(runtime_changes or {})
        catalog.update(catalog_changes or {})
        return evaluate_r6_preflight(nodes, runtime, catalog, checked_at=NOW)

    def test_two_distinct_live_providers_pass_without_sensitive_fields(self):
        report = self.live([self.node(1), self.node(2)])
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "passed")
        self.assertNotIn("host", str(report))
        self.assertNotIn("server_public_key", str(report))

    def test_one_node_or_same_provider_blocks_r6(self):
        self.assertFalse(evaluate_node_topology([self.node(1)])["ready"])
        nodes = [self.node(1), self.node(2, provider_ref="provider-1")]
        self.assertFalse(self.live(nodes)["ready"])

    def test_duplicate_exit_or_endpoint_blocks_r6(self):
        first = self.node(1)
        self.assertFalse(evaluate_node_topology([first, self.node(2, exit_ip=first.exit_ip)])["ready"])
        self.assertFalse(evaluate_node_topology([first, self.node(2, endpoint=first.endpoint)])["ready"])

    def test_unhealthy_or_missing_public_node_blocks_r6(self):
        nodes = [self.node(1), self.node(2)]
        runtime = {"health": [{"server_id": nodes[0].server_id, "healthy": True, "catalog_applied": True}], "counter_error": None}
        catalog = {"servers": [{"server_id": nodes[0].server_id}], "persistence_status": "persistent"}
        self.assertFalse(evaluate_r6_preflight(nodes, runtime, catalog, checked_at=NOW)["ready"])

    def test_counter_or_persistence_failure_blocks_r6(self):
        nodes = [self.node(1), self.node(2)]
        self.assertFalse(self.live(nodes, runtime_changes={"counter_error": "NodeAdapterError"})["ready"])
        self.assertFalse(self.live(nodes, catalog_changes={"persistence_status": "unavailable"})["ready"])

    def test_public_catalog_rejects_unknown_duplicate_or_malformed_rows(self):
        nodes = [self.node(1), self.node(2)]
        valid_rows = [{"server_id": node.server_id} for node in nodes]
        invalid_catalogs = [
            valid_rows + [{"server_id": "not-in-this-candidate"}],
            valid_rows + [{"server_id": nodes[0].server_id}],
            valid_rows + [{}],
        ]
        for rows in invalid_catalogs:
            with self.subTest(rows=rows):
                report = self.live(nodes, catalog_changes={"servers": rows})
                self.assertFalse(report["ready"])
                check = next(item for item in report["checks"] if item["id"] == "catalog_rows_are_candidate_bound")
                self.assertFalse(check["passed"])

    def test_naive_checked_at_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_r6_preflight([], {}, {}, checked_at=datetime(2026, 8, 2))

    def test_config_only_passes_topology_but_never_claims_r6_ready(self):
        report = evaluate_configuration_preflight([self.node(1), self.node(2)], checked_at=NOW)
        self.assertTrue(report["configuration_ready"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["network_attempted"])
        self.assertIn("no server", report["evidence_level"])

    def test_config_only_blocks_single_provider_negative_control(self):
        report = evaluate_configuration_preflight(
            [self.node(1), self.node(2, provider_ref="provider-1")], checked_at=NOW
        )
        self.assertFalse(report["configuration_ready"])
        self.assertEqual(report["status"], "blocked")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(R6PreflightTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"R6 실서버 사전점검 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
