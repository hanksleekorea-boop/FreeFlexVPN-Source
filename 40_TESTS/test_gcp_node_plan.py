#!/usr/bin/env python3
"""GCP 첫 노드 계획의 비용·네트워크·증거 경계 계약."""
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

from infra.cloud_init import (  # noqa: E402
    EXAMPLE_ADMIN_CIDR,
    GOOGLE_IAP_TCP_FORWARDING_CIDR,
    ExitNodeSpec,
    render_cloud_config,
)
from infra.gcp_node_plan import EXAMPLE_PROJECT_ID, GCPNodePlanSpec, build_gcp_plan  # noqa: E402


class GCPNodePlanTests(unittest.TestCase):
    def spec(self, **changes):
        values = {
            "project_id": EXAMPLE_PROJECT_ID,
            "admin_ssh_cidr": EXAMPLE_ADMIN_CIDR,
            "zone": "us-west1-b",
            "node_id": "gcp-usw1-01",
            "example": True,
        }
        values.update(changes)
        return GCPNodePlanSpec(**values)

    def plan(self):
        cloud = render_cloud_config(ExitNodeSpec(EXAMPLE_ADMIN_CIDR, node_id="gcp-usw1-01", example=True)).encode()
        return build_gcp_plan(
            self.spec(), cloud_init_path="C:/safe/gcp.cloud-init.yaml",
            cloud_init_sha256=hashlib.sha256(cloud).hexdigest().upper(),
        )

    def test_example_plan_is_single_provider_and_never_r6_ready(self):
        plan = self.plan()
        self.assertEqual(plan["provider"], "gcp")
        self.assertEqual(plan["gates"]["provider_diversity_credit"], 1)
        self.assertTrue(plan["gates"]["next_provider_required"])
        self.assertFalse(plan["gates"]["r6_ready"])
        self.assertEqual(plan["mode"], "EXAMPLE_ONLY")

    def test_commands_enforce_small_vm_no_service_account_and_ip_forwarding(self):
        commands = "\n".join(self.plan()["commands"])
        self.assertIn("--machine-type=e2-micro", commands)
        self.assertIn("--can-ip-forward", commands)
        self.assertIn("--no-service-account --no-scopes", commands)
        self.assertIn("--shielded-secure-boot", commands)
        self.assertIn("--rules=udp:51820 --source-ranges=0.0.0.0/0", commands)

    def test_ssh_is_one_ip_and_cost_limits_are_honest(self):
        plan = self.plan()
        self.assertEqual(plan["network"]["ssh_source"], EXAMPLE_ADMIN_CIDR)
        self.assertEqual(plan["gates"]["free_tier_eligibility"], "VERIFY_IN_GCP_CONSOLE_BEFORE_CREATE")
        self.assertEqual(plan["gates"]["billing_budget_alert"], "REQUIRED_BUT_NOT_A_HARD_SPEND_CAP")
        self.assertEqual(plan["gates"]["external_ipv4_and_egress"], "MAY_BE_BILLABLE")

    def test_invalid_cost_or_region_choices_are_rejected(self):
        bad = [
            self.spec(project_id="INVALID"),
            self.spec(zone="asia-northeast3-a"),
            self.spec(machine_type="e2-standard-4"),
            self.spec(project_id=EXAMPLE_PROJECT_ID, example=False, admin_ssh_cidr="8.8.8.8/32"),
            self.spec(admin_ssh_cidr="0.0.0.0/0", example=False, project_id="freeflex-real-123456"),
        ]
        for spec in bad:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    spec.validated()

    def test_google_iap_is_the_only_allowed_managed_ssh_range(self):
        spec = self.spec(
            project_id="freeflex-real-123456",
            admin_ssh_cidr=GOOGLE_IAP_TCP_FORWARDING_CIDR,
            example=False,
        )
        spec.validated()
        cloud = render_cloud_config(
            ExitNodeSpec(
                GOOGLE_IAP_TCP_FORWARDING_CIDR,
                node_id="gcp-usw1-01",
                example=False,
            )
        ).encode()
        plan = build_gcp_plan(
            spec,
            cloud_init_path="C:/safe/gcp.cloud-init.yaml",
            cloud_init_sha256=hashlib.sha256(cloud).hexdigest().upper(),
        )
        self.assertEqual(plan["network"]["ssh_source"], GOOGLE_IAP_TCP_FORWARDING_CIDR)
        self.assertEqual(plan["network"]["ssh_access_mode"], "google_iap")
        with self.assertRaises(ValueError):
            self.spec(
                project_id="freeflex-real-123456",
                admin_ssh_cidr="35.235.0.0/16",
                example=False,
            ).validated()

    def test_cli_creates_new_secret_free_files_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_gcp_plan_") as temp:
            plan_path = pathlib.Path(temp) / "plan.json"
            cloud_path = pathlib.Path(temp) / "cloud.yaml"
            command = [
                sys.executable, "-X", "utf8", str(ROOT / "70_TOOLS" / "build_gcp_node_plan.py"),
                "--example", "--output", str(plan_path), "--cloud-init-output", str(cloud_path),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertFalse(plan["contains_secrets"])
            self.assertNotIn("PrivateKey =", cloud_path.read_text(encoding="utf-8"))
            before = (plan_path.read_bytes(), cloud_path.read_bytes())
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(before, (plan_path.read_bytes(), cloud_path.read_bytes()))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPNodePlanTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"GCP 첫 노드 계획 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
