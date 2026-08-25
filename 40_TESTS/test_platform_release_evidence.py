#!/usr/bin/env python3
"""실제 플랫폼 영수증과 95% 출시 증거 게이트의 양·음성 대조."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.platform_evidence import (  # noqa: E402
    OBSERVATION_IDS,
    SCHEMA as PLATFORM_SCHEMA,
    PlatformEvidenceError,
    summarize_platform_evidence,
    verify_platform_evidence,
)
from app.release_95_gate import (  # noqa: E402
    OPERATIONS_GATES,
    SCHEMA as RELEASE_SCHEMA,
    Release95EvidenceError,
    evaluate_release_95,
    verify_operations_evidence,
)


NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
STAMP = NOW.isoformat()


def _artifact(folder: pathlib.Path, name: str, content: str) -> tuple[pathlib.Path, str]:
    path = folder / name
    path.write_text(content, encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _platform_receipt(
    folder: pathlib.Path,
    platform: str,
    *,
    full: bool = True,
    captured_at: str = STAMP,
) -> pathlib.Path:
    states = {item: ("pass" if full or item == "CLIENT_INSTALLED" else "not_run") for item in OBSERVATION_IDS}
    proof, digest = _artifact(folder, f"{platform}-proof.txt", f"deidentified {platform} device verification\n")
    covered = list(OBSERVATION_IDS) if full else ["CLIENT_INSTALLED"]
    payload = {
        "schema": PLATFORM_SCHEMA,
        "platform": platform,
        "captured_at": captured_at,
        "observations": states,
        "artifacts": [{
            "artifact_id": f"{platform}-proof-001",
            "kind": "measurement",
            "observation_ids": covered,
            "contains_secret": False,
            "contains_identifier": False,
            "path": proof.name,
            "sha256": digest,
        }],
    }
    receipt = folder / f"{platform}-receipt.json"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    return receipt


def _operations_bundle(folder: pathlib.Path, *, limited_release: str = "pass") -> pathlib.Path:
    states = {item: "pass" for item in OPERATIONS_GATES}
    states["LIMITED_RELEASE"] = limited_release
    proof, digest = _artifact(folder, "operations-proof.txt", "deidentified commercial operations verification\n")
    covered = [item for item, state in states.items() if state == "pass"]
    payload = {
        "schema": RELEASE_SCHEMA,
        "verified_at": STAMP,
        "gates": states,
        "artifacts": [{
            "artifact_id": "operations-proof-001",
            "kind": "receipt",
            "gate_ids": covered,
            "contains_secret": False,
            "contains_identifier": False,
            "path": proof.name,
            "sha256": digest,
        }],
    }
    bundle = folder / "operations.json"
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    return bundle


class PlatformEvidenceTests(unittest.TestCase):
    def test_external_platform_template_is_valid_but_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "android-evidence"
            completed = subprocess.run(
                [
                    sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "init_external_evidence_bundle.py"),
                    "platform", "--platform", "android", "--output-dir", str(output),
                ],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(json.loads(completed.stdout)["ready"])
            verified = verify_platform_evidence(output / "platform-evidence.json", project_root=ROOT)
            self.assertFalse(verified.connection_ready)
            self.assertFalse(verified.partial)

    def test_template_refuses_project_folder_and_nonempty_folder(self):
        project_output = ROOT / ".tools" / "should-not-create-evidence"
        completed = subprocess.run(
            [
                sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "init_external_evidence_bundle.py"),
                "platform", "--platform", "android", "--output-dir", str(project_output),
            ],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(project_output.exists())
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "occupied"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "init_external_evidence_bundle.py"),
                    "operations", "--output-dir", str(output),
                ],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "keep")
    def test_full_mobile_receipt_is_verified_without_identifiers(self):
        with tempfile.TemporaryDirectory() as temporary:
            verified = verify_platform_evidence(
                _platform_receipt(pathlib.Path(temporary), "android"), project_root=ROOT, now=NOW
            )
            result = summarize_platform_evidence(verified)
            self.assertTrue(result["connection_ready"])
            self.assertEqual(result["category"], "mobile")
            self.assertNotIn(temporary, json.dumps(result))

    def test_install_only_receipt_is_partial_and_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            verified = verify_platform_evidence(
                _platform_receipt(pathlib.Path(temporary), "android", full=False), project_root=ROOT, now=NOW
            )
            self.assertTrue(verified.partial)
            self.assertFalse(verified.connection_ready)

    def test_pass_without_artifact_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _platform_receipt(pathlib.Path(temporary), "windows", full=False)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["observations"]["PROFILE_IMPORTED"] = "pass"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PlatformEvidenceError):
                verify_platform_evidence(path, project_root=ROOT, now=NOW)

    def test_impossible_tunnel_sequence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _platform_receipt(pathlib.Path(temporary), "windows", full=False)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["observations"]["TUNNEL_CONNECTED"] = "pass"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PlatformEvidenceError, "프로필"):
                verify_platform_evidence(path, project_root=ROOT, now=NOW)

    def test_sensitive_field_and_network_address_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _platform_receipt(folder, "android")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["device_id"] = "redacted"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PlatformEvidenceError, "민감"):
                verify_platform_evidence(path, project_root=ROOT, now=NOW)
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _platform_receipt(folder, "android")
            payload = json.loads(path.read_text(encoding="utf-8"))
            proof = folder / payload["artifacts"][0]["path"]
            proof.write_text("network 192.0.2.1\n", encoding="utf-8")
            payload["artifacts"][0]["sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PlatformEvidenceError, "네트워크 주소"):
                verify_platform_evidence(path, project_root=ROOT, now=NOW)

    def test_changed_artifact_old_receipt_and_project_bundle_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _platform_receipt(folder, "android")
            payload = json.loads(path.read_text(encoding="utf-8"))
            (folder / payload["artifacts"][0]["path"]).write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(PlatformEvidenceError, "SHA-256"):
                verify_platform_evidence(path, project_root=ROOT, now=NOW)
        with tempfile.TemporaryDirectory() as temporary:
            path = _platform_receipt(pathlib.Path(temporary), "android")
            with self.assertRaisesRegex(PlatformEvidenceError, "오래"):
                verify_platform_evidence(path, project_root=ROOT, now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        with self.assertRaisesRegex(PlatformEvidenceError, "프로젝트 밖"):
            verify_platform_evidence(ROOT / "MANIFEST.md", project_root=ROOT, now=NOW)

    def test_platform_cli_partial_is_nonzero_and_does_not_leak_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = _platform_receipt(
                pathlib.Path(temporary),
                "android",
                full=False,
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "evaluate_platform_evidence.py"), str(path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 3)
            self.assertFalse(json.loads(completed.stdout)["connection_ready"])
            self.assertNotIn(temporary, completed.stdout)


class Release95GateTests(unittest.TestCase):
    def test_external_operations_template_is_valid_but_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "operations-evidence"
            completed = subprocess.run(
                [
                    sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "init_external_evidence_bundle.py"),
                    "operations", "--output-dir", str(output),
                ],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(json.loads(completed.stdout)["ready"])
            verified = verify_operations_evidence(output / "operations-evidence.json", project_root=ROOT)
            self.assertTrue(all(state == "not_run" for state in verified.states.values()))
    def _verified(self, folder: pathlib.Path, *, mobile_full: bool = True, pc_full: bool = True, limited="pass"):
        mobile_dir = folder / "mobile"
        pc_dir = folder / "pc"
        ops_dir = folder / "ops"
        mobile_dir.mkdir()
        pc_dir.mkdir()
        ops_dir.mkdir()
        mobile = verify_platform_evidence(
            _platform_receipt(mobile_dir, "android", full=mobile_full), project_root=ROOT, now=NOW
        )
        pc = verify_platform_evidence(
            _platform_receipt(pc_dir, "windows", full=pc_full), project_root=ROOT, now=NOW
        )
        operations = verify_operations_evidence(
            _operations_bundle(ops_dir, limited_release=limited), project_root=ROOT, now=NOW
        )
        return mobile, pc, operations

    def test_all_external_evidence_reaches_100(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = evaluate_release_95(*self._verified(pathlib.Path(temporary)))
            self.assertEqual(result["evidence_gate_score"], 100)
            self.assertTrue(result["target_95_ready"])
            self.assertTrue(result["commercial_100_ready"])

    def test_limited_release_missing_is_exactly_95_not_commercial_100(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = evaluate_release_95(*self._verified(pathlib.Path(temporary), limited="not_run"))
            self.assertEqual(result["evidence_gate_score"], 95)
            self.assertTrue(result["target_95_ready"])
            self.assertFalse(result["commercial_100_ready"])

    def test_partial_mobile_blocks_95_without_inflating_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = evaluate_release_95(*self._verified(pathlib.Path(temporary), mobile_full=False))
            self.assertEqual(result["evidence_gate_score"], 85)
            self.assertFalse(result["target_95_ready"])
            self.assertIn("MOBILE_CONNECTION", result["missing_critical"])

    def test_wrong_platform_role_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            mobile, pc, operations = self._verified(pathlib.Path(temporary))
            with self.assertRaisesRegex(Release95EvidenceError, "mobile"):
                evaluate_release_95(pc, mobile, operations)

    def test_operations_pass_without_proof_and_sensitive_content_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _operations_bundle(folder, limited_release="not_run")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["gates"]["LIMITED_RELEASE"] = "pass"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Release95EvidenceError, "원본 증거"):
                verify_operations_evidence(path, project_root=ROOT, now=NOW)
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            path = _operations_bundle(folder)
            payload = json.loads(path.read_text(encoding="utf-8"))
            proof = folder / payload["artifacts"][0]["path"]
            proof.write_text("PrivateKey = unsafe\n", encoding="utf-8")
            payload["artifacts"][0]["sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Release95EvidenceError, "비밀값"):
                verify_operations_evidence(path, project_root=ROOT, now=NOW)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"플랫폼·95% 출시 증거 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
