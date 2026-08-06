#!/usr/bin/env python3
"""T1~T10 외부 원본 증거 번들의 무결성·경계 음성 대조."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
sys.path.insert(0, str(ROOT / "40_TESTS"))

from app.runtime_acceptance import TEST_IDS, evaluate_runtime_acceptance  # noqa: E402
from app.runtime_evidence import EvidenceBundleError, SCHEMA, verify_evidence_bundle  # noqa: E402
from test_runtime_acceptance import CANDIDATE, full_evidence  # noqa: E402


RUN_AT = "2026-08-03T12:00:00+00:00"


def _write_bundle(folder: pathlib.Path, *, run_at: str = RUN_AT) -> pathlib.Path:
    evidence = full_evidence()
    evidence["run_at"] = run_at
    kinds = {
        "T1": "log", "T2": "measurement", "T3": "pcap_summary", "T4": "measurement",
        "T5": "log", "T6": "log", "T7": "log", "T8": "pcap_summary",
        "T9": "log", "T10": "consent_record",
    }
    artifacts = []
    for test_id in TEST_IDS:
        artifact = folder / f"{test_id.lower()}-증거.txt"
        artifact.write_text(f"deidentified runtime evidence for {test_id}\n", encoding="utf-8")
        artifacts.append({
            "artifact_id": f"{test_id.lower()}-evidence-001",
            "candidate_id": CANDIDATE,
            "kind": kinds[test_id],
            "test_ids": [test_id],
            "captured_at": run_at,
            "contains_secret": False,
            "path": artifact.name,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        })
    payload = {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE,
        "run_at": run_at,
        "evidence": evidence,
        "artifacts": artifacts,
    }
    path = folder / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class RuntimeEvidenceTests(unittest.TestCase):
    def test_verified_external_bundle_can_pass_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_bundle(pathlib.Path(temporary))
            evidence, verified = verify_evidence_bundle(
                path, project_root=ROOT, now=datetime(2026, 8, 3, 12, 1, tzinfo=timezone.utc)
            )
            result = evaluate_runtime_acceptance(evidence, verified_artifacts=verified)
            self.assertTrue(result["ready"])
            self.assertTrue(result["artifacts_verified"])
            self.assertEqual(result["artifact_count"], 10)

    def test_changed_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _write_bundle(folder)
            (folder / "t1-증거.txt").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(EvidenceBundleError, "SHA-256"):
                verify_evidence_bundle(path, project_root=ROOT)

    def test_missing_test_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_bundle(pathlib.Path(temporary))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifacts"] = [item for item in payload["artifacts"] if item["test_ids"] != ["T10"]]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(EvidenceBundleError, "T10"):
                verify_evidence_bundle(path, project_root=ROOT)

    def test_candidate_mismatch_duplicate_id_and_secret_unknown_are_rejected(self):
        mutations = (
            lambda value: value["artifacts"][0].update(candidate_id="other-candidate"),
            lambda value: value["artifacts"].append(deepcopy(value["artifacts"][0])),
            lambda value: value["artifacts"][0].update(contains_secret=True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    path = _write_bundle(pathlib.Path(temporary))
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    mutation(payload)
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(EvidenceBundleError):
                        verify_evidence_bundle(path, project_root=ROOT)

    def test_parent_traversal_absolute_and_missing_files_are_rejected(self):
        replacements = ("../runtime.log", str(ROOT / "MANIFEST.md"), "missing.log")
        for replacement in replacements:
            with self.subTest(path=replacement):
                with tempfile.TemporaryDirectory() as temporary:
                    path = _write_bundle(pathlib.Path(temporary))
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["artifacts"][0]["path"] = replacement
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(EvidenceBundleError):
                        verify_evidence_bundle(path, project_root=ROOT)

    def test_wrong_kind_and_duplicate_content_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_bundle(pathlib.Path(temporary))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifacts"][9]["kind"] = "log"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(EvidenceBundleError, "kind"):
                verify_evidence_bundle(path, project_root=ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _write_bundle(folder)
            payload = json.loads(path.read_text(encoding="utf-8"))
            duplicate = (folder / payload["artifacts"][0]["path"]).read_bytes()
            second = folder / payload["artifacts"][1]["path"]
            second.write_bytes(duplicate)
            payload["artifacts"][1]["sha256"] = hashlib.sha256(duplicate).hexdigest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(EvidenceBundleError, "중복"):
                verify_evidence_bundle(path, project_root=ROOT)

    def test_project_resident_bundle_is_rejected(self):
        with self.assertRaisesRegex(EvidenceBundleError, "프로젝트 밖"):
            verify_evidence_bundle(ROOT / "10_STATE" / "LOCAL_EVIDENCE_V2_16_R2_2026-08-03.json", project_root=ROOT)

    def test_cli_passes_verified_bundle_without_leaking_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_at = datetime.now(timezone.utc).isoformat()
            path = _write_bundle(pathlib.Path(temporary), run_at=run_at)
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "evaluate_runtime_acceptance.py"), str(path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ready"])
            self.assertEqual(result["artifact_count"], 10)
            self.assertNotIn(temporary, completed.stdout)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeEvidenceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"T1~T10 원본 증거 무결성 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
