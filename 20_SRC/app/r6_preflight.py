#!/usr/bin/env python3
"""R6 실제 VPN 승격 전에 노드 분산·실시간 readback을 fail-closed로 판정한다."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from app.ssh_node_adapter import SSHNodeSpec


MIN_LIVE_NODES = 2


def _as_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("checked_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"id": name, "passed": bool(passed), "detail": detail}


def evaluate_node_topology(nodes: Iterable[SSHNodeSpec]) -> dict[str, Any]:
    """설정만으로 R6의 2공급자 분산과 식별자 충돌을 판정한다."""
    items = list(nodes)
    providers = {node.provider_ref for node in items}
    exit_ips = {node.exit_ip for node in items}
    endpoints = {node.endpoint for node in items}
    node_ids = {node.node_id for node in items}
    public_keys = {node.server_public_key for node in items}
    checks = [
        _check("at_least_two_nodes", len(items) >= MIN_LIVE_NODES, f"configured={len(items)}, required={MIN_LIVE_NODES}"),
        _check("distinct_providers", len(providers) >= MIN_LIVE_NODES, f"distinct={len(providers)}, required={MIN_LIVE_NODES}"),
        _check("distinct_exit_ips", len(exit_ips) == len(items), f"distinct={len(exit_ips)}, configured={len(items)}"),
        _check("distinct_endpoints", len(endpoints) == len(items), f"distinct={len(endpoints)}, configured={len(items)}"),
        _check("distinct_node_ids", len(node_ids) == len(items), f"distinct={len(node_ids)}, configured={len(items)}"),
        _check("distinct_server_keys", len(public_keys) == len(items), f"distinct={len(public_keys)}, configured={len(items)}"),
        _check("all_exit_verified", all(node.exit_verified and node.verified_at is not None for node in items), "all nodes require console-verified exit evidence"),
    ]
    return {
        "ready": all(item["passed"] for item in checks),
        "configured_nodes": len(items),
        "distinct_providers": len(providers),
        "checks": checks,
    }


def evaluate_configuration_preflight(
    nodes: Iterable[SSHNodeSpec], *, checked_at: datetime | str | None = None
) -> dict[str, Any]:
    """SSH 연결 없이 외부 설정의 R6 토폴로지만 검사한다.

    설정이 통과해도 실서버 readback은 없으므로 ``ready``는 항상 false다. 운영자가
    configuration_ready를 실제 R6 통과로 잘못 승격하지 못하도록 증거 경계를 고정한다.
    """
    current = _as_utc(checked_at)
    items = list(nodes)
    topology = evaluate_node_topology(items)
    return {
        "schema": "FreeFlexVPNR6ConfigurationPreflightV1",
        "checked_at": current.isoformat(),
        "mode": "config_only",
        "configuration_ready": topology["ready"],
        "ready": False,
        "status": "configuration_ready" if topology["ready"] else "blocked",
        "network_attempted": False,
        "evidence_level": "configuration_validation_only; no server, device, or user evidence",
        "configured_nodes": topology["configured_nodes"],
        "distinct_providers": topology["distinct_providers"],
        "checks": topology["checks"],
        "next_gate": "run live R6 server preflight" if topology["ready"] else "fix failed configuration checks",
    }


def evaluate_r6_preflight(
    nodes: Iterable[SSHNodeSpec],
    runtime_result: Mapping[str, Any],
    public_catalog: Mapping[str, Any],
    *,
    checked_at: datetime | str | None = None,
) -> dict[str, Any]:
    """실제 SSH health·counter readback과 공개 카탈로그를 한 후보로 묶어 판정한다.

    반환값은 host, identity 경로, endpoint, IP, 공개키를 포함하지 않아 증거 파일에
    저장해도 런타임 비밀·제어면 주소가 노출되지 않는다.
    """
    current = _as_utc(checked_at)
    items = list(nodes)
    by_server = {node.server_id: node for node in items}
    configured_ids = set(by_server)
    topology = evaluate_node_topology(items)
    health_rows = runtime_result.get("health")
    health_rows = health_rows if isinstance(health_rows, list) else []
    healthy_ids = {
        str(row.get("server_id"))
        for row in health_rows
        if isinstance(row, Mapping) and row.get("healthy") is True and row.get("catalog_applied") is True
    }
    public_rows = public_catalog.get("servers")
    public_rows = public_rows if isinstance(public_rows, list) else []
    public_row_ids = [
        str(row.get("server_id", "")).strip()
        for row in public_rows
        if isinstance(row, Mapping) and str(row.get("server_id", "")).strip()
    ]
    public_id_counts = Counter(public_row_ids)
    public_ids = set(public_row_ids)
    malformed_public_rows = len(public_rows) - len(public_row_ids)
    duplicate_public_rows = sum(count - 1 for count in public_id_counts.values() if count > 1)
    unknown_public_ids = public_ids - configured_ids
    catalog_rows_valid = not (malformed_public_rows or duplicate_public_rows or unknown_public_ids)
    healthy_providers = {by_server[server_id].provider_ref for server_id in healthy_ids if server_id in by_server}
    counter_error = runtime_result.get("counter_error")
    checks = list(topology["checks"]) + [
        _check("two_live_health_readbacks", len(healthy_ids) >= MIN_LIVE_NODES, f"healthy={len(healthy_ids)}, required={MIN_LIVE_NODES}"),
        _check("two_live_providers", len(healthy_providers) >= MIN_LIVE_NODES, f"healthy_provider_count={len(healthy_providers)}"),
        _check(
            "catalog_rows_are_candidate_bound",
            catalog_rows_valid,
            f"malformed={malformed_public_rows}, duplicate={duplicate_public_rows}, unknown={len(unknown_public_ids)}",
        ),
        _check("catalog_matches_health", catalog_rows_valid and public_ids == healthy_ids and len(public_ids) >= MIN_LIVE_NODES, f"public={len(public_ids)}, healthy={len(healthy_ids)}"),
        _check("counter_readback_succeeded", counter_error is None, "ok" if counter_error is None else str(counter_error)),
        _check("catalog_persistence_available", public_catalog.get("persistence_status") == "persistent", str(public_catalog.get("persistence_status", "unknown"))),
    ]
    ready = all(item["passed"] for item in checks)
    return {
        "schema": "FreeFlexVPNR6ServerPreflightV1",
        "checked_at": current.isoformat(),
        "ready": ready,
        "status": "passed" if ready else "blocked",
        "evidence_level": "server_readback; not target-device or independent-user evidence",
        "configured_nodes": len(items),
        "healthy_nodes": len(healthy_ids),
        "public_nodes": len(public_ids),
        "distinct_healthy_providers": len(healthy_providers),
        "server_results": [
            {
                "server_id": node.server_id,
                "country_code": node.country_code,
                "healthy": node.server_id in healthy_ids,
                "public": node.server_id in public_ids,
            }
            for node in sorted(items, key=lambda value: value.server_id)
        ],
        "checks": checks,
        "next_gate": "iOS, Android, Windows same-candidate safety matrix" if ready else "fix failed server checks and rerun",
    }
