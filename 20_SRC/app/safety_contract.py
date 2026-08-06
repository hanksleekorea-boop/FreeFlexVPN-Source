#!/usr/bin/env python3
"""FreeFlexVPN 목표 OS의 실제 안전 검증 결과를 판정하는 고정 계약."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


TARGET_OSES = ("ios", "android", "windows")
REQUIRED_CHECKS = (
    "tunnel_exit",
    "dns_no_leak",
    "ipv6_safe",
    "kill_switch_blocks",
    "wifi_cellular_reconnect",
    "sleep_wake_reconnect",
    "restart_reconnect",
    "captive_portal_recovery",
)
ACTUAL_ORIGIN = "actual_device"


def _as_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("run_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def evaluate_os_run(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """한 OS 실행을 통과·실패·확인 불가로 분리한다.

    이 함수의 로컬 단위 테스트는 계약 검증(L)일 뿐 실제 기기 증거(D)가 아니다.
    실제 실행으로 집계하려면 origin=actual_device와 구체적인 기기·OS·후보 ID가
    있어야 하며, 그래도 외부 증거 원장에 원본 로그/화면을 별도로 보존해야 한다.
    """
    os_family = evidence.get("os_family")
    if os_family not in TARGET_OSES:
        raise ValueError("os_family은 ios, android, windows 중 하나여야 합니다")
    for field in ("candidate_id", "device_id", "os_version", "server_id", "origin"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ValueError(f"{field}가 비어 있거나 너무 깁니다")
    run_at_value = evidence.get("run_at")
    if not isinstance(run_at_value, (str, datetime)):
        raise ValueError("run_at이 비어 있거나 올바르지 않습니다")
    run_at = _as_utc(run_at_value)
    checks = evidence.get("checks")
    if not isinstance(checks, Mapping):
        raise ValueError("checks 객체가 필요합니다")
    unknown_extra = set(checks) - set(REQUIRED_CHECKS)
    if unknown_extra:
        raise ValueError(f"정의되지 않은 안전 검사입니다: {sorted(unknown_extra)}")
    normalized = {name: checks.get(name) for name in REQUIRED_CHECKS}
    if any(value not in (True, False, None) for value in normalized.values()):
        raise ValueError("검사 값은 true, false, null 중 하나여야 합니다")
    failed = [name for name, value in normalized.items() if value is False]
    unknown = [name for name, value in normalized.items() if value is None]
    missing = [name for name in REQUIRED_CHECKS if name not in checks]
    unknown = sorted(set(unknown + missing))
    origin_actual = evidence["origin"] == ACTUAL_ORIGIN
    if failed:
        status = "failed"
    elif unknown:
        status = "unknown"
    elif not origin_actual:
        status = "adapter_or_demo"
    else:
        status = "passed"
    return {
        "candidate_id": str(evidence["candidate_id"]),
        "device_id": str(evidence["device_id"]),
        "os_family": str(os_family),
        "os_version": str(evidence["os_version"]),
        "server_id": str(evidence["server_id"]),
        "run_at": run_at.isoformat(),
        "origin": str(evidence["origin"]),
        "status": status,
        "passed": status == "passed",
        "failed_checks": failed,
        "unknown_checks": unknown,
        "checks": normalized,
        "evidence_note": (
            "실제 기기 원본 증거와 결합해야 D로 기록할 수 있습니다"
            if origin_actual else "시뮬레이션·어댑터 결과는 실제 기기 증거가 아닙니다"
        ),
    }


def evaluate_release_matrix(runs: list[Mapping[str, Any]], *, candidate_id: str) -> dict[str, Any]:
    """동일 후보의 iOS·Android·Windows 전건 통과만 R6 안전 준비로 판정한다."""
    if not candidate_id:
        raise ValueError("candidate_id가 필요합니다")
    evaluated = [evaluate_os_run(run) for run in runs]
    mismatched = [run["os_family"] for run in evaluated if run["candidate_id"] != candidate_id]
    by_os: dict[str, list[dict[str, Any]]] = {name: [] for name in TARGET_OSES}
    for run in evaluated:
        by_os[run["os_family"]].append(run)
    passed_os = [name for name in TARGET_OSES if any(run["passed"] for run in by_os[name])]
    missing_os = [name for name in TARGET_OSES if not by_os[name]]
    unresolved_os = [
        name for name in TARGET_OSES if by_os[name] and not any(run["passed"] for run in by_os[name])
    ]
    ready = not mismatched and len(passed_os) == len(TARGET_OSES)
    return {
        "candidate_id": candidate_id,
        "ready": ready,
        "status": "passed" if ready else "incomplete",
        "passed_os": passed_os,
        "missing_os": missing_os,
        "unresolved_os": unresolved_os,
        "mismatched_candidate_os": mismatched,
        "required_checks": list(REQUIRED_CHECKS),
        "runs": evaluated,
        "evidence_level": "D only after original device evidence is attached",
    }
