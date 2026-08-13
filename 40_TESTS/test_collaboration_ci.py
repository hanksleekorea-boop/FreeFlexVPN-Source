#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


class CollaborationCIContractTests(unittest.TestCase):
    def test_fork_safe_event_and_no_operational_secret_reference(self):
        self.assertIn("pull_request:", WORKFLOW)
        self.assertNotIn("pull_request_target", WORKFLOW)
        self.assertNotIn("${{ secrets.", WORKFLOW)

    def test_production_and_integration_branches_are_covered(self):
        self.assertIn("'feature/**'", WORKFLOW)
        self.assertIn("'shared-development'", WORKFLOW)
        self.assertIn("Run full verification", WORKFLOW)
        self.assertIn("Scan tracked source for secrets", WORKFLOW)

    def test_artifact_is_uploaded_and_attested_only_on_push(self):
        self.assertIn("actions/upload-artifact@v4", WORKFLOW)
        self.assertIn("actions/attest-build-provenance@v3", WORKFLOW)
        self.assertIn("if: github.event_name == 'push'", WORKFLOW)
        self.assertIn("subject-path: freeflexvpn-static.zip", WORKFLOW)

    def test_workflow_permissions_are_explicit_and_minimal_for_attestation(self):
        self.assertIn("contents: read", WORKFLOW)
        self.assertIn("id-token: write", WORKFLOW)
        self.assertIn("attestations: write", WORKFLOW)
        self.assertNotIn("contents: write", WORKFLOW)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollaborationCIContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공동개발 CI 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
