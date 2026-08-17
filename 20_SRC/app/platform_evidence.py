#!/usr/bin/env python3
"""실제 모바일·PC VPN 검사의 비식별 외부 증거 영수증을 검증한다.

참/거짓 자기보고만으로 상용화 점수를 올리지 않는다. 영수증과 원본 증거는
프로젝트 밖에 두고, 각 통과 관찰값을 SHA-256으로 결속된 파일로 입증한다.
반환값에는 원본 경로·기기 식별값·네트워크 주소를 포함하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


SCHEMA = "FreeFlexVPNPlatformEvidenceV1"
OBSERVATION_IDS = (
    "CLIENT_INSTALLED",
    "PROFILE_IMPORTED",
    "TUNNEL_CONNECTED",
    "DNS_OK",
    "WEB_OK",
    "HANDSHAKE_OK",
    "DISCONNECT_RECOVERY",
    "FINAL_SAFE",
)
PLATFORMS = frozenset({"android", "ios", "windows", "macos", "linux"})
MOBILE_PLATFORMS = frozenset({"android", "ios"})
PC_PLATFORMS = PLATFORMS - MOBILE_PLATFORMS
ALLOWED_STATES = frozenset({"pass", "fail", "not_run"})
ALLOWED_KINDS = frozenset({"log", "screenshot", "measurement", "receipt"})
MAX_RECEIPT_BYTES = 500_000
MAX_ARTIFACT_BYTES = 25_000_000
MAX_AGE_DAYS = 14
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_SENSITIVE_KEYS = frozenset({
    "account", "address", "device_id", "email", "endpoint", "ip", "ip_address",
    "private_key", "preshared_key", "public_key", "serial", "token", "user_agent",
})
_SECRET_TEXT = re.compile(
    rb"(?i)(private\s*key|preshared\s*key|access[_ -]?token|authorization\s*:\s*bearer|"
    rb"begin\s+(?:rsa\s+)?private\s+key)"
)
_IPV4_TEXT = re.compile(rb"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")


class PlatformEvidenceError(ValueError):
    """실제 플랫폼 증거가 안전하지 않거나 검증되지 않았을 때 발생한다."""


@dataclass(frozen=True)
class VerifiedPlatformEvidence:
    platform: str
    receipt_sha256: str
    captured_at: str
    states: Mapping[str, str]
    artifact_count: int

    @property
    def category(self) -> str:
        return "mobile" if self.platform in MOBILE_PLATFORMS else "pc"

    @property
    def connection_ready(self) -> bool:
        return all(self.states[item] == "pass" for item in OBSERVATION_IDS)

    @property
    def partial(self) -> bool:
        return any(value == "pass" for value in self.states.values()) and not self.connection_ready


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PlatformEvidenceError(f"{field}가 필요합니다")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PlatformEvidenceError(f"{field}가 ISO-8601 형식이 아닙니다") from exc
    if parsed.tzinfo is None:
        raise PlatformEvidenceError(f"{field}에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    return path == parent or parent in path.parents


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_sensitive_keys(value: Any, prefix: str = "receipt") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            attestation_fields = {"contains_secret", "contains_identifier"}
            if normalized not in attestation_fields and (
                normalized in _SENSITIVE_KEYS or normalized.endswith(("_token", "_secret", "_password"))
            ):
                raise PlatformEvidenceError(f"{prefix}에 금지된 민감 필드가 있습니다")
            _reject_sensitive_keys(child, f"{prefix}.{normalized}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_keys(child, f"{prefix}[{index}]")


def _resolve_artifact(base: pathlib.Path, relative: Any, artifact_id: str) -> pathlib.Path:
    if not isinstance(relative, str) or not relative.strip():
        raise PlatformEvidenceError(f"{artifact_id}의 path가 필요합니다")
    pure = pathlib.PurePath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise PlatformEvidenceError(f"{artifact_id}의 path는 영수증 폴더 안 상대경로여야 합니다")
    cursor = base
    for part in pure.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PlatformEvidenceError(f"{artifact_id}는 심볼릭 링크일 수 없습니다")
    try:
        target = (base / pathlib.Path(relative)).resolve(strict=True)
    except OSError as exc:
        raise PlatformEvidenceError(f"{artifact_id} 파일을 찾을 수 없습니다") from exc
    if not _is_within(target, base) or not target.is_file():
        raise PlatformEvidenceError(f"{artifact_id} 파일 경계가 올바르지 않습니다")
    return target


def verify_platform_evidence(
    receipt_path: pathlib.Path | str,
    *,
    project_root: pathlib.Path | str,
    now: datetime | None = None,
) -> VerifiedPlatformEvidence:
    """외부 영수증을 검증하고 식별정보가 제거된 판정만 반환한다."""
    requested = pathlib.Path(receipt_path).expanduser()
    if requested.is_symlink():
        raise PlatformEvidenceError("영수증은 심볼릭 링크일 수 없습니다")
    source = requested.resolve(strict=True)
    root = pathlib.Path(project_root).resolve(strict=True)
    if _is_within(source, root):
        raise PlatformEvidenceError("실제 기기 영수증은 프로젝트 밖에 두어야 합니다")
    if not source.is_file() or source.stat().st_size <= 0 or source.stat().st_size > MAX_RECEIPT_BYTES:
        raise PlatformEvidenceError("영수증 파일 크기가 허용 범위를 벗어났습니다")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlatformEvidenceError("영수증은 UTF-8 JSON이어야 합니다") from exc
    if not isinstance(payload, Mapping):
        raise PlatformEvidenceError("영수증 최상위 값은 객체여야 합니다")
    _reject_sensitive_keys(payload)
    if payload.get("schema") != SCHEMA:
        raise PlatformEvidenceError(f"schema는 {SCHEMA}여야 합니다")
    platform = payload.get("platform")
    if platform not in PLATFORMS:
        raise PlatformEvidenceError("platform이 허용되지 않습니다")
    captured = _utc(payload.get("captured_at"), "captured_at")
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if captured > clock + timedelta(minutes=5):
        raise PlatformEvidenceError("captured_at이 현재보다 5분 넘게 미래입니다")
    if clock - captured > timedelta(days=MAX_AGE_DAYS):
        raise PlatformEvidenceError(f"영수증이 {MAX_AGE_DAYS}일보다 오래됐습니다")

    observations = payload.get("observations")
    if not isinstance(observations, Mapping) or set(observations) != set(OBSERVATION_IDS):
        raise PlatformEvidenceError("observations는 필수 관찰값 8개를 정확히 포함해야 합니다")
    states: dict[str, str] = {}
    for observation_id in OBSERVATION_IDS:
        state = observations.get(observation_id)
        if state not in ALLOWED_STATES:
            raise PlatformEvidenceError(f"{observation_id} 상태가 올바르지 않습니다")
        states[observation_id] = state

    if states["PROFILE_IMPORTED"] == "pass" and states["CLIENT_INSTALLED"] != "pass":
        raise PlatformEvidenceError("프로필 통과에는 공식 클라이언트 설치 통과가 필요합니다")
    if states["TUNNEL_CONNECTED"] == "pass" and states["PROFILE_IMPORTED"] != "pass":
        raise PlatformEvidenceError("터널 통과에는 프로필 가져오기 통과가 필요합니다")
    for item in ("DNS_OK", "WEB_OK", "HANDSHAKE_OK", "DISCONNECT_RECOVERY"):
        if states[item] == "pass" and states["TUNNEL_CONNECTED"] != "pass":
            raise PlatformEvidenceError(f"{item} 통과에는 실제 터널 연결 통과가 필요합니다")
    if states["FINAL_SAFE"] == "pass" and states["DISCONNECT_RECOVERY"] != "pass":
        raise PlatformEvidenceError("최종 안전 상태 통과에는 연결 해제·복구 통과가 필요합니다")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise PlatformEvidenceError("artifacts가 비어 있습니다")
    base = source.parent.resolve()
    seen_ids: set[str] = set()
    seen_paths: set[pathlib.Path] = set()
    covered: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise PlatformEvidenceError(f"artifacts[{index}]는 객체여야 합니다")
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not _ARTIFACT_ID.fullmatch(artifact_id):
            raise PlatformEvidenceError("artifact_id 형식이 올바르지 않습니다")
        if artifact_id in seen_ids:
            raise PlatformEvidenceError(f"중복 artifact_id: {artifact_id}")
        seen_ids.add(artifact_id)
        if artifact.get("kind") not in ALLOWED_KINDS:
            raise PlatformEvidenceError(f"{artifact_id}의 kind가 허용되지 않습니다")
        observation_ids = artifact.get("observation_ids")
        if (
            not isinstance(observation_ids, list)
            or not observation_ids
            or any(item not in OBSERVATION_IDS for item in observation_ids)
            or len(set(observation_ids)) != len(observation_ids)
        ):
            raise PlatformEvidenceError(f"{artifact_id}의 observation_ids가 올바르지 않습니다")
        if artifact.get("contains_secret") is not False or artifact.get("contains_identifier") is not False:
            raise PlatformEvidenceError(f"{artifact_id}의 비밀값·식별값 제거 확인이 필요합니다")
        target = _resolve_artifact(base, artifact.get("path"), artifact_id)
        if _is_within(target, root):
            raise PlatformEvidenceError(f"{artifact_id}는 프로젝트 밖 원본이어야 합니다")
        if target in seen_paths:
            raise PlatformEvidenceError(f"같은 원본 경로가 중복 등록됐습니다: {artifact_id}")
        seen_paths.add(target)
        size = target.stat().st_size
        if size <= 0 or size > MAX_ARTIFACT_BYTES:
            raise PlatformEvidenceError(f"{artifact_id} 파일 크기가 허용 범위를 벗어났습니다")
        expected = artifact.get("sha256")
        if not isinstance(expected, str) or not _SHA256.fullmatch(expected) or _sha256(target) != expected:
            raise PlatformEvidenceError(f"{artifact_id}의 SHA-256이 일치하지 않습니다")
        if size <= 5_000_000:
            content = target.read_bytes()
            if _SECRET_TEXT.search(content) or _IPV4_TEXT.search(content):
                raise PlatformEvidenceError(f"{artifact_id} 원본에 제거되지 않은 비밀값 또는 네트워크 주소가 있습니다")
        covered.update(observation_ids)

    missing_proof = [item for item, state in states.items() if state == "pass" and item not in covered]
    if missing_proof:
        raise PlatformEvidenceError(f"원본 증거가 없는 통과 관찰값: {missing_proof}")
    return VerifiedPlatformEvidence(
        platform=platform,
        receipt_sha256=hashlib.sha256(raw).hexdigest(),
        captured_at=captured.isoformat(),
        states=states,
        artifact_count=len(artifacts),
    )


def summarize_platform_evidence(verified: VerifiedPlatformEvidence) -> dict[str, Any]:
    """경로·기기 식별값 없는 UI/자동화용 요약을 반환한다."""
    return {
        "schema": SCHEMA,
        "category": verified.category,
        "platform": verified.platform,
        "captured_at": verified.captured_at,
        "receipt_sha256": verified.receipt_sha256,
        "artifact_count": verified.artifact_count,
        "observations": dict(verified.states),
        "connection_ready": verified.connection_ready,
        "partial": verified.partial,
    }
