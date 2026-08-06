#!/usr/bin/env python3
"""GCP admission CLI의 무네트워크 설정검사와 증거 결속 계약."""
from __future__ import annotations

import base64
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.preflight_evidence import sha256_file, validate_preflight_evidence  # noqa: E402


CLI = ROOT / "70_TOOLS" / "run_gcp_node_admission.py"
SCHEMA = "FreeFlexVPNGCPNodeConfigurationPreflightV1"


class GCPNodeAdmissionCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_gcp_cli_")
        root = pathlib.Path(self.temp.name)
        self.identity = root / "id_ed25519"
        self.known = root / "known_hosts"
        self.identity.write_text("test-only", encoding="ascii")
        self.known.write_text("gcp.example.test ssh-ed25519 test-only", encoding="ascii")
        self.config = root / "nodes.json"
        self.output = root / "config-evidence.json"
        self.candidate_id = "GCP-candidate-20260802-01"
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "nodes": [{
                "server_id": "gcp-usw1-01", "node_id": "gcp-usw1-01",
                "host": "gcp.example.test", "ssh_user": "freeflex", "ssh_port": 22,
                "identity_file": str(self.identity), "known_hosts_file": str(self.known),
                "country_code": "US", "country": "United States", "city": "Oregon",
                "provider_ref": "gcp", "exit_ip": "8.8.8.8", "endpoint": "8.8.8.8:51820",
                "server_public_key": base64.b64encode(b"g" * 32).decode("ascii"),
                "dns_addresses": ["1.1.1.1"], "exit_verified": True,
                "verified_at": now, "capacity_percent": 10,
            }],
            "health_interval_seconds": 60, "counter_interval_seconds": 60,
        }
        self.config.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_config_only_creates_bound_non_network_evidence(self):
        completed = subprocess.run(
            [
                sys.executable, "-X", "utf8", str(CLI), "--config", str(self.config),
                "--candidate-id", self.candidate_id, "--output", str(self.output), "--config-only",
            ],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertTrue(report["configuration_ready"])
        self.assertFalse(report["network_attempted"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["r6_ready"])
        self.assertEqual(report["config_sha256"], sha256_file(self.config))

    def test_live_mode_requires_evidence_before_config_or_network(self):
        completed = subprocess.run(
            [
                sys.executable, "-X", "utf8", str(CLI), "--config", str(self.config.with_name("missing.json")),
                "--candidate-id", self.candidate_id,
            ],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--config-evidence 절대 경로가 필요합니다", completed.stderr)

    def test_gcp_evidence_rejects_r6_schema_or_changed_config(self):
        report = {
            "schema": SCHEMA, "mode": "config_only", "provider": "gcp",
            "configuration_ready": True, "ready": False, "r6_ready": False,
            "network_attempted": False, "candidate_id": self.candidate_id,
            "config_sha256": sha256_file(self.config), "contains_secrets": False,
        }
        self.output.write_text(json.dumps(report), encoding="utf-8")
        digest = validate_preflight_evidence(
            self.output, schema=SCHEMA, candidate_id=self.candidate_id,
            config_sha256=sha256_file(self.config), extra_required={"provider": "gcp", "r6_ready": False},
        )
        self.assertEqual(len(digest), 64)
        with self.assertRaisesRegex(ValueError, "일치하지 않습니다"):
            validate_preflight_evidence(
                self.output, schema="FreeFlexVPNR6ConfigurationPreflightV1",
                candidate_id=self.candidate_id, config_sha256=sha256_file(self.config),
            )
        with self.assertRaisesRegex(ValueError, "일치하지 않습니다"):
            validate_preflight_evidence(
                self.output, schema=SCHEMA, candidate_id=self.candidate_id,
                config_sha256="0" * 64, extra_required={"provider": "gcp", "r6_ready": False},
            )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPNodeAdmissionCLITests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP admission CLI 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
