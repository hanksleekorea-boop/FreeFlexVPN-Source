#!/usr/bin/env python3
"""Verify GCP provider JSON readback without claiming VPN admission."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import pathlib
import tempfile
from dataclasses import dataclass
from typing import Any


READBACK_SCHEMA = "FreeFlexVPNGCPProviderReadbackV2"
EXPECTED_TAG = "freeflexvpn-exit"


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def _basename(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a resource name")
    return value.rstrip("/").rsplit("/", 1)[-1]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class ExpectedReadback:
    project_id: str
    zone: str
    region: str
    node_id: str
    machine_type: str
    address_name: str
    ssh_rule: str
    wg_rule: str
    ssh_source: str
    ssh_port: int
    wg_port: int
    cloud_init_sha256: str


def _verify_firewall(
    payload: dict[str, Any], *, name: str, source: str, protocol: str, port: int
) -> None:
    _require(payload.get("name") == name, f"{name}: firewall name mismatch")
    _require(payload.get("direction") == "INGRESS", f"{name}: direction must be INGRESS")
    _require(payload.get("disabled") in (None, False), f"{name}: firewall rule is disabled")
    _require(_basename(payload.get("network"), f"{name}.network") == "default", f"{name}: network must be default")
    _require(payload.get("sourceRanges") == [source], f"{name}: source range mismatch")
    _require(payload.get("targetTags") == [EXPECTED_TAG], f"{name}: target tags mismatch")
    allowed = _list(payload.get("allowed"), f"{name}.allowed")
    _require(len(allowed) == 1, f"{name}: exactly one allow entry is required")
    entry = _mapping(allowed[0], f"{name}.allowed[0]")
    _require(entry.get("IPProtocol") == protocol, f"{name}: protocol mismatch")
    _require(entry.get("ports") == [str(port)], f"{name}: port mismatch")


def verify_provider_readback(
    *,
    expected: ExpectedReadback,
    instance: dict[str, Any],
    address: dict[str, Any],
    disk: dict[str, Any],
    ssh_firewall: dict[str, Any],
    wg_firewall: dict[str, Any],
) -> dict[str, Any]:
    """Return sanitized evidence only when every planned provider field matches."""
    _require(instance.get("name") == expected.node_id, "instance name mismatch")
    _require(_basename(instance.get("zone"), "instance.zone") == expected.zone, "instance zone mismatch")
    _require(
        _basename(instance.get("machineType"), "instance.machineType") == expected.machine_type,
        "machine type mismatch",
    )
    _require(instance.get("status") == "RUNNING", "instance is not RUNNING")
    _require(instance.get("canIpForward") is True, "IP forwarding is not enabled")
    _require(not instance.get("serviceAccounts"), "unexpected service account")

    shielded = _mapping(instance.get("shieldedInstanceConfig"), "shieldedInstanceConfig")
    for field in ("enableSecureBoot", "enableVtpm", "enableIntegrityMonitoring"):
        _require(shielded.get(field) is True, f"shielded setting is not enabled: {field}")

    tags = _mapping(instance.get("tags"), "tags")
    _require(tags.get("items") == [EXPECTED_TAG], "instance tags mismatch")

    interfaces = _list(instance.get("networkInterfaces"), "networkInterfaces")
    _require(len(interfaces) == 1, "exactly one network interface is required")
    interface = _mapping(interfaces[0], "networkInterfaces[0]")
    _require(_basename(interface.get("network"), "networkInterfaces[0].network") == "default", "network must be default")
    access = _list(interface.get("accessConfigs"), "networkInterfaces[0].accessConfigs")
    _require(len(access) == 1, "exactly one external access config is required")
    nat_ip = _mapping(access[0], "networkInterfaces[0].accessConfigs[0]").get("natIP")

    _require(address.get("name") == expected.address_name, "reserved address name mismatch")
    _require(_basename(address.get("region"), "address.region") == expected.region, "reserved address region mismatch")
    _require(address.get("addressType") == "EXTERNAL", "reserved address must be EXTERNAL")
    _require(address.get("ipVersion") in (None, "IPV4"), "reserved address must be IPv4")
    _require(address.get("status") == "IN_USE", "reserved address is not attached")
    reserved_ip = address.get("address")
    try:
        parsed_ip = ipaddress.ip_address(str(reserved_ip))
    except ValueError as exc:
        raise ValueError("reserved address is invalid") from exc
    _require(parsed_ip.version == 4 and parsed_ip.is_global, "reserved address is not a public IPv4")
    _require(nat_ip == reserved_ip, "instance NAT IP does not match reserved address")

    disks = _list(instance.get("disks"), "instance.disks")
    _require(len(disks) == 1, "exactly one attached disk is required")
    attached = _mapping(disks[0], "instance.disks[0]")
    _require(attached.get("boot") is True, "attached disk is not the boot disk")
    disk_name = _basename(attached.get("source"), "instance.disks[0].source")
    _require(disk.get("name") == disk_name, "boot disk readback mismatch")
    _require(str(disk.get("sizeGb")) == "10", "boot disk size must be 10GB")
    _require(_basename(disk.get("type"), "disk.type") == "pd-standard", "boot disk type must be pd-standard")

    metadata = _mapping(instance.get("metadata"), "metadata")
    items = _list(metadata.get("items"), "metadata.items")
    user_data = [item.get("value") for item in items if isinstance(item, dict) and item.get("key") == "user-data"]
    _require(len(user_data) == 1 and isinstance(user_data[0], str), "exactly one user-data metadata item is required")
    actual_cloud_hash = hashlib.sha256(user_data[0].encode("utf-8")).hexdigest().upper()
    _require(actual_cloud_hash == expected.cloud_init_sha256, "cloud-init metadata SHA-256 mismatch")

    _verify_firewall(
        ssh_firewall,
        name=expected.ssh_rule,
        source=expected.ssh_source,
        protocol="tcp",
        port=expected.ssh_port,
    )
    _verify_firewall(
        wg_firewall,
        name=expected.wg_rule,
        source="0.0.0.0/0",
        protocol="udp",
        port=expected.wg_port,
    )

    return {
        "schema": READBACK_SCHEMA,
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "gcp",
        "project_id": expected.project_id,
        "zone": expected.zone,
        "node_id": expected.node_id,
        "instance_status": "RUNNING",
        "machine_type": expected.machine_type,
        "can_ip_forward": True,
        "service_account_present": False,
        "shielded_vm": {
            "secure_boot": True,
            "vtpm": True,
            "integrity_monitoring": True,
        },
        "boot_disk": {"name": disk_name, "size_gb": 10, "type": "pd-standard"},
        "reserved_ip": reserved_ip,
        "network": "default",
        "ssh_source": expected.ssh_source,
        "wireguard_source": "0.0.0.0/0",
        "cloud_init_sha256": actual_cloud_hash,
        "provider_configuration_verified": True,
        "admission_ready": False,
        "r6_ready": False,
        "contains_secrets": False,
    }


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def _atomic_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GCP provider readback and emit non-admission evidence")
    for name in ("project-id", "zone", "region", "node-id", "machine-type", "address-name", "ssh-rule", "wg-rule", "ssh-source", "cloud-init-sha256"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--ssh-port", type=int, required=True)
    parser.add_argument("--wg-port", type=int, required=True)
    for name in ("instance", "address", "disk", "ssh-firewall", "wg-firewall", "output"):
        parser.add_argument(f"--{name}", type=pathlib.Path, required=True)
    args = parser.parse_args()
    expected = ExpectedReadback(
        project_id=args.project_id,
        zone=args.zone,
        region=args.region,
        node_id=args.node_id,
        machine_type=args.machine_type,
        address_name=args.address_name,
        ssh_rule=args.ssh_rule,
        wg_rule=args.wg_rule,
        ssh_source=args.ssh_source,
        ssh_port=args.ssh_port,
        wg_port=args.wg_port,
        cloud_init_sha256=args.cloud_init_sha256,
    )
    evidence = verify_provider_readback(
        expected=expected,
        instance=_read_json(args.instance),
        address=_read_json(args.address),
        disk=_read_json(args.disk),
        ssh_firewall=_read_json(args.ssh_firewall),
        wg_firewall=_read_json(args.wg_firewall),
    )
    _atomic_json(args.output, evidence)
    print("PROVIDER CONFIGURATION VERIFIED, NOT VPN ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
