#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "70_TOOLS" / "verify_account_continuation.py"
HANDOFF = ROOT / "00_START" / "NEW_CODEX_ACCOUNT_HANDOFF.md"
SPEC = importlib.util.spec_from_file_location("verify_account_continuation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AccountContinuationContractTests(unittest.TestCase):
    def test_handoff_resolves_the_current_same_pc_worktree_portably(self):
        source = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("$project = (Get-Location).Path", source)
        self.assertIn("$env:USERPROFILE", source)
        self.assertNotIn(r"C:\Users\x13", source)
        self.assertNotIn("handoff-check-cp949", source)
        self.assertIn("verify_account_continuation.py", source)

    def test_handoff_does_not_promise_account_or_provider_inheritance(self):
        source = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("Codex 데스크톱 앱 안의 계정 전환은 지원되지 않는다", source)
        self.assertIn("권한은 새 계정에 자동 승계되지 않습니다", source)
        self.assertIn("full_site_development: ready", source)

    def test_helper_contract_is_pinned(self):
        self.assertEqual(MODULE.EXPECTED_HELPER_BYTES, 11_497)
        self.assertEqual(MODULE.EXPECTED_HELPER_SHA256, "02fb55391fdb021e114a2457c68ef26b1a4056166b6f546b7314e50dd78de921")

    def test_expired_permission_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "permission.json"
            path.write_text('{"status":"complete","expires_epoch":10,"capabilities":["source_read"]}', encoding="utf-8")
            result = MODULE.evaluate_permission(path, now=11)
        self.assertEqual(result["status"], "expired")

    def test_verifier_is_read_only_and_blocks_destructive_shortcuts(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"--mode", "ReadOnly"', source)
        self.assertIn('environment["GIT_OPTIONAL_LOCKS"] = "0"', source)
        for forbidden in ("reset --hard", "clean -fd", "push --force", "git stash"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AccountContinuationContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"계정 전환 연속성 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
