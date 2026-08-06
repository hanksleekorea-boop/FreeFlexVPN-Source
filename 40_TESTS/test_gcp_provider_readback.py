#!/usr/bin/env python3
"""Negative-control tests for GCP provider configuration readback."""
from __future__ import annotations

import copy
import hashlib
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_provider_readback import ExpectedReadback, verify_provider_readback  # noqa: E402


class GCPProviderReadbackTests(unittest.TestCase):
    def setUp(self):
        self.user_data = "#cloud-config\npackages:\n  - wireguard\n"
        self.expected = ExpectedReadback(
            project_id="freeflex-real-123456",
            zone="us-west1-b",
            region="us-west1",
            node_id="gcp-usw1-01",
            machine_type="e2-micro",
            address_name="gcp-usw1-01-ip",
            ssh_rule="gcp-usw1-01-ssh",
            wg_rule="gcp-usw1-01-wg",
            ssh_source="1.1.1.1/32",
            ssh_port=22,
            wg_port=51820,
            cloud_init_sha256=hashlib.sha256(self.user_data.encode()).hexdigest().upper(),
        )
        base = "https://www.googleapis.com/compute/v1/projects/freeflex-real-123456"
        self.instance = {
            "name": "gcp-usw1-01",
            "zone": f"{base}/zones/us-west1-b",
            "machineType": f"{base}/zones/us-west1-b/machineTypes/e2-micro",
            "status": "RUNNING",
            "canIpForward": True,
            "shieldedInstanceConfig": {
                "enableSecureBoot": True,
                "enableVtpm": True,
                "enableIntegrityMonitoring": True,
            },
            "tags": {"items": ["freeflexvpn-exit"]},
            "networkInterfaces": [{
                "network": f"{base}/global/networks/default",
                "accessConfigs": [{"natIP": "34.1.2.3", "type": "ONE_TO_ONE_NAT"}],
            }],
            "disks": [{"boot": True, "source": f"{base}/zones/us-west1-b/disks/gcp-usw1-01"}],
            "metadata": {"items": [{"key": "user-data", "value": self.user_data}]},
        }
        self.address = {
            "name": "gcp-usw1-01-ip",
            "region": f"{base}/regions/us-west1",
            "address": "34.1.2.3",
            "addressType": "EXTERNAL",
            "ipVersion": "IPV4",
            "status": "IN_USE",
        }
        self.disk = {
            "name": "gcp-usw1-01",
            "sizeGb": "10",
            "type": f"{base}/zones/us-west1-b/diskTypes/pd-standard",
        }
        self.ssh = {
            "name": "gcp-usw1-01-ssh",
            "network": f"{base}/global/networks/default",
            "direction": "INGRESS",
            "sourceRanges": ["1.1.1.1/32"],
            "targetTags": ["freeflexvpn-exit"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}],
        }
        self.wg = {
            "name": "gcp-usw1-01-wg",
            "network": f"{base}/global/networks/default",
            "direction": "INGRESS",
            "sourceRanges": ["0.0.0.0/0"],
            "targetTags": ["freeflexvpn-exit"],
            "allowed": [{"IPProtocol": "udp", "ports": ["51820"]}],
        }

    def verify(self):
        return verify_provider_readback(
            expected=self.expected,
            instance=self.instance,
            address=self.address,
            disk=self.disk,
            ssh_firewall=self.ssh,
            wg_firewall=self.wg,
        )

    def test_valid_provider_configuration_is_sanitized_but_not_admitted(self):
        evidence = self.verify()
        self.assertTrue(evidence["provider_configuration_verified"])
        self.assertFalse(evidence["admission_ready"])
        self.assertFalse(evidence["r6_ready"])
        self.assertFalse(evidence["contains_secrets"])
        self.assertNotIn("user-data", str(evidence))

    def test_instance_state_forwarding_and_service_account_fail_closed(self):
        for field, value in (("status", "STOPPED"), ("canIpForward", False), ("serviceAccounts", [{"name": "unexpected-service-account"}])):
            with self.subTest(field=field):
                original = self.instance.get(field, None)
                self.instance[field] = value
                with self.assertRaises(ValueError):
                    self.verify()
                if original is None:
                    self.instance.pop(field)
                else:
                    self.instance[field] = original

    def test_all_shielded_vm_controls_are_required(self):
        for field in ("enableSecureBoot", "enableVtpm", "enableIntegrityMonitoring"):
            with self.subTest(field=field):
                self.instance["shieldedInstanceConfig"][field] = False
                with self.assertRaises(ValueError):
                    self.verify()
                self.instance["shieldedInstanceConfig"][field] = True

    def test_reserved_public_ip_must_be_attached_to_the_instance(self):
        for field, value in (("status", "RESERVED"), ("address", "203.0.113.10")):
            with self.subTest(field=field):
                original = self.address[field]
                self.address[field] = value
                with self.assertRaises(ValueError):
                    self.verify()
                self.address[field] = original
        self.instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"] = "34.1.2.4"
        with self.assertRaises(ValueError):
            self.verify()

    def test_boot_disk_contract_is_exact(self):
        for field, value in (("sizeGb", "20"), ("type", "https://example.invalid/diskTypes/pd-balanced")):
            with self.subTest(field=field):
                original = self.disk[field]
                self.disk[field] = value
                with self.assertRaises(ValueError):
                    self.verify()
                self.disk[field] = original
        self.instance["disks"].append(copy.deepcopy(self.instance["disks"][0]))
        with self.assertRaises(ValueError):
            self.verify()

    def test_cloud_init_metadata_hash_is_bound(self):
        self.instance["metadata"]["items"][0]["value"] += "# changed\n"
        with self.assertRaisesRegex(ValueError, "cloud-init"):
            self.verify()

    def test_firewall_protocol_port_source_and_tags_are_exact(self):
        mutations = [
            (self.ssh, "sourceRanges", ["0.0.0.0/0"]),
            (self.ssh, "targetTags", ["freeflexvpn-exit", "extra"]),
            (self.ssh["allowed"][0], "ports", ["22", "443"]),
            (self.wg["allowed"][0], "IPProtocol", "tcp"),
            (self.wg, "disabled", True),
        ]
        for target, field, value in mutations:
            with self.subTest(field=field, value=value):
                original = target.get(field, None)
                target[field] = value
                with self.assertRaises(ValueError):
                    self.verify()
                if original is None:
                    target.pop(field)
                else:
                    target[field] = original


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GCPProviderReadbackTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"GCP provider readback 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
