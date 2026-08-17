#!/usr/bin/env python3
"""민감정보 없이 기존 프로필 보존형 피어·재발급 경로를 판정한다."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA = "freeflexvpn-profile-reissue-readback/v1"
PEER_STATES = ("present", "absent", "unknown")
EVIDENCE_SCOPES = ("none", "historical_separate_profile", "current_candidate")
DEVICE_SCOPES = ("historical_record", "live_readback")
DEVICE_FIELDS = (
    "scope",
    "legacy_profile_present",
    "legacy_profile_enabled",
    "candidate_profile_present",
    "candidate_profile_enabled",
    "always_on_enabled",
    "lockdown_enabled",
)
SERVER_FIELDS = (
    "readback_available",
    "peer_count",
    "legacy_peer_state",
    "candidate_peer_state",
    "forwarding_ok",
    "nat_ok",
    "firewall_ok",
)
EVIDENCE_FIELDS = (
    "scope",
    "human_switch_confirmed",
    "tunnel_ok",
    "exit_path_ok",
    "dns_ok",
    "handshake_ok",
    "return_path_ok",
)
FORBIDDEN_FIELD_FRAGMENTS = (
    "privatekey",
    "publickey",
    "presharedkey",
    "endpoint",
    "assignedaddress",
    "clientip",
    "serverip",
    "observedip",
    "expectedip",
    "email",
    "token",
    "secret",
    "cookie",
    "password",
    "configuration",
    "configtext",
    "profilecontent",
)


def _normalized_key(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _reject_sensitive_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = _normalized_key(key)
            if any(fragment in normalized for fragment in FORBIDDEN_FIELD_FRAGMENTS):
                raise ValueError(f"민감 필드는 읽지 않습니다: {key}")
            _reject_sensitive_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_sensitive_fields(nested)


def _strict_object(value: Any, *, name: str, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} 객체가 필요합니다")
    unknown = set(value) - set(fields)
    missing = set(fields) - set(value)
    if unknown or missing:
        raise ValueError(f"{name} 필드가 계약과 다릅니다: missing={sorted(missing)} unknown={sorted(unknown)}")
    return {field: value[field] for field in fields}


def _require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field}는 true 또는 false여야 합니다")
    return value


def _require_tristate(value: Any, field: str) -> bool | None:
    if value not in (True, False, None) or (value is not None and type(value) is not bool):
        raise ValueError(f"{field}는 true, false, null 중 하나여야 합니다")
    return value


def evaluate_profile_reissue(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """읽기 전용 스냅샷으로 다음 안전 단계만 판정하며 어떤 변경도 실행하지 않는다."""
    _reject_sensitive_fields(snapshot)
    top = _strict_object(snapshot, name="snapshot", fields=("schema", "origin", "device", "server", "candidate_evidence"))
    if top["schema"] != SCHEMA:
        raise ValueError("지원하지 않는 profile reissue schema입니다")
    if top["origin"] != "read_only":
        raise ValueError("origin은 read_only여야 합니다")

    device = _strict_object(top["device"], name="device", fields=DEVICE_FIELDS)
    server = _strict_object(top["server"], name="server", fields=SERVER_FIELDS)
    evidence = _strict_object(top["candidate_evidence"], name="candidate_evidence", fields=EVIDENCE_FIELDS)
    if device["scope"] not in DEVICE_SCOPES:
        raise ValueError("device.scope가 올바르지 않습니다")
    for field in DEVICE_FIELDS[1:]:
        device[field] = _require_bool(device[field], f"device.{field}")
    server["readback_available"] = _require_bool(server["readback_available"], "server.readback_available")
    peer_count = server["peer_count"]
    if peer_count is not None and (type(peer_count) is not int or peer_count < 0):
        raise ValueError("server.peer_count는 0 이상의 정수 또는 null이어야 합니다")
    for field in ("legacy_peer_state", "candidate_peer_state"):
        if server[field] not in PEER_STATES:
            raise ValueError(f"server.{field}가 올바르지 않습니다")
    for field in ("forwarding_ok", "nat_ok", "firewall_ok"):
        server[field] = _require_tristate(server[field], f"server.{field}")
    if evidence["scope"] not in EVIDENCE_SCOPES:
        raise ValueError("candidate_evidence.scope가 올바르지 않습니다")
    evidence["human_switch_confirmed"] = _require_bool(
        evidence["human_switch_confirmed"], "candidate_evidence.human_switch_confirmed"
    )
    evidence_checks = ("tunnel_ok", "exit_path_ok", "dns_ok", "handshake_ok", "return_path_ok")
    for field in evidence_checks:
        evidence[field] = _require_tristate(evidence[field], f"candidate_evidence.{field}")

    if device["legacy_profile_enabled"] and not device["legacy_profile_present"]:
        raise ValueError("없는 기존 프로필을 켜짐으로 기록할 수 없습니다")
    if device["candidate_profile_enabled"] and not device["candidate_profile_present"]:
        raise ValueError("없는 후보 프로필을 켜짐으로 기록할 수 없습니다")
    if not server["readback_available"]:
        if peer_count is not None or any(server[field] != "unknown" for field in ("legacy_peer_state", "candidate_peer_state")):
            raise ValueError("서버 readback이 없으면 피어 개수·대응 상태를 단정할 수 없습니다")
        if any(server[field] is not None for field in ("forwarding_ok", "nat_ok", "firewall_ok")):
            raise ValueError("서버 readback이 없으면 전달·NAT·방화벽을 단정할 수 없습니다")
    if peer_count == 0 and any(server[field] == "present" for field in ("legacy_peer_state", "candidate_peer_state")):
        raise ValueError("피어 0개와 피어 present를 함께 기록할 수 없습니다")
    if peer_count is not None and peer_count < 2 and all(
        server[field] == "present" for field in ("legacy_peer_state", "candidate_peer_state")
    ):
        raise ValueError("기존/후보 피어가 모두 present이면 피어가 최소 2개여야 합니다")

    reasons: list[str] = []
    device_readback_live = device["scope"] == "live_readback"
    if not device_readback_live:
        reasons.append("live_device_readback_required")
    if evidence["scope"] == "historical_separate_profile":
        reasons.append("historical_candidate_evidence_not_current_proof")
    if not device["legacy_profile_present"]:
        reasons.append("legacy_profile_presence_unconfirmed")
    if device["legacy_profile_enabled"]:
        reasons.append("legacy_profile_enabled_preserve_without_change")
    if device["always_on_enabled"]:
        reasons.append("always_on_requires_human_review")
    if device["lockdown_enabled"]:
        reasons.append("lockdown_requires_human_review")
    if not server["readback_available"]:
        reasons.append("server_readback_required")
    else:
        if server["legacy_peer_state"] == "unknown":
            reasons.append("legacy_peer_mapping_unknown")
        if server["candidate_peer_state"] == "unknown":
            reasons.append("candidate_peer_mapping_unknown")
        for field in ("forwarding_ok", "nat_ok", "firewall_ok"):
            if server[field] is not True:
                reasons.append(f"server_{field}_not_verified")

    device_candidate = device["candidate_profile_present"]
    server_candidate = server["candidate_peer_state"]
    mapping_mismatch = server["readback_available"] and (
        (device_candidate and server_candidate == "absent")
        or (not device_candidate and server_candidate == "present")
    )
    evidence_failed = any(evidence[field] is False for field in evidence_checks)
    current_evidence_complete = (
        evidence["scope"] == "current_candidate"
        and all(evidence[field] is True for field in evidence_checks)
        and evidence["human_switch_confirmed"]
        and not device["candidate_profile_enabled"]
    )
    server_infra_ready = server["readback_available"] and all(
        server[field] is True for field in ("forwarding_ok", "nat_ok", "firewall_ok")
    ) and all(server[field] != "unknown" for field in ("legacy_peer_state", "candidate_peer_state"))
    device_policy_safe = device_readback_live and not any(
        device[field] for field in ("legacy_profile_enabled", "always_on_enabled", "lockdown_enabled")
    )

    if not device_readback_live or not server["readback_available"]:
        stage = "readback_required"
        next_action = "read_only_device_and_server_compare"
    elif mapping_mismatch:
        stage = "mapping_investigation_required"
        next_action = "compare_candidate_mapping_without_keys_or_addresses"
        reasons.append("candidate_device_server_mapping_mismatch")
    elif evidence_failed:
        stage = "candidate_failure_investigation"
        next_action = "keep_both_profiles_off_and_investigate_failed_evidence"
        reasons.append("candidate_evidence_failed")
    elif not device_candidate and server_candidate == "absent" and server_infra_ready and device_policy_safe:
        stage = "candidate_issue_review_ready"
        next_action = "request_explicit_approval_for_isolated_candidate_issue"
    elif not device_candidate or server_candidate != "present":
        stage = "candidate_reissue_planning"
        next_action = "complete_read_only_mapping_before_candidate_issue"
    elif current_evidence_complete:
        stage = "legacy_retirement_review_ready"
        next_action = "request_explicit_approval_before_any_legacy_retirement"
    else:
        stage = "candidate_validation_required"
        next_action = "human_switch_and_collect_current_candidate_evidence"
        if not evidence["human_switch_confirmed"]:
            reasons.append("human_switch_not_confirmed")
        if device["candidate_profile_enabled"]:
            reasons.append("candidate_profile_must_be_off_after_return_path")
        for field in evidence_checks:
            if evidence[field] is not True:
                reasons.append(f"candidate_{field}_not_verified")

    return {
        "schema": "freeflexvpn-profile-reissue-decision/v1",
        "read_only": True,
        "status": stage,
        "next_action": next_action,
        "legacy_profile_action": "preserve",
        "server_peer_action": "none",
        "device_setting_action": "none",
        "mutation_performed": False,
        "ready_for_candidate_issue_review": stage == "candidate_issue_review_ready",
        "ready_for_legacy_retirement_review": stage == "legacy_retirement_review_ready",
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "snapshot": {
            "device": device,
            "server": server,
            "candidate_evidence": evidence,
        },
        "evidence_boundary": {
            "historical_candidate_is_current_proof": False,
            "actual_device_change_performed": False,
            "server_change_performed": False,
            "contains_sensitive_data": False,
        },
    }
