#!/usr/bin/env python3
"""Cloud Shell bundle safety and reversibility contracts."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.cloud_init import ExitNodeSpec, render_cloud_config  # noqa: E402
from infra.gcp_cloud_shell_bundle import build_bundle_files, validate_inputs  # noqa: E402
from infra.gcp_node_plan import GCPNodePlanSpec, build_gcp_plan  # noqa: E402


EXAMPLE_PLAN = ROOT / "60_OUTPUTS" / "infra" / "FreeFlexVPN_gcp_node_plan_v1_EXAMPLE.json"
EXAMPLE_CLOUD = ROOT / "60_OUTPUTS" / "infra" / "FreeFlexVPN_gcp_node_cloud_init_v1_EXAMPLE.yaml"
CLI = ROOT / "70_TOOLS" / "build_gcp_cloud_shell_bundle.py"


class CloudShellBundleTests(unittest.TestCase):
    def example(self):
        plan_bytes = EXAMPLE_PLAN.read_bytes()
        cloud = EXAMPLE_CLOUD.read_bytes()
        return validate_inputs(json.loads(plan_bytes), plan_bytes, cloud, example=True), cloud

    def real(self):
        cloud = render_cloud_config(ExitNodeSpec("1.1.1.1/32", node_id="gcp-usw1-01", example=False)).encode("utf-8")
        plan = build_gcp_plan(
            GCPNodePlanSpec("freeflex-real-123456", "1.1.1.1/32", example=False),
            cloud_init_path="/safe/cloud-init.yaml",
            cloud_init_sha256=hashlib.sha256(cloud).hexdigest().upper(),
        )
        plan_bytes = json.dumps(plan, ensure_ascii=False).encode("utf-8")
        return validate_inputs(plan, plan_bytes, cloud, example=False), cloud

    def test_example_bundle_is_hard_stopped_before_cloud_commands(self):
        spec, cloud = self.example()
        files = build_bundle_files(spec, cloud)
        for name in ("01_preflight.sh", "02_deploy.sh", "03_provider_readback.sh", "04_rollback.sh"):
            script = files[name].decode("utf-8")
            self.assertLess(script.index("EXAMPLE_ONLY"), script.index("gcloud"))
        manifest = json.loads(files["bundle-manifest.json"])
        self.assertEqual(manifest["mode"], "EXAMPLE_ONLY")
        self.assertFalse(manifest["r6_ready"])

    def test_preflight_is_read_only(self):
        spec, cloud = self.real()
        script = build_bundle_files(spec, cloud)["01_preflight.sh"].decode("utf-8")
        for forbidden in (" services enable ", " instances create ", " firewall-rules create ", " addresses create ", " delete "):
            self.assertNotIn(forbidden, script)
        self.assertIn("billing projects describe", script)

    def test_deploy_requires_three_acknowledgements_before_first_mutation(self):
        spec, cloud = self.real()
        script = build_bundle_files(spec, cloud)["02_deploy.sh"].decode("utf-8")
        mutation = script.index("gcloud services enable")
        for gate in ("FREEFLEX_COST_REVIEWED", "FREEFLEX_PROJECT_CONFIRM", "FREEFLEX_APPLY"):
            self.assertLess(script.index(gate), mutation)
        self.assertIn("--no-service-account --no-scopes", script)
        self.assertIn("--can-ip-forward", script)

    def test_readback_never_claims_admission_or_r6(self):
        spec, cloud = self.real()
        files = build_bundle_files(spec, cloud)
        script = files["03_provider_readback.sh"].decode("utf-8")
        verifier = files["verify_provider_readback.py"].decode("utf-8")
        self.assertIn('"admission_ready": False', verifier)
        self.assertIn('"r6_ready": False', verifier)
        for resource in ("instances describe", "addresses describe", "disks describe", "firewall-rules describe"):
            self.assertIn(resource, script)
        self.assertIn("--format=json", script)
        self.assertIn("--cloud-init-sha256", script)
        self.assertIn("provider-readback-v2.json", script)

    def test_rollback_is_exact_and_preserves_project_and_api(self):
        spec, cloud = self.real()
        script = build_bundle_files(spec, cloud)["04_rollback.sh"].decode("utf-8")
        self.assertIn("FREEFLEX_ROLLBACK", script)
        for resource in (spec.node_id, spec.address_name, spec.ssh_rule, spec.wg_rule):
            self.assertIn(resource, script)
        self.assertNotIn("projects delete", script)
        self.assertNotIn("services disable", script)

    def test_cli_creates_atomic_manifest_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_cloud_shell_") as temp:
            output = pathlib.Path(temp) / "bundle"
            command = [sys.executable, "-X", "utf8", str(CLI), "--plan", str(EXAMPLE_PLAN), "--cloud-init", str(EXAMPLE_CLOUD), "--output-dir", str(output), "--example"]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            manifest = json.loads((output / "bundle-manifest.json").read_text(encoding="utf-8"))
            for name, expected in manifest["files_sha256"].items():
                actual = hashlib.sha256((output / name).read_bytes()).hexdigest().upper()
                self.assertEqual(actual, expected)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_tampered_cloud_init_is_rejected(self):
        plan_bytes = EXAMPLE_PLAN.read_bytes()
        with self.assertRaises(ValueError):
            validate_inputs(json.loads(plan_bytes), plan_bytes, EXAMPLE_CLOUD.read_bytes() + b"\n# tampered", example=True)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CloudShellBundleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP Cloud Shell 묶음 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
