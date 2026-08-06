#!/usr/bin/env python3
"""T1~T10 실환경 출시 관문을 실패 폐쇄형으로 판정한다.

이 모듈의 단위 테스트는 구현·로컬 계약 증거일 뿐 실제 서버, 기기 또는
독립 사용자 증거가 아니다. 실제 통과 판정은 원본 로그·화면·측정 결과를
별도 증거 원장에 보존한 뒤 같은 후보 ID로 평가해야 한다.
"""
from __future__ import annotations

import ipaddress
import math
import statistics
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from app.runtime_evidence import VerifiedArtifacts


TEST_IDS = tuple(f"T{index}" for index in range(1, 11))
TARGET_OSES = ("ios", "android", "windows")
ACTUAL_ORIGIN = "actual_target"
FREE_MONTHLY_BYTES = 1_000_000_000
MAX_HANDSHAKE_AGE_SECONDS = 180
MAX_QUOTA_TRANSITION_SECONDS = 60
MAX_ALERT_SECONDS = 180
MIN_SPEED_RUNS = 3
MIN_DOWNLOAD_MBPS = 30.0
MAX_PACKET_LOSS_PERCENT = 1.0


def _as_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise ValueError("run_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, *, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field}가 비어 있거나 너무 깁니다")
    return value.strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _public_ip(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not any((parsed.is_private, parsed.is_loopback, parsed.is_link_local,
                    parsed.is_multicast, parsed.is_unspecified, parsed.is_reserved))


def _strings(value: Any) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    return [item.strip() for item in value]


def _result(test_id: str, reasons: list[str], *, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "passed": not reasons,
        "status": "passed" if not reasons else "failed",
        "reasons": reasons,
        "details": dict(details or {}),
    }


def _t1(value: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    runs = value.get("os_runs")
    if not isinstance(runs, list):
        return _result("T1", ["os_runs_missing"])
    passed_os: list[str] = []
    for os_family in TARGET_OSES:
        matching = [run for run in runs if isinstance(run, Mapping) and run.get("os_family") == os_family]
        if any(
            isinstance(run.get("run_id"), str)
            and bool(run["run_id"].strip())
            and run.get("candidate_id") == candidate_id
            and run.get("config_source") == "official_wireguard"
            and run.get("tunnel_started") is True
            and (_number(run.get("handshake_age_seconds")) is not None)
            and 0 <= float(run["handshake_age_seconds"]) <= MAX_HANDSHAKE_AGE_SECONDS
            and (_number(run.get("sustained_seconds")) is not None)
            and float(run["sustained_seconds"]) >= 60
            for run in matching
        ):
            passed_os.append(os_family)
    run_ids = [run.get("run_id") for run in runs if isinstance(run, Mapping) and isinstance(run.get("run_id"), str)]
    if len(run_ids) != len(set(run_ids)):
        return _result("T1", ["duplicate_run_id"], details={"passed_os": passed_os})
    missing = [name for name in TARGET_OSES if name not in passed_os]
    return _result("T1", [f"connection_not_proven:{name}" for name in missing], details={"passed_os": passed_os})


def _t2(value: Mapping[str, Any]) -> dict[str, Any]:
    observed = value.get("observed_exit_ip")
    expected = value.get("expected_exit_ip")
    baseline = value.get("baseline_ip")
    reasons = []
    if not all(_public_ip(item) for item in (observed, expected, baseline)):
        reasons.append("public_ip_evidence_invalid")
    if observed != expected:
        reasons.append("exit_ip_mismatch")
    if observed == baseline:
        reasons.append("exit_ip_unchanged")
    if value.get("observed_country") != value.get("expected_country"):
        reasons.append("exit_country_mismatch")
    return _result("T2", reasons)


def _t3(value: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _strings(value.get("baseline_resolvers"))
    tunnel = _strings(value.get("tunnel_resolvers"))
    unexpected = _strings(value.get("unexpected_resolvers"))
    queries = value.get("queries_tested")
    reasons = []
    if baseline is None or tunnel is None or unexpected is None:
        reasons.append("resolver_evidence_invalid")
    else:
        if not tunnel:
            reasons.append("tunnel_resolver_missing")
        if set(baseline) & set(tunnel):
            reasons.append("baseline_resolver_exposed")
        if unexpected:
            reasons.append("unexpected_resolver_exposed")
    if not isinstance(queries, int) or isinstance(queries, bool) or queries < 10:
        reasons.append("dns_query_sample_too_small")
    return _result("T3", reasons)


def _t4(value: Mapping[str, Any]) -> dict[str, Any]:
    raw_runs = value.get("download_mbps_runs")
    runs = [_number(item) for item in raw_runs] if isinstance(raw_runs, list) else []
    valid = [item for item in runs if item is not None and item >= 0]
    loss = _number(value.get("packet_loss_percent"))
    measurement_ids = _strings(value.get("measurement_ids"))
    reasons = []
    if len(valid) < MIN_SPEED_RUNS:
        reasons.append("speed_runs_too_few")
        median = None
    else:
        median = statistics.median(valid)
        if median < MIN_DOWNLOAD_MBPS:
            reasons.append("download_below_30_mbps")
    if loss is None or not 0 <= loss <= MAX_PACKET_LOSS_PERCENT:
        reasons.append("packet_loss_above_1_percent_or_missing")
    if measurement_ids is None or len(measurement_ids) != len(valid) or len(set(measurement_ids)) != len(measurement_ids):
        reasons.append("measurement_ids_missing_or_duplicate")
    return _result("T4", reasons, details={"median_download_mbps": median, "valid_runs": len(valid)})


def _t5(value: Mapping[str, Any]) -> dict[str, Any]:
    delay = _number(value.get("blocked_after_seconds"))
    limit = value.get("limit_bytes")
    usage = value.get("usage_bytes")
    reasons = []
    if not isinstance(limit, int) or not isinstance(usage, int) or usage < limit or limit <= 0:
        reasons.append("quota_threshold_not_proven")
    if delay is None or not 0 <= delay <= MAX_QUOTA_TRANSITION_SECONDS:
        reasons.append("quota_block_slower_than_poll_cycle")
    if value.get("traffic_blocked") is not True:
        reasons.append("traffic_not_blocked")
    if value.get("user_notice") is not True:
        reasons.append("quota_notice_missing")
    return _result("T5", reasons)


def _t6(value: Mapping[str, Any]) -> dict[str, Any]:
    delay = _number(value.get("reactivated_after_seconds"))
    reasons = []
    if value.get("free_bytes_after") != FREE_MONTHLY_BYTES:
        reasons.append("monthly_free_balance_not_restored")
    if value.get("paid_bytes_before") != value.get("paid_bytes_after"):
        reasons.append("paid_balance_changed_on_reset")
    if value.get("traffic_active") is not True:
        reasons.append("peer_not_reactivated")
    if delay is None or not 0 <= delay <= MAX_QUOTA_TRANSITION_SECONDS:
        reasons.append("reset_slower_than_poll_cycle")
    return _result("T6", reasons)


def _t7(value: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    if value.get("active_key_count") != 2:
        reasons.append("two_active_keys_not_proven")
    if value.get("third_key_rejected") is not True:
        reasons.append("third_key_not_rejected")
    if value.get("duplicate_key_rejected") is not True:
        reasons.append("duplicate_key_not_rejected")
    return _result("T7", reasons)


def _t8(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "tcp_25_blocked", "tcp_6881_6999_blocked", "udp_6881_6999_blocked",
        "tcp_51413_blocked", "udp_51413_blocked",
    )
    return _result("T8", [f"not_proven:{field}" for field in fields if value.get(field) is not True])


def _t9(value: Mapping[str, Any]) -> dict[str, Any]:
    delay = _number(value.get("alert_after_seconds"))
    reasons = []
    if value.get("node_stopped") is not True:
        reasons.append("node_stop_not_proven")
    if value.get("alert_received") is not True or value.get("channel") != "telegram":
        reasons.append("telegram_alert_missing")
    if delay is None or not 0 <= delay <= MAX_ALERT_SECONDS:
        reasons.append("alert_slower_than_180_seconds")
    if value.get("contains_secret") is not False:
        reasons.append("alert_secret_safety_unknown")
    return _result("T9", reasons)


def _t10(value: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    participants = value.get("participants")
    if not isinstance(participants, list):
        return _result("T10", ["participants_missing"])
    participant_refs = [
        item.get("participant_ref") for item in participants
        if isinstance(item, Mapping) and isinstance(item.get("participant_ref"), str) and item.get("participant_ref").strip()
    ]
    eligible = [
        item for item in participants
        if isinstance(item, Mapping)
        and item.get("candidate_id") == candidate_id
        and item.get("consented") is True
        and item.get("independent") is True
        and item.get("actual_protected") is True
        and isinstance(item.get("active_weeks"), int)
        and not isinstance(item.get("active_weeks"), bool)
        and item.get("active_weeks") >= 4
    ]
    completed = [item for item in eligible if item.get("completed_without_help") is True]
    reasons = []
    if len(eligible) < 5:
        reasons.append("fewer_than_5_eligible_users")
    if len(completed) < 4:
        reasons.append("fewer_than_4_unassisted_successes")
    if len(participant_refs) != len(participants) or len(participant_refs) != len(set(participant_refs)):
        reasons.append("participant_refs_missing_or_duplicate")
    observation_days = value.get("observation_days")
    if not isinstance(observation_days, int) or isinstance(observation_days, bool) or observation_days < 28:
        reasons.append("pilot_shorter_than_4_weeks")
    return _result("T10", reasons, details={"eligible_users": len(eligible), "unassisted_successes": len(completed)})


EVALUATORS = {
    "T1": _t1, "T2": _t2, "T3": _t3, "T4": _t4, "T5": _t5,
    "T6": _t6, "T7": _t7, "T8": _t8, "T9": _t9,
}


def evaluate_runtime_acceptance(
    evidence: Mapping[str, Any],
    *,
    verified_artifacts: "VerifiedArtifacts | None" = None,
) -> dict[str, Any]:
    """같은 후보의 T1~T10과 검증된 원본 파일이 있을 때만 ready를 반환한다."""
    candidate_id = _text(evidence.get("candidate_id"), "candidate_id")
    run_at_value = evidence.get("run_at")
    if not isinstance(run_at_value, (str, datetime)):
        raise ValueError("run_at이 필요합니다")
    run_at = _as_utc(run_at_value)
    origin = _text(evidence.get("origin"), "origin")
    tests = evidence.get("tests")
    if not isinstance(tests, Mapping):
        raise ValueError("tests 객체가 필요합니다")
    unknown = sorted(set(tests) - set(TEST_IDS))
    if unknown:
        raise ValueError(f"정의되지 않은 테스트입니다: {unknown}")

    results: list[dict[str, Any]] = []
    for test_id in TEST_IDS:
        value = tests.get(test_id)
        if not isinstance(value, Mapping):
            results.append({"test_id": test_id, "passed": False, "status": "unknown", "reasons": ["evidence_missing"], "details": {}})
        elif test_id in ("T1", "T10"):
            results.append(_t1(value, candidate_id) if test_id == "T1" else _t10(value, candidate_id))
        else:
            results.append(EVALUATORS[test_id](value))

    all_tests_passed = all(item["passed"] for item in results)
    actual = origin == ACTUAL_ORIGIN
    artifacts_ready = bool(
        verified_artifacts is not None
        and verified_artifacts.candidate_id == candidate_id
        and verified_artifacts.complete
    )
    ready = all_tests_passed and actual and artifacts_ready
    if ready:
        status = "passed"
    elif all_tests_passed and actual and not artifacts_ready:
        status = "unverified_artifacts"
    elif all_tests_passed and not actual:
        status = "adapter_or_demo"
    else:
        status = "incomplete"
    return {
        "schema": "FreeFlexVPNRuntimeAcceptanceV2",
        "candidate_id": candidate_id,
        "run_at": run_at.isoformat(),
        "origin": origin,
        "ready": ready,
        "status": status,
        "artifacts_verified": artifacts_ready,
        "artifact_bundle_sha256": verified_artifacts.bundle_sha256 if artifacts_ready else None,
        "artifact_count": len(verified_artifacts.artifacts) if artifacts_ready else 0,
        "passed_tests": [item["test_id"] for item in results if item["passed"]],
        "blocked_tests": [item["test_id"] for item in results if not item["passed"]],
        "tests": results,
        "evidence_note": "원본 서버·기기·사용자 증거와 결합한 경우에만 D/U로 기록할 수 있습니다",
    }
