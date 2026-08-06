#!/usr/bin/env python3
"""출구 IP·핸드셰이크·안전 근거를 조합하는 보호 상태 판정."""
from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any


HANDSHAKE_MAX_AGE_SECONDS = 180
FUTURE_CLOCK_TOLERANCE_SECONDS = 30
ACTIVE_SERVER_HEALTH = ("healthy", "busy")


def _as_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _valid_ip(value: str | None) -> bool:
    if value is None:
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def evaluate_connection(
    *,
    profile_present: bool,
    tunnel_started: bool,
    observed_exit_ip: str | None,
    expected_exit_ip: str | None,
    server_health: str | None,
    handshake_at: datetime | str | None,
    dns_protected: bool | None,
    ipv6_protected: bool | None,
    kill_switch_protected: bool | None,
    checked_at: datetime | str | None = None,
) -> dict[str, Any]:
    """다섯 상태 중 하나를 반환한다. 모든 필수 근거가 참일 때만 protected다."""
    checked = _as_utc(checked_at) or datetime.now(timezone.utc)
    result: dict[str, Any] = {
        "state": "disconnected",
        "protected": False,
        "observed_exit_ip": observed_exit_ip if _valid_ip(observed_exit_ip) else None,
        "checked_at": checked.isoformat(),
        "handshake_at": None,
        "checks": {
            "profile": bool(profile_present),
            "tunnel": bool(tunnel_started),
            "exit_ip": False,
            "handshake": False,
            "server": False,
            "dns": dns_protected,
            "ipv6": ipv6_protected,
            "kill_switch": kill_switch_protected,
        },
        "reasons": [],
    }
    if not profile_present:
        result["state"] = "setup_needed"
        result["reasons"] = ["profile_missing"]
        return result
    if not tunnel_started:
        result["state"] = "disconnected"
        result["reasons"] = ["tunnel_not_observed"]
        return result
    if observed_exit_ip is None and handshake_at is None:
        result["state"] = "checking"
        result["reasons"] = ["external_evidence_pending"]
        return result

    reasons: list[str] = []
    expected_valid = _valid_ip(expected_exit_ip)
    observed_valid = _valid_ip(observed_exit_ip)
    exit_match = bool(expected_valid and observed_valid and observed_exit_ip == expected_exit_ip)
    result["checks"]["exit_ip"] = exit_match
    if not exit_match:
        reasons.append("exit_ip_not_verified")

    handshake = _as_utc(handshake_at)
    if handshake is not None:
        result["handshake_at"] = handshake.isoformat()
        age = checked - handshake
        handshake_fresh = (
            age <= timedelta(seconds=HANDSHAKE_MAX_AGE_SECONDS)
            and age >= -timedelta(seconds=FUTURE_CLOCK_TOLERANCE_SECONDS)
        )
    else:
        handshake_fresh = False
    result["checks"]["handshake"] = handshake_fresh
    if not handshake_fresh:
        reasons.append("handshake_missing_or_stale")

    server_ok = server_health in ACTIVE_SERVER_HEALTH
    result["checks"]["server"] = server_ok
    if not server_ok:
        reasons.append("server_not_available")

    for code, value in (
        ("dns_not_verified", dns_protected),
        ("ipv6_not_verified", ipv6_protected),
        ("kill_switch_not_verified", kill_switch_protected),
    ):
        if value is not True:
            reasons.append(code)

    if not reasons:
        result["state"] = "protected"
        result["protected"] = True
    else:
        result["state"] = "limited"
    result["reasons"] = reasons
    return result
