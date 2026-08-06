#!/usr/bin/env python3
"""GCP 비용 확인 도우미의 단일 HTML·저장 안전성·가격 동기화 계약."""
from __future__ import annotations

import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
sys.path.insert(0, str(ROOT / "70_TOOLS"))

from infra.gcp_cost_review import DESTINATION_RATES_USD_PER_GIB, GCPPriceSnapshot  # noqa: E402
from build_gcp_billing_review import build_html  # noqa: E402


class GCPBillingReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build_html().decode("utf-8")

    def test_build_is_self_contained_and_has_no_placeholders(self):
        self.assertNotIn("__MANIFEST", self.html)
        self.assertNotIn("__PRICE_", self.html)
        self.assertNotRegex(self.html, r"<(?:script|img)[^>]+(?:src|href)=[\"']https?://")
        self.assertIn("data:application/manifest+json;base64,", self.html)

    def test_manifest_contains_png_icons_and_install_contract(self):
        match = re.search(r'data:application/manifest\+json;base64,([^\"]+)', self.html)
        self.assertIsNotNone(match)
        manifest = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
        self.assertEqual([icon["sizes"] for icon in manifest["icons"]], ["192x192", "512x512"])
        self.assertTrue(all(icon["src"].startswith("data:image/png;base64,") for icon in manifest["icons"]))
        for token in ("beforeinstallprompt", "appinstalled", "display-mode:standalone", "86400000"):
            self.assertIn(token, self.html)

    def test_price_payload_matches_python_source_of_truth(self):
        match = re.search(r'<script id="price-data" type="application/json">([^<]+)</script>', self.html)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["rates"], DESTINATION_RATES_USD_PER_GIB)
        self.assertEqual(payload["external_ipv4_usd_per_hour"], GCPPriceSnapshot().external_ipv4_usd_per_hour)

    def test_storage_failure_keeps_memory_and_warns_honestly(self):
        for token in ("forceStorageFailure", "memoryState=value", "현재 화면 메모리에서만 유지 중", "JSON으로 내보내세요"):
            self.assertIn(token, self.html)
        self.assertIn("기존 입력은 유지했습니다", self.html)

    def test_six_checks_and_no_deploy_action(self):
        self.assertEqual(self.html.count('data-check="'), 6)
        self.assertIn("읽기 전용 사전점검 준비", self.html)
        self.assertNotIn("gcloud compute instances create", self.html)
        self.assertNotIn("Billing Account ID</label><input", self.html)

    def test_export_import_and_privacy_contract(self):
        for token in ("JSON 내보내기", "JSON 가져오기", "contains_secrets:false", "비밀번호·결제수단·Billing Account ID·토큰"):
            self.assertIn(token, self.html)

    def test_cli_writes_once_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_gcp_billing_") as temp:
            output = pathlib.Path(temp) / "helper.html"
            command = [sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "build_gcp_billing_review.py"), "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            before = output.read_bytes()
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPBillingReviewTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP 비용 확인 도우미 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
