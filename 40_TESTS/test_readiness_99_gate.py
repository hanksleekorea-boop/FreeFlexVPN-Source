#!/usr/bin/env python3
"""99% 목표 게이트가 자기보고가 아닌 외부 증거를 요구하는지 확인한다."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
from app.readiness_99_gate import (  # noqa: E402
    DEVELOPMENT_GATES,
    SCHEMA,
    Readiness99EvidenceError,
    verify_and_evaluate_readiness_99,
    verify_development_evidence,
)

SPEC = importlib.util.spec_from_file_location("platform_release_fixtures", ROOT / "40_TESTS" / "test_platform_release_evidence.py")
assert SPEC and SPEC.loader
FIXTURES = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FIXTURES
SPEC.loader.exec_module(FIXTURES)


def development_bundle(folder: pathlib.Path, *, all_pass: bool = True) -> pathlib.Path:
    states = {gate: "pass" if all_pass else "not_run" for gate in DEVELOPMENT_GATES}
    proof = folder / "development-proof.txt"
    proof.write_text("deidentified development verification\n", encoding="utf-8")
    payload = {
        "schema": SCHEMA,
        "verified_at": FIXTURES.STAMP,
        "gates": states,
        "artifacts": [{
            "artifact_id": "development-proof-001",
            "kind": "receipt",
            "gate_ids": list(DEVELOPMENT_GATES) if all_pass else ["REGRESSION"],
            "contains_secret": False,
            "contains_identifier": False,
            "path": proof.name,
            "sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
        }],
    }
    target = folder / "development-evidence.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class Readiness99GateTests(unittest.TestCase):
    def test_all_external_evidence_reaches_99_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            mobile_dir, pc_dir, ops_dir, dev_dir = (root / name for name in ("mobile", "pc", "ops", "development"))
            for folder in (mobile_dir, pc_dir, ops_dir, dev_dir): folder.mkdir()
            result = verify_and_evaluate_readiness_99(
                mobile_receipt=FIXTURES._platform_receipt(mobile_dir, "android"),
                pc_receipt=FIXTURES._platform_receipt(pc_dir, "windows"),
                operations_bundle=FIXTURES._operations_bundle(ops_dir),
                development_bundle=development_bundle(dev_dir), project_root=ROOT, now=FIXTURES.NOW,
            )
            self.assertTrue(result["target_99_ready"])
            self.assertEqual(result["areas"], {"mobile": 100, "pc": 100, "commercial": 100, "development": 100})

    def test_missing_development_evidence_blocks_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            verified = verify_development_evidence(development_bundle(pathlib.Path(temporary), all_pass=False), project_root=ROOT, now=FIXTURES.NOW)
            self.assertFalse(verified.ready)

    def test_development_template_is_valid_but_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "development-evidence"
            completed = __import__("subprocess").run(
                [sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "init_external_evidence_bundle.py"), "development", "--output-dir", str(output)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(verify_development_evidence(output / "development-evidence.json", project_root=ROOT).ready)

    def test_pass_without_matching_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = development_bundle(pathlib.Path(temporary))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifacts"][0]["gate_ids"] = ["REGRESSION"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Readiness99EvidenceError, "원본 증거"):
                verify_development_evidence(path, project_root=ROOT, now=FIXTURES.NOW)

    def test_sensitive_field_and_project_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = development_bundle(pathlib.Path(temporary))
            payload = json.loads(path.read_text(encoding="utf-8")); payload["token"] = "redacted"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Readiness99EvidenceError, "민감"):
                verify_development_evidence(path, project_root=ROOT, now=FIXTURES.NOW)
        with self.assertRaisesRegex(Readiness99EvidenceError, "프로젝트 밖"):
            verify_development_evidence(ROOT / "MANIFEST.md", project_root=ROOT, now=FIXTURES.NOW)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Readiness99GateTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"99% 준비도 게이트 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
