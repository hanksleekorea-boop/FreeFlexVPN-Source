#!/usr/bin/env python3
"""GCP 첫 실제 노드 admission과 R6 미승격 경계 검사."""
from __future__ import annotations

import base64
import pathlib
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.gcp_node_admission import evaluate_gcp_admission, evaluate_gcp_configuration  # noqa: E402
from app.ssh_node_adapter import SSHNodeSpec  # noqa: E402


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


class GCPNodeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_gcp_admission_")
        root = pathlib.Path(self.temp.name)
        self.identity = root / "id_ed25519"
        self.known = root / "known_hosts"
        self.identity.write_text("test-only", encoding="ascii")
        self.known.write_text("gcp.example.test ssh-ed25519 test-only", encoding="ascii")

    def tearDown(self):
        self.temp.cleanup()

    def node(self, **changes):
        values = {
            "server_id": "gcp-usw1-01", "node_id": "gcp-usw1-01",
            "host": "gcp.example.test", "ssh_user": "freeflex", "ssh_port": 22,
            "identity_file": self.identity, "known_hosts_file": self.known,
            "country_code": "US", "country": "United States", "city": "Oregon",
            "provider_ref": "gcp", "exit_ip": "8.8.8.8", "endpoint": "8.8.8.8:51820",
            "server_public_key": base64.b64encode(b"g" * 32).decode("ascii"),
            "dns_addresses": ("1.1.1.1",), "exit_verified": True,
            "verified_at": NOW, "capacity_percent": 10,
        }
        values.update(changes)
        return SSHNodeSpec(**values).validated()

    def live(self, node=None, *, runtime=None, catalog=None):
        node = node or self.node()
        runtime = runtime or {
            "health": [{"server_id": node.server_id, "healthy": True, "catalog_applied": True}],
            "counter_error": None,
        }
        catalog = catalog or {"servers": [{"server_id": node.server_id}], "persistence_status": "persistent"}
        return evaluate_gcp_admission([node], runtime, catalog, checked_at=NOW)

    def test_configuration_is_ready_but_never_live_or_r6_ready(self):
        report = evaluate_gcp_configuration([self.node()], checked_at=NOW)
        self.assertTrue(report["configuration_ready"])
        self.assertFalse(report["admission_ready"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["r6_ready"])
        self.assertFalse(report["network_attempted"])

    def test_live_gcp_node_is_admitted_without_r6_promotion(self):
        report = self.live()
        self.assertTrue(report["admission_ready"])
        self.assertEqual(report["status"], "admitted_first_node")
        self.assertFalse(report["ready"])
        self.assertFalse(report["r6_ready"])
        self.assertEqual(report["provider_diversity_credit"], 1)
        self.assertIn("different cloud provider", report["next_gate"])

    def test_non_gcp_or_multiple_nodes_are_rejected(self):
        self.assertFalse(evaluate_gcp_configuration([self.node(provider_ref="aws")], checked_at=NOW)["configuration_ready"])
        self.assertFalse(evaluate_gcp_configuration([self.node(), self.node(server_id="gcp-usw1-02")], checked_at=NOW)["configuration_ready"])

    def test_unknown_duplicate_or_unhealthy_readback_blocks(self):
        node = self.node()
        bad_runtime = [
            {"health": [{"server_id": node.server_id, "healthy": False, "catalog_applied": False}], "counter_error": None},
            {"health": [{"server_id": node.server_id, "healthy": True, "catalog_applied": True}, {"server_id": "unknown", "healthy": True, "catalog_applied": True}], "counter_error": None},
            {"health": [{"server_id": node.server_id, "healthy": True, "catalog_applied": True}], "counter_error": "NodeAdapterError"},
        ]
        for runtime in bad_runtime:
            with self.subTest(runtime=runtime):
                self.assertFalse(self.live(node, runtime=runtime)["admission_ready"])

    def test_catalog_must_be_exact_and_persistent(self):
        node = self.node()
        bad_catalogs = [
            {"servers": [{"server_id": node.server_id}, {"server_id": "unknown"}], "persistence_status": "persistent"},
            {"servers": [{"server_id": node.server_id}, {"server_id": node.server_id}], "persistence_status": "persistent"},
            {"servers": [{"server_id": node.server_id}], "persistence_status": "unavailable"},
        ]
        for catalog in bad_catalogs:
            with self.subTest(catalog=catalog):
                self.assertFalse(self.live(node, catalog=catalog)["admission_ready"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPNodeAdmissionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP 첫 노드 admission 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
