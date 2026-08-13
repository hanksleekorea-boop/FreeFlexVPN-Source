#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class OpenCollaborationContractTests(unittest.TestCase):
    def test_public_contribution_paths_are_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for phrase in ("복제", "포크", "Pull Request", "잠금 없이"):
            self.assertIn(phrase, readme + contributing)

    def test_universal_direct_push_is_not_falsely_promised(self):
        source = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("불특정 로그인 사용자 전체에 직접 push 권한을 주는 GitHub 권한은 없습니다", source)
        self.assertIn("기능 브랜치", source)

    def test_pr_template_requires_no_lock_and_secret_hygiene(self):
        source = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        self.assertIn("LOCK*.json", source)
        self.assertIn("개인키", source)
        self.assertIn("run_all_tests.py", source)

    def test_security_policy_uses_private_reporting(self):
        source = (ROOT / ".github" / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("비공개 취약점 신고", source)
        self.assertIn("공개 협업", source)

    def test_current_onboarding_does_not_claim_repository_is_private(self):
        current_files = (
            ROOT / "00_START" / "RECEIVER_HANDOFF_PROMPT.md",
            ROOT / "00_START" / "NEW_PC_SETUP.md",
            ROOT / "00_START" / "NEW_CODEX_ACCOUNT_HANDOFF.md",
            ROOT / "00_START" / "시작하세요.md",
            ROOT / "70_TOOLS" / "create_ai_handoff.py",
        )
        source = "\n".join(path.read_text(encoding="utf-8") for path in current_files)
        for stale in (
            "원격은 비공개",
            "원격 원본은 비공개",
            "최신 비공개 GitHub Release",
            "예상 비공개 인계 Release",
        ):
            self.assertNotIn(stale, source)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OpenCollaborationContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공개 협업 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
