#!/usr/bin/env python3
"""목표 OS 안전·재연결 계약과 거짓 완료 방지 검사."""
from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.safety_contract import REQUIRED_CHECKS, evaluate_os_run, evaluate_release_matrix  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)


def run(os_family="android", **changes):
    value = {
        "candidate_id": "R6-candidate-001",
        "device_id": f"device-{os_family}-001",
        "os_family": os_family,
        "os_version": "test-version",
        "server_id": "de-fra-01",
        "run_at": NOW,
        "origin": "actual_device",
        "checks": {name: True for name in REQUIRED_CHECKS},
    }
    value.update(changes)
    return value


class SafetyContractTests(unittest.TestCase):
    def test_all_required_checks_on_actual_device_pass_one_os(self):
        result = evaluate_os_run(run())
        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "passed")

    def test_each_safety_failure_blocks_pass_negative_control(self):
        for name in REQUIRED_CHECKS:
            checks = {item: True for item in REQUIRED_CHECKS}
            checks[name] = False
            with self.subTest(name=name):
                result = evaluate_os_run(run(checks=checks))
                self.assertFalse(result["passed"])
                self.assertEqual(result["failed_checks"], [name])

    def test_missing_or_unknown_check_is_unknown_not_pass(self):
        checks = {name: True for name in REQUIRED_CHECKS if name != "ipv6_safe"}
        result = evaluate_os_run(run(checks=checks))
        self.assertEqual(result["status"], "unknown")
        self.assertIn("ipv6_safe", result["unknown_checks"])

    def test_simulation_cannot_be_device_evidence(self):
        result = evaluate_os_run(run(origin="synthetic"))
        self.assertEqual(result["status"], "adapter_or_demo")
        self.assertFalse(result["passed"])
        self.assertIn("실제 기기 증거가 아닙니다", result["evidence_note"])

    def test_full_same_candidate_three_os_matrix_passes(self):
        matrix = evaluate_release_matrix(
            [run("ios"), run("android"), run("windows")], candidate_id="R6-candidate-001"
        )
        self.assertTrue(matrix["ready"])
        self.assertEqual(matrix["passed_os"], ["ios", "android", "windows"])

    def test_missing_target_os_blocks_matrix(self):
        matrix = evaluate_release_matrix(
            [run("ios"), run("android")], candidate_id="R6-candidate-001"
        )
        self.assertFalse(matrix["ready"])
        self.assertEqual(matrix["missing_os"], ["windows"])

    def test_candidate_mismatch_blocks_evidence_reuse(self):
        matrix = evaluate_release_matrix(
            [run("ios"), run("android"), run("windows", candidate_id="old-candidate")],
            candidate_id="R6-candidate-001",
        )
        self.assertFalse(matrix["ready"])
        self.assertEqual(matrix["mismatched_candidate_os"], ["windows"])

    def test_undefined_check_and_naive_time_are_rejected(self):
        checks = {name: True for name in REQUIRED_CHECKS} | {"magic_safe": True}
        with self.assertRaises(ValueError):
            evaluate_os_run(run(checks=checks))
        with self.assertRaises(ValueError):
            evaluate_os_run(run(run_at=datetime(2026, 8, 2)))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SafetyContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"OS 안전 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
