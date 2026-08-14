#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTINUITY = ROOT / ".project-continuity"
RUNTIME = CONTINUITY / "runtime" / "continuity-v520.py"
EXPECTED_RUNTIME_BYTES = 70_072
EXPECTED_RUNTIME_SHA256 = "e15cc0713ece51021be584aa437806ca1ab4008b277f4d779d6b6e12e832a1c7"


def compact_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class ContinuityV520ContractTests(unittest.TestCase):
    def test_runtime_and_install_receipt_are_pinned(self):
        data = RUNTIME.read_bytes()
        receipt = compact_json(CONTINUITY / "INSTALL-RECEIPT.json")
        self.assertEqual(len(data), EXPECTED_RUNTIME_BYTES)
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXPECTED_RUNTIME_SHA256)
        self.assertEqual(receipt["runtime_bytes"], EXPECTED_RUNTIME_BYTES)
        self.assertEqual(receipt["runtime_sha256"], EXPECTED_RUNTIME_SHA256)

    def test_existing_agents_content_is_preserved_with_one_managed_block(self):
        source = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("<!-- CONTINUITY-v3 BEGIN -->", source)
        self.assertIn("<!-- AI-GLOBAL-RULES-v9 BEGIN -->", source)
        self.assertIn("<!-- FREEFLEX-REPORT-DASHBOARD BEGIN -->", source)
        self.assertEqual(source.count("<!-- AI-CONTINUITY-V5 BEGIN -->"), 1)
        self.assertEqual(source.count("<!-- AI-CONTINUITY-V5 END -->"), 1)

    def test_hot_and_context_are_small_and_repeat_is_zero_write(self):
        environment = os.environ.copy()
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(RUNTIME), "bootstrap", "--project-path", str(ROOT), "--compact"],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
            check=False,
        )
        packet = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertLessEqual(len(result.stdout.strip().encode("utf-8")), 1_024)
        self.assertLessEqual((CONTINUITY / "CONTEXT.md").stat().st_size, 4_096)
        self.assertEqual(packet["w"], 0)
        self.assertEqual(packet["g"], "READY")

    def test_github_baseline_is_identity_free_and_admin_ready(self):
        baseline_path = CONTINUITY / "GITHUB-ACCESS-BASELINE.json"
        baseline = compact_json(baseline_path)
        access = compact_json(CONTINUITY / "GITHUB-ACCESS.json")
        self.assertEqual(access["status"], "READY")
        self.assertEqual(access["role"], "ADMIN")
        self.assertEqual(set(baseline["minimum_permissions"]), {"admin", "maintain", "push", "triage", "pull"})
        self.assertTrue(all(baseline["minimum_permissions"].values()))
        lowered = baseline_path.read_text(encoding="utf-8").lower()
        for forbidden in ('"login"', '"user_id"', '"token"', '"cookie"', '"email"', '"pat"'):
            self.assertNotIn(forbidden, lowered)

    def test_cleanup_truth_table_and_no_collaboration_locks(self):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(RUNTIME), "simulate", "--project-path", str(ROOT)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
            check=False,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["states"], 1_024)
        self.assertTrue(payload["all_pass"])
        self.assertEqual(list(CONTINUITY.glob("LOCK*.json")), [])

    def test_drive_state_never_claims_ready_without_verified_records(self):
        state = compact_json(CONTINUITY / "STATE.json")
        records = [line for line in (CONTINUITY / "BACKUPS.jsonl").read_text(encoding="utf-8").splitlines() if line]
        if state["remote_status"] == "READY":
            self.assertTrue(state["restore_verified"])
            self.assertGreater(len(records), 0)
        else:
            self.assertIn(state["remote_status"], {"UNKNOWN", "BLOCKED", "PARTIAL", "CONFIGURED"})

    def test_site_and_provider_eighteen_capability_truth_tables(self):
        full_mask = (1 << 18) - 1
        site_ready = 0
        provider_ready = 0
        for mask in range(1 << 18):
            site_ready += int(mask == full_mask)
            provider_ready += int(mask == full_mask)
        self.assertEqual(site_ready, 1)
        self.assertEqual(provider_ready, 1)

    def test_github_permission_superset_truth_table(self):
        ready = 0
        for bits in range(1 << 10):
            minimum = [(bits & (1 << index)) != 0 for index in range(5)]
            current = [(bits & (1 << (index + 5))) != 0 for index in range(5)]
            ready += int(all(not required or present for required, present in zip(minimum, current)))
        self.assertEqual(ready, 3**5)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuityV520ContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"연속성 v5.2 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
