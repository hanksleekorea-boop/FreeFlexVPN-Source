#!/usr/bin/env python3
"""Reproducible progress dashboard contracts."""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "70_TOOLS" / "progress_dashboard.py"
CONFIG = ROOT / "10_STATE" / "progress_dashboard_v2.15.json"
spec = importlib.util.spec_from_file_location("progress_dashboard", TOOL)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ProgressDashboardTests(unittest.TestCase):
    def config(self):
        return json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_baseline_generates_evidence_bound_progress(self):
        model = module.build_model(self.config(), ROOT)
        self.assertEqual(model["completed_milestones"], 7)
        self.assertEqual(model["total_milestones"], 12)
        self.assertEqual(model["remaining_milestones"], 5)
        self.assertEqual(model["actual_percent"], 58.3)
        self.assertEqual(model["planned_percent"], 58.3)
        self.assertEqual(model["schedule_delta_days"], 0.0)
        self.assertEqual(model["eta"]["initial_date"], "2026-08-12")
        self.assertEqual(model["eta"]["status"], "blocked_zero_velocity")
        self.assertIsNone(model["eta"]["current_date"])
        self.assertEqual(model["public_app"]["qr_verification"], "decoded_exact_match")
        self.assertEqual(len(model["roadmap"]), 3)

    def test_eta_is_generated_only_from_measured_recent_speed(self):
        config = self.config()
        config["progress_history"][0]["actual_percent"] = 50.0
        model = module.build_model(config, ROOT)
        self.assertEqual(model["eta"]["status"], "projected")
        self.assertEqual(model["eta"]["speed_percent_per_day"], 8.3)
        self.assertEqual(model["eta"]["current_date"], "2026-08-09")
        self.assertEqual(model["eta"]["deviation_days"], -3)

    def test_qr_payload_or_file_mismatch_is_rejected(self):
        config = self.config()
        config["public_app"]["url"] = "https://example.invalid/not-the-decoded-url"
        with self.assertRaises(module.DashboardError):
            module.build_model(config, ROOT)

    def test_invalid_weight_and_area_count_stop_before_render(self):
        bad_weight = self.config()
        bad_weight["areas"][0]["weight"] = 9
        with self.assertRaises(module.DashboardError):
            module.build_model(bad_weight, ROOT)
        bad_count = self.config()
        bad_count["areas"] = bad_count["areas"][:1]
        with self.assertRaises(module.DashboardError):
            module.build_model(bad_count, ROOT)

    def test_completed_milestone_requires_existing_evidence(self):
        config = self.config()
        config["milestones"][0]["evidence"] = ["10_STATE/DOES_NOT_EXIST.json"]
        with self.assertRaises(module.DashboardError):
            module.build_model(config, ROOT)

    def test_html_is_self_contained_accessible_and_embeds_metrics(self):
        rendered = module.render_html(module.build_model(self.config(), ROOT))
        self.assertIn("prefers-color-scheme:dark", rendered)
        self.assertIn("data-theme='dark'", rendered)
        self.assertIn("tabular-nums", rendered)
        self.assertIn("58.3%", rendered)
        self.assertIn("당초 예정일", rendered)
        self.assertIn("현재 예상일", rendered)
        self.assertIn("현재 예상선: 측정 없음", rendered)
        self.assertIn("다음 출시 로드맵", rendered)
        self.assertIn("병목 경보", rendered)
        self.assertIn("원인 계층", rendered)
        self.assertIn("방치 시 영향", rendered)
        self.assertIn("용어 원장", rendered)
        self.assertIn("data:image/png;base64,", rendered)
        self.assertIn("https://hanksleekorea-boop.github.io/FreeFlexVPN/app.html", rendered)
        self.assertNotIn("<link ", rendered)
        self.assertNotIn("<script src=", rendered)

    def test_cli_writes_atomic_pair_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_progress_") as temp:
            html_path = pathlib.Path(temp) / "dashboard.html"
            summary_path = pathlib.Path(temp) / "summary.json"
            command = [sys.executable, "-X", "utf8", str(TOOL), "--config", str(CONFIG), "--output", str(html_path), "--summary-output", str(summary_path)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["actual_percent"], 58.3)
            self.assertEqual(summary["eta"]["status"], "blocked_zero_velocity")
            self.assertEqual(summary["public_app"]["qr_verification"], "decoded_exact_match")
            before = (html_path.read_bytes(), summary_path.read_bytes())
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(before, (html_path.read_bytes(), summary_path.read_bytes()))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProgressDashboardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"진척 대시보드 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
