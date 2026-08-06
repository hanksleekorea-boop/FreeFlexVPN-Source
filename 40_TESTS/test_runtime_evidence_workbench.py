#!/usr/bin/env python3
"""v2.17 증거 번들 작성기의 로컬 전용·해시·덮어쓰기 방지 계약."""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "70_TOOLS"))

from build_runtime_evidence_workbench import build_html  # noqa: E402


class RuntimeEvidenceWorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build_html().decode("utf-8")

    def test_is_self_contained_local_only_and_versioned(self):
        self.assertNotIn("__SOURCE_SHA256__", self.html)
        self.assertNotRegex(self.html, r"<(?:script|img|link)[^>]+(?:src|href)=[\"']https?://")
        self.assertNotIn("fetch(", self.html)
        for token in ("후보 v2.17", "LOCAL ONLY", "전송 0건", "Content-Security-Policy"):
            self.assertIn(token, self.html)

    def test_all_ten_tests_and_bundle_v2_contract_are_present(self):
        self.assertIn("Array.from({length:10}", self.html)
        self.assertIn("FreeFlexVPNRuntimeEvidenceBundleV2", self.html)
        self.assertIn("origin:'actual_target'", self.html)
        self.assertIn("contains_secret:false", self.html)
        self.assertIn("crypto.subtle.digest('SHA-256'", self.html)
        self.assertIn("T10:'consent_record'", self.html)
        self.assertIn("seenHashes.has(digest)", self.html)

    def test_unicode_file_names_are_preserved(self):
        self.assertIn("path:file.name", self.html)
        self.assertNotIn("cleanName", self.html)

    def test_honest_boundary_and_privacy_controls_are_visible(self):
        for token in ("개인키·토큰·결제수단·실명", "실제 출시 판정 전", "비밀값 제거 확인", "원본 파일들과 같은 폴더"):
            self.assertIn(token, self.html)

    def test_source_hash_is_embedded(self):
        match = re.search(r'name="freeflex-source-sha256" content="([0-9a-f]{64})"', self.html)
        self.assertIsNotNone(match)

    def test_cli_writes_once_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_runtime_workbench_") as temporary:
            output = pathlib.Path(temporary) / "workbench.html"
            command = [sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "build_runtime_evidence_workbench.py"), "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            before = output.read_bytes()
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(before, output.read_bytes())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeEvidenceWorkbenchTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"v2.17 증거 번들 작성기 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
