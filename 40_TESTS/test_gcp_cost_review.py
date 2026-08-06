#!/usr/bin/env python3
"""GCP 첫 노드 비용 검토의 계산·정직성 계약."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_cost_review import build_cost_review, estimate_first_node_month  # noqa: E402


class GCPCostReviewTests(unittest.TestCase):
    def test_free_vm_still_includes_external_ipv4_charge(self):
        estimate = estimate_first_node_month(usage_gib=1, destination="korea")
        self.assertEqual(estimate["compute"], "FREE_TIER_ASSUMED")
        self.assertEqual(estimate["external_ipv4_usd"], 3.65)
        self.assertGreater(estimate["known_minimum_usd"], 0)

    def test_korea_egress_after_free_gib_is_nineteen_cents(self):
        estimate = estimate_first_node_month(usage_gib=10, destination="korea")
        self.assertEqual(estimate["free_egress_gib_assumed"], 1.0)
        self.assertEqual(estimate["billed_egress_gib"], 9.0)
        self.assertEqual(estimate["egress_usd"], 1.71)
        self.assertEqual(estimate["known_minimum_usd"], 5.36)

    def test_china_and_australia_do_not_receive_assumed_free_egress(self):
        for destination in ("china_excluding_hong_kong", "australia"):
            with self.subTest(destination=destination):
                estimate = estimate_first_node_month(usage_gib=1, destination=destination)
                self.assertEqual(estimate["free_egress_gib_assumed"], 0.0)

    def test_non_free_region_keeps_compute_and_disk_unknown(self):
        estimate = estimate_first_node_month(usage_gib=1, destination="korea", region="asia-northeast1")
        self.assertEqual(estimate["compute"], "UNKNOWN_VERIFY_CONSOLE")
        self.assertEqual(estimate["disk"], "UNKNOWN_VERIFY_CONSOLE")
        self.assertEqual(len(estimate["unknown_costs"]), 2)

    def test_invalid_inputs_fail_closed(self):
        invalid = [
            {"usage_gib": -1, "destination": "korea"},
            {"usage_gib": 1, "destination": "unknown"},
            {"usage_gib": 1, "destination": "korea", "hours": 745},
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    estimate_first_node_month(**kwargs)

    def test_review_never_claims_authenticated_or_server_evidence(self):
        review = build_cost_review()
        self.assertEqual(review["decision"], "DO_NOT_CREATE_UNTIL_AUTHENTICATED_CONSOLE_READBACK")
        self.assertIn("no authenticated billing", review["evidence_level"])
        self.assertFalse(review["contains_secrets"])

    def test_cli_creates_json_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_gcp_cost_") as temp:
            output = pathlib.Path(temp) / "review.json"
            command = [
                sys.executable,
                "-X",
                "utf8",
                str(ROOT / "70_TOOLS" / "run_gcp_cost_review.py"),
                "--output",
                str(output),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "FreeFlexVPNGCPCostReviewV1")
            before = output.read_bytes()
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPCostReviewTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP 비용 검토 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
