"""Locate one approved GCP project by fingerprint without storing or printing project identifiers."""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence

from infra.gcp_readback_access import check_readback_access, target_fingerprint


SCHEMA = "FreeFlexVPNGCPTargetLocatorV1"
PROJECT = re.compile(r"^[a-z](?:[-a-z0-9]{4,61}[a-z0-9])$")
FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


Runner = Callable[[Sequence[str]], CommandResult]


def _run(argv: Sequence[str]) -> CommandResult:
    command = _process_command(argv)
    completed = subprocess.run(
        list(command), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=45
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _process_command(argv: Sequence[str]) -> tuple[str, ...]:
    """Run a Windows gcloud PowerShell wrapper through PowerShell, never through a shell string."""
    if not argv:
        raise ValueError("empty command")
    if pathlib.Path(argv[0]).suffix.lower() == ".ps1":
        cmd_sibling = pathlib.Path(argv[0]).with_suffix(".cmd")
        if cmd_sibling.is_file():
            return (str(cmd_sibling), *[str(value) for value in argv[1:]])
        return ("powershell.exe", "-NoProfile", "-File", str(argv[0]), *[str(value) for value in argv[1:]])
    return tuple(str(value) for value in argv)


def _project_list_command(gcloud: str) -> tuple[str, ...]:
    return (gcloud, "projects", "list", "--format=value(projectId)")


def _project_fingerprint(project: str) -> str:
    return hashlib.sha256(project.encode("utf-8")).hexdigest()


def locate_target(
    *,
    gcloud: str,
    expected_target_fingerprint: str,
    zone: str,
    instance: str,
    runner: Runner = _run,
    checked_at: datetime | None = None,
) -> tuple[dict[str, object], str | None]:
    """Return redacted selection evidence and retain a matching project only in memory."""
    if not FINGERPRINT.fullmatch(expected_target_fingerprint):
        raise ValueError("expected target fingerprint must be lowercase SHA-256")
    checked_at = checked_at or datetime.now(timezone.utc)
    result = runner(_project_list_command(gcloud))
    base: dict[str, object] = {
        "schema": SCHEMA,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "expected_target_fingerprint": expected_target_fingerprint,
        "contains_project_identifier": False,
        "contains_account_identifier": False,
        "contains_network_address": False,
        "mutation_count": 0,
    }
    if result.returncode:
        return ({**base, "status": "project_listing_unavailable", "accessible_project_count": 0, "matching_count": 0}, None)

    projects = [line.strip() for line in result.stdout.splitlines() if PROJECT.fullmatch(line.strip())]
    matches = [project for project in projects if target_fingerprint(project, zone, instance) == expected_target_fingerprint]
    if not matches:
        return ({**base, "status": "target_not_accessible", "accessible_project_count": len(projects), "matching_count": 0}, None)
    if len(matches) != 1:
        return ({**base, "status": "ambiguous_target", "accessible_project_count": len(projects), "matching_count": len(matches)}, None)
    return ({**base, "status": "target_selected", "accessible_project_count": len(projects), "matching_count": 1, "selected_project_fingerprint": _project_fingerprint(matches[0])}, matches[0])


def locate_and_check(
    *,
    gcloud: str,
    expected_target_fingerprint: str,
    zone: str,
    instance: str,
    runner: Runner = _run,
    checked_at: datetime | None = None,
) -> dict[str, object]:
    """Locate target then perform existing provider readback only when one exact match exists."""
    located, project = locate_target(
        gcloud=gcloud, expected_target_fingerprint=expected_target_fingerprint, zone=zone, instance=instance,
        runner=runner, checked_at=checked_at,
    )
    if project is None:
        return {**located, "provider_readback_attempted": False, "server_internal_readback_ready": False}

    def adapted(argv: Sequence[str]):
        reply = runner(argv)
        return type("Reply", (), {"returncode": reply.returncode, "stdout": reply.stdout, "stderr": reply.stderr})()

    provider = check_readback_access(gcloud=gcloud, project=project, zone=zone, instance=instance, runner=adapted, checked_at=checked_at)
    return {
        **located,
        "provider_readback_attempted": True,
        "provider_status": provider["status"],
        "instance_readable": provider["instance_readable"],
        "firewall_readable": provider["firewall_readable"],
        "server_internal_readback_ready": provider["server_internal_readback_ready"],
    }
