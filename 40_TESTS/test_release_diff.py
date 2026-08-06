#!/usr/bin/env python3
"""공개 셸과 로컬 강화 후보의 증거·배포 경계 검사."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "70_TOOLS"))

from build_release_diff import build_release_diff  # noqa: E402


class ReleaseDiffTests(unittest.TestCase):
    def setUp(self):
        self.ledger_path = ROOT / "10_STATE" / "RELEASE_DIFF_V2_21_PC_PUBLIC_2026-08-04.json"
        self.ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def test_pc_shell_matches_verified_public_v25(self):
        value = self.ledger
        self.assertTrue(value["app_shell"]["equal_to_verified_public_v2_5"])
        self.assertIn("PC-2·3", value["app_shell"]["visible_change"])

    def test_local_candidate_is_publicly_deployed(self):
        value = self.ledger
        self.assertTrue(value["to"]["deployed"])
        self.assertEqual(value["app_shell"]["deployment_action"], "completed_and_publicly_verified")
        self.assertEqual(value["to"]["github_actions_conclusion"], "success")

    def test_progress_stays_at_evidence_gated_baseline(self):
        value = self.ledger
        self.assertEqual(value["to"]["progress_percent"], 58.3)
        self.assertFalse(value["to"]["progress_changed"])

    def test_each_local_change_has_hashes_and_explicit_public_effect(self):
        value = self.ledger
        for change in value["local_changes"]:
            if change["area"] == "pc_responsive_web_train":
                self.assertEqual(change["public_effect"], "deployed_v2_5")
            else:
                self.assertEqual(change["public_effect"], "none")
            self.assertTrue(change["files"])
            for record in change["files"]:
                self.assertRegex(record["sha256"], r"^[0-9A-F]{64}$")
                self.assertGreater(record["bytes"], 0)

    def test_missing_real_world_layers_remain_visible(self):
        value = self.ledger
        joined = " ".join(value["still_missing"])
        for phrase in ("GCP S-1", "actual VPN server", "actual device", "independent user", "payment"):
            self.assertIn(phrase, joined)

    def test_public_claim_boundary_is_unambiguous(self):
        value = self.ledger
        self.assertIn("UI 앱 셸 v2.5", value["claim_boundary"])
        self.assertIn("실제 VPN 연결 서비스가 아닙니다", value["claim_boundary"])

    def test_historical_ledger_is_immutable_after_next_release_work(self):
        self.assertTrue(self.ledger_path.is_file())
        current = build_release_diff()
        self.assertEqual(self.ledger["schema"], current["schema"])
        self.assertNotEqual(self.ledger["app_shell"]["local_deploy"]["sha256"], current["app_shell"]["local_deploy"]["sha256"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReleaseDiffTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"릴리스 차이 원장 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
