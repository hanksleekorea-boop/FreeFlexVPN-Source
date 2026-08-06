#!/usr/bin/env python3
"""GCP runtime config 생성기의 외부 경로·무비밀·검증 계약."""
from __future__ import annotations

import base64
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_runtime import load_runtime_settings  # noqa: E402


CLI = ROOT / "70_TOOLS" / "build_gcp_runtime_config.py"


class GCPRuntimeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_gcp_runtime_")
        root = pathlib.Path(self.temp.name)
        self.identity = root / "id_ed25519"
        self.known = root / "known_hosts"
        self.output = root / "nodes.json"
        self.identity.write_text("test-only", encoding="ascii")
        self.known.write_text("gcp.example.test ssh-ed25519 test-only", encoding="ascii")

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *, output=None, country_code="US", exit_ip="8.8.8.8"):
        return [
            sys.executable, "-X", "utf8", str(CLI), "--output", str(output or self.output),
            "--host", "gcp.example.test", "--identity-file", str(self.identity),
            "--known-hosts-file", str(self.known), "--country-code", country_code,
            "--exit-ip", exit_ip, "--server-public-key", base64.b64encode(b"g" * 32).decode("ascii"),
            "--verified-at", datetime.now(timezone.utc).isoformat(),
        ]

    def test_creates_valid_single_gcp_config_without_secret_material(self):
        completed = subprocess.run(
            self.command(), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        settings = load_runtime_settings(self.output)
        self.assertEqual(len(settings.nodes), 1)
        self.assertEqual(settings.nodes[0].provider_ref, "gcp")
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("private_key", text.lower())
        self.assertNotIn("test-only", text)

    def test_invalid_country_or_private_exit_leaves_no_output(self):
        for country_code, exit_ip in [("KR", "8.8.8.8"), ("US", "10.0.0.5")]:
            self.output.unlink(missing_ok=True)
            completed = subprocess.run(
                self.command(country_code=country_code, exit_ip=exit_ip), cwd=ROOT,
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(self.output.exists())

    def test_project_inside_output_is_rejected_before_write(self):
        forbidden = ROOT / "nodes-should-never-exist.json"
        forbidden.unlink(missing_ok=True)
        completed = subprocess.run(
            self.command(output=forbidden), cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", errors="replace", check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPRuntimeConfigTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP runtime config 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
