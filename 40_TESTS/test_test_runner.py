#!/usr/bin/env python3
"""전체 회귀 실행기의 의존성 사전진단 계약."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("freeflex_run_all_tests", ROOT / "70_TOOLS" / "run_all_tests.py")
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class TestRunnerTests(unittest.TestCase):
    def test_all_required_modules_present(self):
        with mock.patch.object(RUNNER.importlib.util, "find_spec", return_value=object()):
            self.assertEqual(RUNNER.missing_test_dependencies(), [])

    def test_missing_modules_are_reported_with_purpose(self):
        present = {"numpy"}
        with mock.patch.object(
            RUNNER.importlib.util,
            "find_spec",
            side_effect=lambda module: object() if module in present else None,
        ):
            self.assertEqual(
                RUNNER.missing_test_dependencies(),
                [
                    ("playwright", "브라우저 계약 검사"),
                    ("cv2", "QR 디코딩 검사"),
                    ("qrcode", "QR 생성 검사"),
                    ("PIL", "QR PNG 생성 검사"),
                ],
            )

    def test_version_ranges_reject_opencv_5(self):
        versions = {"cv2": (5, 0), "qrcode": (8, 2), "PIL": (12, 3)}
        with mock.patch.object(RUNNER.importlib.util, "find_spec", return_value=object()), mock.patch.object(
            RUNNER, "_installed_version", side_effect=lambda module: versions[module]
        ):
            issues = RUNNER.incompatible_test_dependencies()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], "cv2")

    def test_declared_version_ranges_accept_supported_stack(self):
        versions = {"cv2": (4, 12), "qrcode": (8, 2), "PIL": (12, 3)}
        with mock.patch.object(RUNNER.importlib.util, "find_spec", return_value=object()), mock.patch.object(
            RUNNER, "_installed_version", side_effect=lambda module: versions[module]
        ):
            self.assertEqual(RUNNER.incompatible_test_dependencies(), [])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestRunnerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"전체 회귀 실행기 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
