#!/usr/bin/env python3
"""Contract tests for redacted GCP read-access evidence."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_readback_access import (  # noqa: E402
    CommandResult,
    check_readback_access,
    write_new_json,
)


class ScriptedRunner:
    def __init__(self, results):
        self.results = list(results)
        self.commands = []

    def __call__(self, argv):
        self.commands.append(list(argv))
        return self.results.pop(0)


class GCPReadbackAccessTests(unittest.TestCase):
    def check(self, runner):
        return check_readback_access(
            gcloud="gcloud.cmd",
            project="oceanic-example-123456",
            zone="us-west1-b",
            instance="gcp-usw1-01",
            runner=runner,
            checked_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )

    def test_permission_failure_is_classified_without_raw_identifiers(self):
        account_marker = "owner" + "@example.com"
        raw = (
            "Required 'compute.instances.get' permission for project oceanic-example-123456 "
            f"while signed in as {account_marker} from 203.0.113.10"
        )
        receipt = self.check(ScriptedRunner([CommandResult(1, "", raw)]))
        encoded = json.dumps(receipt)
        self.assertEqual(receipt["status"], "permission_missing")
        self.assertEqual(receipt["required_permissions"], ["compute.instances.get"])
        self.assertNotIn(account_marker, encoded)
        self.assertNotIn("203.0.113.10", encoded)
        self.assertNotIn("oceanic-example", encoded)
        self.assertEqual(receipt["mutation_count"], 0)

    def test_provider_ready_returns_only_allowlisted_booleans_and_counts(self):
        instance = {
            "status": "RUNNING",
            "canIpForward": True,
            "tags": {"items": ["freeflexvpn-exit"]},
            "networkInterfaces": [{"networkIP": "10.0.0.2", "accessConfigs": [{"natIP": "34.1.2.3"}]}],
        }
        firewall = [{
            "direction": "INGRESS",
            "disabled": False,
            "targetTags": ["freeflexvpn-exit"],
            "allowed": [{"IPProtocol": "udp", "ports": ["51820"]}],
        }]
        runner = ScriptedRunner([
            CommandResult(0, json.dumps(instance), ""),
            CommandResult(0, json.dumps(firewall), ""),
        ])
        receipt = self.check(runner)
        encoded = json.dumps(receipt)
        self.assertEqual(receipt["status"], "provider_ready")
        self.assertTrue(receipt["server_internal_readback_ready"])
        self.assertEqual(receipt["enabled_wireguard_rule_count"], 1)
        self.assertNotIn("10.0.0.2", encoded)
        self.assertNotIn("34.1.2.3", encoded)
        self.assertNotIn("networkInterfaces", encoded)
        self.assertTrue(receipt["contains_secrets"] is False)

    def test_provider_mismatch_fails_closed(self):
        instance = {
            "status": "RUNNING",
            "canIpForward": False,
            "tags": {"items": []},
            "networkInterfaces": [],
        }
        runner = ScriptedRunner([
            CommandResult(0, json.dumps(instance), ""),
            CommandResult(0, "[]", ""),
        ])
        receipt = self.check(runner)
        self.assertEqual(receipt["status"], "provider_mismatch")
        self.assertFalse(receipt["server_internal_readback_ready"])

    def test_invalid_identifiers_are_rejected_before_process_start(self):
        runner = ScriptedRunner([])
        with self.assertRaises(ValueError):
            check_readback_access(
                gcloud="gcloud.cmd",
                project="bad;project",
                zone="us-west1-b",
                instance="gcp-usw1-01",
                runner=runner,
            )
        self.assertEqual(runner.commands, [])

    def test_non_wireguard_firewall_rule_does_not_pass(self):
        instance = {
            "status": "RUNNING",
            "canIpForward": True,
            "tags": {"items": ["freeflexvpn-exit"]},
            "networkInterfaces": [{}],
        }
        wrong_rule = [{
            "direction": "INGRESS",
            "disabled": False,
            "targetTags": ["freeflexvpn-exit"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["51820"]}],
        }]
        runner = ScriptedRunner([
            CommandResult(0, json.dumps(instance), ""),
            CommandResult(0, json.dumps(wrong_rule), ""),
        ])
        receipt = self.check(runner)
        self.assertEqual(receipt["status"], "provider_mismatch")
        self.assertEqual(receipt["enabled_wireguard_rule_count"], 0)

    def test_malformed_provider_lists_fail_closed(self):
        instance = {
            "status": "RUNNING",
            "canIpForward": True,
            "tags": {"items": None},
            "networkInterfaces": None,
        }
        malformed_rules = [{
            "direction": "INGRESS",
            "disabled": False,
            "targetTags": ["freeflexvpn-exit"],
            "allowed": [{"IPProtocol": "udp", "ports": None}],
        }, {
            "direction": "INGRESS",
            "disabled": False,
            "targetTags": ["freeflexvpn-exit"],
            "allowed": None,
        }]
        runner = ScriptedRunner([
            CommandResult(0, json.dumps(instance), ""),
            CommandResult(0, json.dumps(malformed_rules), ""),
        ])
        receipt = self.check(runner)
        self.assertEqual(receipt["status"], "provider_mismatch")
        self.assertEqual(receipt["network_interface_count"], 0)
        self.assertEqual(receipt["enabled_wireguard_rule_count"], 0)

    def test_receipts_never_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "receipt.json"
            write_new_json(path, {"status": "first"})
            with self.assertRaises(FileExistsError):
                write_new_json(path, {"status": "second"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"status": "first"})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPReadbackAccessTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"GCP readback access contract {passed}/{result.testsRun}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
