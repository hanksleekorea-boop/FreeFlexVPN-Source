#!/usr/bin/env python3
"""공통 증거 레코드의 출처·신선도·비식별 경계를 강제한다.

이 모듈은 화면의 자기신고, 자동 검사, 실제 기기 검사, 거래 영수증을 같은
형태로 표현하되 서로를 대신하지 못하게 하는 작은 공통 계약이다. 원본 파일,
계정·기기 식별값, 주소와 비밀값은 이 계약에 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Iterable, Mapping


SCHEMA = "FreeFlexVPNEvidenceContractV1"
ALLOWED_SUBJECT_SCOPES = frozenset({"session", "device", "account", "node", "release"})
ALLOWED_SOURCE_CLASSES = frozenset({
    "automatic", "browser", "android", "windows", "iphone", "transaction", "operation", "expert", "persona",
})
ALLOWED_RESULTS = frozenset({"pass", "fail", "partial", "unknown"})
ALLOWED_REDACTIONS = frozenset({"account", "identifier", "ip", "key", "network_address", "secret"})
REQUIRED_SOURCE_BY_USE = {
    "android_protection": frozenset({"android"}),
    "windows_protection": frozenset({"windows"}),
    "iphone_protection": frozenset({"iphone"}),
    "payment_transaction": frozenset({"transaction"}),
    "operational_review": frozenset({"operation"}),
    "external_security_review": frozenset({"expert"}),
}

_EVIDENCE_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_SENSITIVE_KEYS = frozenset({
    "account", "address", "device_id", "email", "endpoint", "ip", "ip_address",
    "private_key", "preshared_key", "public_key", "serial", "token", "cookie", "password",
})


class EvidenceContractError(ValueError):
    """공통 증거 계약이 충족되지 않을 때 발생한다."""


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    subject_scope: str
    observed_at: datetime
    expires_at: datetime | None
    source_class: str
    result: str
    redaction: tuple[str, ...]
    version: Mapping[str, str | None]

    def public_summary(self) -> dict[str, Any]:
        """증거 내용·원본 위치 없이 UI와 보고서에 안전한 요약을 반환한다."""
        return {
            "schema": SCHEMA,
            "evidence_id": self.evidence_id,
            "subject_scope": self.subject_scope,
            "observed_at": self.observed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "source_class": self.source_class,
            "result": self.result,
            "redaction": list(self.redaction),
            "version": dict(self.version),
        }


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceContractError(f"{field}가 필요합니다")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceContractError(f"{field}가 ISO-8601 형식이 아닙니다") from exc
    if parsed.tzinfo is None:
        raise EvidenceContractError(f"{field}에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _reject_sensitive_keys(value: Any, prefix: str = "evidence") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _SENSITIVE_KEYS or normalized.endswith(("_token", "_secret", "_password")):
                raise EvidenceContractError(f"{prefix}에 금지된 민감 필드가 있습니다")
            _reject_sensitive_keys(child, f"{prefix}.{normalized}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_keys(child, f"{prefix}[{index}]")


def validate_evidence_record(value: Mapping[str, Any], *, now: datetime | None = None) -> EvidenceRecord:
    """비식별 공통 증거 한 건을 엄격히 검증하고 정규화한다."""
    if not isinstance(value, Mapping):
        raise EvidenceContractError("증거 레코드는 객체여야 합니다")
    _reject_sensitive_keys(value)
    allowed = {"schema", "evidence_id", "subject_scope", "observed_at", "expires_at", "source_class", "result", "redaction", "version"}
    unexpected = set(value) - allowed
    if unexpected:
        raise EvidenceContractError("정의되지 않은 증거 필드를 허용하지 않습니다")
    if value.get("schema") != SCHEMA:
        raise EvidenceContractError(f"schema는 {SCHEMA}여야 합니다")
    evidence_id = value.get("evidence_id")
    if not isinstance(evidence_id, str) or not _EVIDENCE_ID.fullmatch(evidence_id):
        raise EvidenceContractError("evidence_id 형식이 올바르지 않습니다")
    subject_scope = value.get("subject_scope")
    if subject_scope not in ALLOWED_SUBJECT_SCOPES:
        raise EvidenceContractError("subject_scope가 허용되지 않습니다")
    source_class = value.get("source_class")
    if source_class not in ALLOWED_SOURCE_CLASSES:
        raise EvidenceContractError("source_class가 허용되지 않습니다")
    result = value.get("result")
    if result not in ALLOWED_RESULTS:
        raise EvidenceContractError("result가 허용되지 않습니다")
    observed_at = _utc(value.get("observed_at"), "observed_at")
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if observed_at > clock + timedelta(minutes=5):
        raise EvidenceContractError("observed_at이 현재보다 5분 넘게 미래입니다")
    raw_expiry = value.get("expires_at")
    expires_at = None if raw_expiry is None else _utc(raw_expiry, "expires_at")
    if expires_at is not None and expires_at < observed_at:
        raise EvidenceContractError("expires_at은 observed_at보다 빠를 수 없습니다")
    redaction = value.get("redaction")
    if not isinstance(redaction, list) or not redaction or any(item not in ALLOWED_REDACTIONS for item in redaction):
        raise EvidenceContractError("redaction은 허용된 비식별 처리 항목을 하나 이상 포함해야 합니다")
    if len(set(redaction)) != len(redaction):
        raise EvidenceContractError("redaction 항목이 중복됩니다")
    version = value.get("version")
    if not isinstance(version, Mapping) or not version:
        raise EvidenceContractError("version 객체가 필요합니다")
    normalized_version: dict[str, str | None] = {}
    for key, item in version.items():
        if not isinstance(key, str) or not key or key.lower() in _SENSITIVE_KEYS:
            raise EvidenceContractError("version 키가 올바르지 않습니다")
        if item is not None and (not isinstance(item, str) or not item.strip()):
            raise EvidenceContractError("version 값은 비어 있지 않은 문자열 또는 null이어야 합니다")
        normalized_version[key] = item
    return EvidenceRecord(
        evidence_id=evidence_id,
        subject_scope=subject_scope,
        observed_at=observed_at,
        expires_at=expires_at,
        source_class=source_class,
        result=result,
        redaction=tuple(redaction),
        version=normalized_version,
    )


def evidence_freshness(record: EvidenceRecord, *, now: datetime | None = None, max_age_seconds: int | None = None) -> str:
    """`fresh`·`stale`·`unknown`만 반환한다. 만료 또는 보존기간 없는 증거는 성공을 주장하지 않는다."""
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if record.expires_at is not None:
        return "fresh" if clock <= record.expires_at else "stale"
    if max_age_seconds is None:
        return "unknown"
    if not isinstance(max_age_seconds, int) or max_age_seconds <= 0:
        raise EvidenceContractError("max_age_seconds는 양의 정수여야 합니다")
    return "fresh" if clock <= record.observed_at + timedelta(seconds=max_age_seconds) else "stale"


def require_source_for_use(record: EvidenceRecord, use: str) -> None:
    """자동/브라우저/페르소나 증거를 실기기·거래·전문가 판정에 승격하지 못하게 한다."""
    allowed_sources = REQUIRED_SOURCE_BY_USE.get(use)
    if allowed_sources is None:
        raise EvidenceContractError("알 수 없는 증거 사용 목적입니다")
    if record.source_class not in allowed_sources:
        raise EvidenceContractError(f"{use}에는 {', '.join(sorted(allowed_sources))} 출처 증거가 필요합니다")


def require_all_sources(records: Iterable[EvidenceRecord], use: str) -> None:
    """여러 증거 중 적어도 하나가 목적에 맞는 직접 출처인지 확인한다."""
    allowed_sources = REQUIRED_SOURCE_BY_USE.get(use)
    if allowed_sources is None:
        raise EvidenceContractError("알 수 없는 증거 사용 목적입니다")
    if not any(record.source_class in allowed_sources for record in records):
        raise EvidenceContractError(f"{use}에는 직접 출처 증거가 필요합니다")
