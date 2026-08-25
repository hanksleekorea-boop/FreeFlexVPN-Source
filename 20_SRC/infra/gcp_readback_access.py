#!/usr/bin/env python3
"""Read GCP VPN-node provider state without emitting account, address, or key data."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence


SCHEMA = "FreeFlexVPNGCPReadbackAccessV1"
WIREGUARD_TAG = "freeflexvpn-exit"
IDENTIFIER = re.compile(r"^[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?$")
ZONE = re.compile(r"^[a-z]+-[a-z0-9]+[0-9]-[a-z]$")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], CommandResult]


def _validate(value: str, pattern: re.Pattern[str], field: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def target_fingerprint(project: str, zone: str, instance: str) -> str:
    """Bind evidence to one target without storing its identifiers."""
    material = f"{project}\0{zone}\0{instance}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _default_runner(argv: Sequence[str]) -> CommandResult:
    completed = subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=45,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _failure_status(stderr: str) -> tuple[str, list[str]]:
    lowered = stderr.lower()
    if "compute.instances.get" in lowered or "required permission" in lowered:
        return "permission_missing", ["compute.instances.get"]
    if "re-authentication" in lowered or "login" in lowered or "no credentialed accounts" in lowered:
        return "authentication_required", []
    if "was not found" in lowered or "could not be found" in lowered:
        return "target_not_found", []
    if "timed out" in lowered or "connection" in lowered:
        return "network_unavailable", []
    return "provider_error", []


def _parse_json_object(raw: str, field: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {field} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _parse_json_list(raw: str, field: str) -> list[object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {field} JSON") from exc
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def check_readback_access(
    *,
    gcloud: str,
    project: str,
    zone: str,
    instance: str,
    runner: Runner = _default_runner,
    checked_at: datetime | None = None,
) -> dict[str, object]:
    """Return allowlisted provider evidence; raw command output is never returned."""
    _validate(project, IDENTIFIER, "project")
    _validate(zone, ZONE, "zone")
    _validate(instance, IDENTIFIER, "instance")
    checked_at = checked_at or datetime.now(timezone.utc)
    base: dict[str, object] = {
        "schema": SCHEMA,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "target_fingerprint": target_fingerprint(project, zone, instance),
        "provider": "gcp",
        "contains_secrets": False,
        "contains_account_identifier": False,
        "contains_network_address": False,
        "mutation_count": 0,
    }
    instance_result = runner([
        gcloud,
        "compute",
        "instances",
        "describe",
        instance,
        f"--project={project}",
        f"--zone={zone}",
        "--format=json(status,canIpForward,tags.items,networkInterfaces)",
    ])
    if instance_result.returncode:
        status, permissions = _failure_status(instance_result.stderr)
        return {
            **base,
            "status": status,
            "required_permissions": permissions,
            "instance_readable": False,
            "firewall_readable": False,
            "server_internal_readback_ready": False,
        }

    payload = _parse_json_object(instance_result.stdout, "instance")
    tags = payload.get("tags")
    tag_items = tags.get("items", []) if isinstance(tags, dict) else []
    if not isinstance(tag_items, list):
        tag_items = []
    interfaces = payload.get("networkInterfaces")
    interface_count = len(interfaces) if isinstance(interfaces, list) else 0

    firewall_result = runner([
        gcloud,
        "compute",
        "firewall-rules",
        "list",
        f"--project={project}",
        "--filter=direction=INGRESS AND allowed.ports:51820",
        "--format=json(direction,disabled,targetTags,allowed)",
    ])
    if firewall_result.returncode:
        status, permissions = _failure_status(firewall_result.stderr)
        return {
            **base,
            "status": status,
            "required_permissions": permissions,
            "instance_readable": True,
            "firewall_readable": False,
            "instance_running": payload.get("status") == "RUNNING",
            "ip_forwarding_enabled": payload.get("canIpForward") is True,
            "wireguard_tag_present": WIREGUARD_TAG in tag_items,
            "network_interface_count": interface_count,
            "server_internal_readback_ready": False,
        }

    rules = _parse_json_list(firewall_result.stdout, "firewall")
    enabled_matches = 0
    for candidate in rules:
        if not isinstance(candidate, dict):
            continue
        targets = candidate.get("targetTags", [])
        allowed = candidate.get("allowed", [])
        udp_51820 = False
        if isinstance(allowed, list):
            for entry in allowed:
                if not isinstance(entry, dict):
                    continue
                ports = entry.get("ports", [])
                if entry.get("IPProtocol") == "udp" and isinstance(ports, list) and "51820" in ports:
                    udp_51820 = True
                    break
        if (
            candidate.get("direction") == "INGRESS"
            and candidate.get("disabled") in (None, False)
            and isinstance(targets, list)
            and WIREGUARD_TAG in targets
            and udp_51820
        ):
            enabled_matches += 1
    provider_ready = (
        payload.get("status") == "RUNNING"
        and payload.get("canIpForward") is True
        and WIREGUARD_TAG in tag_items
        and enabled_matches > 0
    )
    return {
        **base,
        "status": "provider_ready" if provider_ready else "provider_mismatch",
        "required_permissions": [],
        "instance_readable": True,
        "firewall_readable": True,
        "instance_running": payload.get("status") == "RUNNING",
        "ip_forwarding_enabled": payload.get("canIpForward") is True,
        "wireguard_tag_present": WIREGUARD_TAG in tag_items,
        "network_interface_count": interface_count,
        "enabled_wireguard_rule_count": enabled_matches,
        "server_internal_readback_ready": provider_ready,
    }


def write_new_json(path: pathlib.Path, payload: dict[str, object]) -> None:
    """Write one new receipt without replacing prior evidence."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
