#!/usr/bin/env python3
"""R6 CLI가 설정검사 증거와 실서버 후보를 같은 해시로 결속하는지 검사한다."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "70_TOOLS" / "run_r6_server_preflight.py"
SPEC = importlib.util.spec_from_file_location(
    "freeflex_run_r6_server_preflight", CLI_PATH
)
assert SPEC and SPEC.loader
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


class R6PreflightCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_r6_cli_")
        self.path = pathlib.Path(self.temp.name) / "config-evidence.json"
        self.candidate_id = "R6-candidate-20260802-01"
        self.config_sha256 = "a" * 64
        self.payload = {
            "schema": CLI.CONFIG_EVIDENCE_SCHEMA,
            "mode": "config_only",
            "configuration_ready": True,
            "ready": False,
            "network_attempted": False,
            "candidate_id": self.candidate_id,
            "config_sha256": self.config_sha256,
            "contains_secrets": False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def write(self, changes=None):
        payload = dict(self.payload)
        payload.update(changes or {})
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def test_matching_candidate_and_config_evidence_passes(self):
        self.write()
        digest = CLI.validate_configuration_evidence(
            self.path, candidate_id=self.candidate_id, config_sha256=self.config_sha256
        )
        self.assertEqual(len(digest), 64)

    def test_candidate_or_config_mismatch_blocks_before_network(self):
        self.write()
        for candidate_id, config_sha256 in [
            ("R6-candidate-20260802-02", self.config_sha256),
            (self.candidate_id, "b" * 64),
        ]:
            with self.subTest(candidate_id=candidate_id, config_sha256=config_sha256):
                with self.assertRaisesRegex(ValueError, "일치하지 않습니다"):
                    CLI.validate_configuration_evidence(
                        self.path, candidate_id=candidate_id, config_sha256=config_sha256
                    )

    def test_unready_or_network_attempted_evidence_is_rejected(self):
        for changes in [
            {"configuration_ready": False},
            {"ready": True},
            {"network_attempted": True},
            {"contains_secrets": True},
        ]:
            with self.subTest(changes=changes):
                self.write(changes)
                with self.assertRaisesRegex(ValueError, "일치하지 않습니다"):
                    CLI.validate_configuration_evidence(
                        self.path, candidate_id=self.candidate_id, config_sha256=self.config_sha256
                    )

    def test_live_mode_requires_evidence_before_loading_config_or_network(self):
        missing_config = pathlib.Path(self.temp.name) / "missing-nodes.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(CLI_PATH),
                "--config",
                str(missing_config),
                "--candidate-id",
                self.candidate_id,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("실서버 모드는 --config-evidence 절대 경로가 필요합니다", completed.stderr)

    def test_relative_or_oversized_evidence_is_rejected(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "절대 경로"):
            CLI.validate_configuration_evidence(
                pathlib.Path("config-evidence.json"),
                candidate_id=self.candidate_id,
                config_sha256=self.config_sha256,
            )
        self.path.write_bytes(b"x" * (CLI.MAX_EVIDENCE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "크기"):
            CLI.validate_configuration_evidence(
                self.path, candidate_id=self.candidate_id, config_sha256=self.config_sha256
            )
        with self.assertRaisesRegex(ValueError, "확인할 수 없습니다"):
            CLI.validate_configuration_evidence(
                self.path.with_name("missing.json"),
                candidate_id=self.candidate_id,
                config_sha256=self.config_sha256,
            )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(R6PreflightCLITests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"R6 증거 연결 CLI 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
