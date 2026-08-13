#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "70_TOOLS" / "grant_contributor_access.ps1"
SETUP = ROOT / "00_START" / "NEW_PC_SETUP.md"
NO_LOCK = ROOT / ".project-continuity" / "NO_LOCK_POLICY.md"


class ContributorAccessContractTests(unittest.TestCase):
    def test_grant_is_identity_bound_and_plan_only_by_default(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[Parameter(Mandatory = $true)]", source)
        self.assertIn("[switch]$Execute", source)
        self.assertIn("PLAN_ONLY", source)
        self.assertIn("permission=push", source)

    def test_site_write_is_bucket_scoped_without_anonymous_or_shared_secret(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("roles/storage.objectAdmin", source)
        self.assertIn("storage buckets add-iam-policy-binding", source)
        self.assertNotIn("allUsers", source)
        self.assertNotIn("allAuthenticatedUsers", source)
        self.assertNotIn("token=", source.lower())

    def test_setup_explains_acceptance_and_separate_cloud_identity(self):
        source = SETUP.read_text(encoding="utf-8")
        self.assertIn("grant_contributor_access.ps1", source)
        self.assertIn("초대 수락", source)
        self.assertIn("Google IAM 주체", source)

    def test_no_lock_policy_is_explicit(self):
        source = NO_LOCK.read_text(encoding="utf-8")
        self.assertIn("협업 잠금 파일을 생성하지 않는다", source)
        self.assertIn("Git 상태", source)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContributorAccessContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"참여자 접근 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
