#!/usr/bin/env python3
"""모바일·PC·상업 운영 원본 증거로 95% 출시 후보 게이트를 계산한다."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from app.platform_evidence import (
    PC_PLATFORMS,
    MOBILE_PLATFORMS,
    PlatformEvidenceError,
    VerifiedPlatformEvidence,
    verify_platform_evidence,
)


SCHEMA = "FreeFlexVPNRelease95EvidenceV1"
OPERATIONS_GATES = (
    "ACCESSIBILITY",
    "PRIVACY_SECURITY",
    "SUPPORT_RECOVERY",
    "PAYMENT",
    "REFUND",
    "LEGAL",
    "MONITORING",
    "LIMITED_RELEASE",
)
WEIGHTS = {
    "MOBILE_CONNECTION": 15,
    "PC_CONNECTION": 15,
    "ACCESSIBILITY": 10,
    "PRIVACY_SECURITY": 10,
    "SUPPORT_RECOVERY": 10,
    "PAYMENT": 10,
    "REFUND": 5,
    "LEGAL": 10,
    "MONITORING": 10,
    "LIMITED_RELEASE": 5,
}
CRITICAL_95 = frozenset(set(WEIGHTS) - {"LIMITED_RELEASE"})
ALLOWED_STATES = frozenset({"pass", "fail", "not_run"})
ALLOWED_KINDS = frozenset({"log", "screenshot", "measurement", "receipt", "document"})
MAX_BUNDLE_BYTES = 500_000
MAX_ARTIFACT_BYTES = 25_000_000
MAX_AGE_DAYS = 30
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_SENSITIVE_KEYS = re.compile(r"(?i)(account|address|device.?id|email|endpoint|ip.?address|password|private.?key|secret|serial|token)")
_SENSITIVE_TEXT = re.compile(
    rb"(?i)(private\s*key|preshared\s*key|access[_ -]?token|authorization\s*:\s*bearer|"
    rb"begin\s+(?:rsa\s+)?private\s+key)"
)
_IPV4_TEXT = re.compile(rb"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")


class Release95EvidenceError(ValueError):
    """95% 출시 후보 증거가 불완전하거나 안전하지 않을 때 발생한다."""


@dataclass(frozen=True)
class VerifiedOperationsEvidence:
    bundle_sha256: str
    verified_at: str
    states: Mapping[str, str]
    artifact_count: int


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise Release95EvidenceError(f"{field}가 필요합니다")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Release95EvidenceError(f"{field}가 ISO-8601 형식이 아닙니다") from exc
    if parsed.tzinfo is None:
        raise Release95EvidenceError(f"{field}에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    return path == parent or parent in path.parents


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_sensitive_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _SENSITIVE_KEYS.fullmatch(str(key).replace("-", "_")):
                raise Release95EvidenceError("운영 증거에 금지된 민감 필드가 있습니다")
            _reject_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_keys(child)


def verify_operations_evidence(
    bundle_path: pathlib.Path | str,
    *,
    project_root: pathlib.Path | str,
    now: datetime | None = None,
) -> VerifiedOperationsEvidence:
    """프로젝트 밖 상업 운영 증거와 원본 지문값을 검증한다."""
    requested = pathlib.Path(bundle_path).expanduser()
    if requested.is_symlink():
        raise Release95EvidenceError("운영 증거 번들은 심볼릭 링크일 수 없습니다")
    source = requested.resolve(strict=True)
    root = pathlib.Path(project_root).resolve(strict=True)
    if _is_within(source, root):
        raise Release95EvidenceError("운영 증거 번들은 프로젝트 밖에 두어야 합니다")
    size = source.stat().st_size
    if not source.is_file() or size <= 0 or size > MAX_BUNDLE_BYTES:
        raise Release95EvidenceError("운영 증거 번들 크기가 허용 범위를 벗어났습니다")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Release95EvidenceError("운영 증거 번들은 UTF-8 JSON이어야 합니다") from exc
    if not isinstance(payload, Mapping):
        raise Release95EvidenceError("운영 증거 번들 최상위 값은 객체여야 합니다")
    _reject_sensitive_keys(payload)
    if payload.get("schema") != SCHEMA:
        raise Release95EvidenceError(f"schema는 {SCHEMA}여야 합니다")
    verified_at = _utc(payload.get("verified_at"), "verified_at")
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if verified_at > clock + timedelta(minutes=5):
        raise Release95EvidenceError("verified_at이 현재보다 5분 넘게 미래입니다")
    if clock - verified_at > timedelta(days=MAX_AGE_DAYS):
        raise Release95EvidenceError(f"운영 증거가 {MAX_AGE_DAYS}일보다 오래됐습니다")
    gates = payload.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != set(OPERATIONS_GATES):
        raise Release95EvidenceError("gates는 상업 운영 게이트 8개를 정확히 포함해야 합니다")
    states = dict(gates)
    if any(state not in ALLOWED_STATES for state in states.values()):
        raise Release95EvidenceError("운영 게이트 상태는 pass/fail/not_run만 허용됩니다")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise Release95EvidenceError("운영 증거 artifacts가 비어 있습니다")
    base = source.parent.resolve()
    covered: set[str] = set()
    seen_ids: set[str] = set()
    seen_paths: set[pathlib.Path] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise Release95EvidenceError("운영 artifact는 객체여야 합니다")
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not _ARTIFACT_ID.fullmatch(artifact_id) or artifact_id in seen_ids:
            raise Release95EvidenceError("운영 artifact_id가 잘못됐거나 중복됐습니다")
        seen_ids.add(artifact_id)
        if artifact.get("kind") not in ALLOWED_KINDS:
            raise Release95EvidenceError(f"{artifact_id}의 kind가 허용되지 않습니다")
        gate_ids = artifact.get("gate_ids")
        if (
            not isinstance(gate_ids, list)
            or not gate_ids
            or any(item not in OPERATIONS_GATES for item in gate_ids)
            or len(set(gate_ids)) != len(gate_ids)
        ):
            raise Release95EvidenceError(f"{artifact_id}의 gate_ids가 올바르지 않습니다")
        if artifact.get("contains_secret") is not False or artifact.get("contains_identifier") is not False:
            raise Release95EvidenceError(f"{artifact_id}의 비밀값·식별값 제거 확인이 필요합니다")
        relative = artifact.get("path")
        if not isinstance(relative, str) or not relative.strip():
            raise Release95EvidenceError(f"{artifact_id}의 path가 필요합니다")
        pure = pathlib.PurePath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise Release95EvidenceError(f"{artifact_id}의 path 경계가 올바르지 않습니다")
        cursor = base
        for part in pure.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise Release95EvidenceError(f"{artifact_id}는 심볼릭 링크일 수 없습니다")
        try:
            target = (base / pathlib.Path(relative)).resolve(strict=True)
        except OSError as exc:
            raise Release95EvidenceError(f"{artifact_id} 파일을 찾을 수 없습니다") from exc
        if not _is_within(target, base) or _is_within(target, root) or not target.is_file() or target in seen_paths:
            raise Release95EvidenceError(f"{artifact_id} 파일 경계 또는 중복이 올바르지 않습니다")
        seen_paths.add(target)
        artifact_size = target.stat().st_size
        expected = artifact.get("sha256")
        if (
            artifact_size <= 0
            or artifact_size > MAX_ARTIFACT_BYTES
            or not isinstance(expected, str)
            or not _SHA256.fullmatch(expected)
            or _sha256(target) != expected
        ):
            raise Release95EvidenceError(f"{artifact_id}의 크기 또는 SHA-256이 올바르지 않습니다")
        if artifact_size <= 5_000_000:
            content = target.read_bytes()
            if _SENSITIVE_TEXT.search(content) or _IPV4_TEXT.search(content):
                raise Release95EvidenceError(f"{artifact_id}에 제거되지 않은 비밀값 또는 네트워크 주소가 있습니다")
        covered.update(gate_ids)
    missing = [gate for gate, state in states.items() if state == "pass" and gate not in covered]
    if missing:
        raise Release95EvidenceError(f"원본 증거가 없는 통과 운영 게이트: {missing}")
    return VerifiedOperationsEvidence(
        bundle_sha256=hashlib.sha256(raw).hexdigest(),
        verified_at=verified_at.isoformat(),
        states=states,
        artifact_count=len(artifacts),
    )


def evaluate_release_95(
    mobile: VerifiedPlatformEvidence,
    pc: VerifiedPlatformEvidence,
    operations: VerifiedOperationsEvidence,
) -> dict[str, Any]:
    """검증 객체만 받아 95점 후보와 100점 운영 가능을 분리한다."""
    if mobile.platform not in MOBILE_PLATFORMS:
        raise Release95EvidenceError("mobile 영수증은 Android 또는 iOS여야 합니다")
    if pc.platform not in PC_PLATFORMS:
        raise Release95EvidenceError("pc 영수증은 데스크톱 운영체제여야 합니다")
    states = {
        "MOBILE_CONNECTION": "pass" if mobile.connection_ready else "fail",
        "PC_CONNECTION": "pass" if pc.connection_ready else "fail",
        **dict(operations.states),
    }
    score = sum(WEIGHTS[gate] for gate, state in states.items() if state == "pass")
    missing_critical = [gate for gate in WEIGHTS if gate in CRITICAL_95 and states[gate] != "pass"]
    blockers = [gate for gate in WEIGHTS if states[gate] != "pass"]
    return {
        "schema": SCHEMA,
        "evidence_gate_score": score,
        "target_95_ready": score >= 95 and not missing_critical,
        "commercial_100_ready": score == 100 and not blockers,
        "states": states,
        "blockers": blockers,
        "missing_critical": missing_critical,
        "evidence_hashes": {
            "mobile": mobile.receipt_sha256,
            "pc": pc.receipt_sha256,
            "operations": operations.bundle_sha256,
        },
    }


def verify_and_evaluate_release_95(
    *,
    mobile_receipt: pathlib.Path | str,
    pc_receipt: pathlib.Path | str,
    operations_bundle: pathlib.Path | str,
    project_root: pathlib.Path | str,
    now: datetime | None = None,
) -> dict[str, Any]:
    try:
        mobile = verify_platform_evidence(mobile_receipt, project_root=project_root, now=now)
        pc = verify_platform_evidence(pc_receipt, project_root=project_root, now=now)
    except PlatformEvidenceError as exc:
        raise Release95EvidenceError(str(exc)) from exc
    operations = verify_operations_evidence(operations_bundle, project_root=project_root, now=now)
    return evaluate_release_95(mobile, pc, operations)
