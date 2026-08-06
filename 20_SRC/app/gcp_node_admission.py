#!/usr/bin/env python3
"""첫 GCP 실제 노드를 검증하되 2공급자 R6 완료로 승격하지 않는다."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from app.ssh_node_adapter import SSHNodeSpec


GCP_PROVIDER_REFS = {"gcp", "google-cloud", "google-cloud-platform"}


def _as_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("checked_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"id": name, "passed": bool(passed), "detail": detail}


def evaluate_gcp_configuration(
    nodes: Iterable[SSHNodeSpec], *, checked_at: datetime | str | None = None
) -> dict[str, Any]:
    current = _as_utc(checked_at)
    items = list(nodes)
    node = items[0] if len(items) == 1 else None
    provider_ok = bool(node and node.provider_ref.strip().lower() in GCP_PROVIDER_REFS)
    checks = [
        _check("exactly_one_first_node", len(items) == 1, f"configured={len(items)}, required=1"),
        _check("provider_is_gcp", provider_ok, "gcp provider reference required"),
        _check(
            "console_exit_evidence_present",
            bool(node and node.exit_verified and node.verified_at is not None),
            "public exit IP and timestamp must be console-verified",
        ),
    ]
    configuration_ready = all(item["passed"] for item in checks)
    return {
        "schema": "FreeFlexVPNGCPNodeConfigurationPreflightV1",
        "checked_at": current.isoformat(),
        "mode": "config_only",
        "provider": "gcp",
        "configuration_ready": configuration_ready,
        "admission_ready": False,
        "ready": False,
        "r6_ready": False,
        "network_attempted": False,
        "configured_nodes": len(items),
        "provider_diversity_credit": 1 if provider_ok else 0,
        "checks": checks,
        "evidence_level": "configuration validation only; no cloud, server, device, or user evidence",
        "next_gate": "run live GCP node admission" if configuration_ready else "fix failed GCP configuration checks",
    }


def evaluate_gcp_admission(
    nodes: Iterable[SSHNodeSpec],
    runtime_result: Mapping[str, Any],
    public_catalog: Mapping[str, Any],
    *,
    checked_at: datetime | str | None = None,
) -> dict[str, Any]:
    current = _as_utc(checked_at)
    items = list(nodes)
    configuration = evaluate_gcp_configuration(items, checked_at=current)
    candidate_id = items[0].server_id if len(items) == 1 else None
    health_rows = runtime_result.get("health")
    health_rows = health_rows if isinstance(health_rows, list) else []
    valid_health = [
        row for row in health_rows
        if isinstance(row, Mapping) and str(row.get("server_id", "")) == candidate_id
    ]
    health_exact = len(health_rows) == 1 and len(valid_health) == 1
    healthy = health_exact and valid_health[0].get("healthy") is True and valid_health[0].get("catalog_applied") is True
    public_rows = public_catalog.get("servers")
    public_rows = public_rows if isinstance(public_rows, list) else []
    valid_public = [
        row for row in public_rows
        if isinstance(row, Mapping) and str(row.get("server_id", "")) == candidate_id
    ]
    catalog_exact = len(public_rows) == 1 and len(valid_public) == 1
    counter_error = runtime_result.get("counter_error")
    checks = list(configuration["checks"]) + [
        _check("one_live_health_readback", healthy, f"health_rows={len(health_rows)}, matching={len(valid_health)}"),
        _check("catalog_exactly_matches_candidate", catalog_exact, f"public_rows={len(public_rows)}, matching={len(valid_public)}"),
        _check("counter_readback_succeeded", counter_error is None, "ok" if counter_error is None else str(counter_error)),
        _check("catalog_persistence_available", public_catalog.get("persistence_status") == "persistent", str(public_catalog.get("persistence_status", "unknown"))),
    ]
    admitted = all(item["passed"] for item in checks)
    return {
        "schema": "FreeFlexVPNGCPNodeAdmissionV1",
        "checked_at": current.isoformat(),
        "mode": "live_single_provider",
        "provider": "gcp",
        "status": "admitted_first_node" if admitted else "blocked",
        "admission_ready": admitted,
        "ready": False,
        "r6_ready": False,
        "network_attempted": True,
        "configured_nodes": len(items),
        "healthy_nodes": 1 if healthy else 0,
        "public_nodes": 1 if catalog_exact else 0,
        "provider_diversity_credit": 1 if admitted else 0,
        "server_result": {
            "server_id": candidate_id,
            "country_code": items[0].country_code if len(items) == 1 else None,
            "healthy": healthy,
            "public": catalog_exact,
        },
        "checks": checks,
        "evidence_level": "single GCP server readback; not two-provider R6, target-device, or independent-user evidence",
        "next_gate": "add and verify a different cloud provider, then run R6" if admitted else "fix failed GCP node checks and rerun",
    }
