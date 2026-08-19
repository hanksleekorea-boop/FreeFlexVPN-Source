#!/usr/bin/env python3
"""Contract tests for redacted target-by-fingerprint GCP selection."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_readback_access import target_fingerprint  # noqa: E402
from infra.gcp_target_locator import CommandResult, _process_command, locate_and_check, locate_target  # noqa: E402


class ScriptedRunner:
    def __init__(self, results):
        self.results = list(results)
        self.commands = []

    def __call__(self, argv):
        self.commands.append(tuple(argv))
        return self.results.pop(0)


class GCPTargetLocatorTests(unittest.TestCase):
    zone = "us-west1-b"
    instance = "gcp-usw1-01"
    target = "oceanic-example-123456"

    def locate(self, runner):
        return locate_target(
            gcloud="gcloud", expected_target_fingerprint=target_fingerprint(self.target, self.zone, self.instance),
            zone=self.zone, instance=self.instance, runner=runner, checked_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
        )

    def test_matching_project_is_held_only_in_memory(self):
        runner = ScriptedRunner([CommandResult(0, f"wrong-example-123456\n{self.target}\n")])
        receipt, project = self.locate(runner)
        self.assertEqual(receipt["status"], "target_selected")
        self.assertEqual(project, self.target)
        self.assertNotIn(self.target, json.dumps(receipt))
        self.assertEqual(receipt["mutation_count"], 0)

    def test_no_match_fails_closed(self):
        runner = ScriptedRunner([CommandResult(0, "wrong-example-123456\n")])
        receipt, project = self.locate(runner)
        self.assertEqual(receipt["status"], "target_not_accessible")
        self.assertIsNone(project)
        self.assertEqual(receipt["matching_count"], 0)

    def test_listing_error_is_redacted(self):
        marker = "account-marker-must-be-redacted"
        runner = ScriptedRunner([CommandResult(1, "", f"signed in as {marker} for oceanic-example-123456")])
        receipt, project = self.locate(runner)
        self.assertEqual(receipt["status"], "project_listing_unavailable")
        self.assertIsNone(project)
        self.assertNotIn(marker, json.dumps(receipt))
        self.assertNotIn(self.target, json.dumps(receipt))

    def test_invalid_expected_fingerprint_stops_before_command(self):
        runner = ScriptedRunner([])
        with self.assertRaises(ValueError):
            locate_target(gcloud="gcloud", expected_target_fingerprint="bad", zone=self.zone, instance=self.instance, runner=runner)
        self.assertEqual(runner.commands, [])

    def test_windows_powershell_wrapper_is_invoked_without_a_shell_string(self):
        command = _process_command((r"C:\\Tools\\gcloud.ps1", "projects", "list", "--format=value(projectId)"))
        self.assertEqual(command[:4], ("powershell.exe", "-NoProfile", "-File", r"C:\\Tools\\gcloud.ps1"))
        self.assertEqual(command[4:], ("projects", "list", "--format=value(projectId)"))

    def test_windows_powershell_wrapper_prefers_existing_cmd_sibling(self):
        with tempfile.TemporaryDirectory() as temp:
            ps1 = pathlib.Path(temp) / "gcloud.ps1"
            cmd = pathlib.Path(temp) / "gcloud.cmd"
            ps1.write_text("# placeholder\n", encoding="utf-8")
            cmd.write_text("@echo off\n", encoding="utf-8")
            command = _process_command((str(ps1), "projects", "list"))
            self.assertEqual(command, (str(cmd), "projects", "list"))

    def test_selected_target_runs_only_existing_readback_queries(self):
        instance = json.dumps({"status": "RUNNING", "canIpForward": True, "tags": {"items": ["freeflexvpn-exit"]}, "networkInterfaces": [{}]})
        firewall = json.dumps([{"direction": "INGRESS", "disabled": False, "targetTags": ["freeflexvpn-exit"], "allowed": [{"IPProtocol": "udp", "ports": ["51820"]}]}])
        runner = ScriptedRunner([CommandResult(0, f"{self.target}\n"), CommandResult(0, instance), CommandResult(0, firewall)])
        receipt = locate_and_check(
            gcloud="gcloud", expected_target_fingerprint=target_fingerprint(self.target, self.zone, self.instance),
            zone=self.zone, instance=self.instance, runner=runner,
        )
        self.assertEqual(receipt["provider_status"], "provider_ready")
        self.assertTrue(receipt["server_internal_readback_ready"])
        self.assertEqual(receipt["mutation_count"], 0)
        self.assertTrue(all("create" not in " ".join(command) for command in runner.commands))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPTargetLocatorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"GCP target locator contract {passed}/{result.testsRun}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
