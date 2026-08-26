"""99% 목표를 실제 외부 증거와 연결하는 최종 준비도 통과 조건."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from app.evidence_contract import EvidenceContractError, evidence_freshness, validate_evidence_record
from app.release_95_gate import Release95EvidenceError, verify_and_evaluate_release_95


SCHEMA = "FreeFlexVPNReadiness99EvidenceV1"
DEVELOPMENT_GATES = ("REGRESSION", "MANIFEST", "SECRET_SCAN", "PUBLIC_BUILD")
AREA_EVIDENCE_REQUIREMENTS = {
    "mobile": frozenset({"android"}),
    "pc": frozenset({"windows"}),
    "commercial": frozenset({"operation", "transaction", "expert"}),
    "development": frozenset({"automatic"}),
}
ALLOWED_STATES = frozenset({"pass", "fail", "not_run"})
ALLOWED_KINDS = frozenset({"log", "screenshot", "measurement", "receipt", "document"})
MAX_BUNDLE_BYTES = 500_000
MAX_ARTIFACT_BYTES = 25_000_000
MAX_AGE_DAYS = 30
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_SENSITIVE_KEY = re.compile(r"(?i)(account|address|device.?id|email|endpoint|ip.?address|password|private.?key|secret|serial|token)")
_SENSITIVE_TEXT = re.compile(rb"(?i)(private\s*key|preshared\s*key|access[_ -]?token|authorization\s*:\s*bearer|begin\s+(?:rsa\s+)?private\s+key)")
_IPV4_TEXT = re.compile(rb"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")


class Readiness99EvidenceError(ValueError):
    """99% 준비도 증거가 불완전하거나 안전하지 않을 때 발생한다."""


@dataclass(frozen=True)
class VerifiedDevelopmentEvidence:
    bundle_sha256: str
    verified_at: str
    states: Mapping[str, str]
    artifact_count: int

    @property
    def ready(self) -> bool:
        return all(state == "pass" for state in self.states.values())


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise Readiness99EvidenceError("verified_at이 필요합니다")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Readiness99EvidenceError("verified_at은 ISO-8601 형식이어야 합니다") from exc
    if parsed.tzinfo is None:
        raise Readiness99EvidenceError("verified_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    return path == parent or parent in path.parents


def _sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_sensitive(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _SENSITIVE_KEY.fullmatch(str(key).replace("-", "_")):
                raise Readiness99EvidenceError("개발 증거에 금지된 민감 필드가 있습니다")
            _reject_sensitive(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive(child)


def verify_development_evidence(bundle_path: pathlib.Path | str, *, project_root: pathlib.Path | str, now: datetime | None = None) -> VerifiedDevelopmentEvidence:
    """프로젝트 밖의 비식별 검사 원본으로 개발 완료를 판정한다."""
    requested = pathlib.Path(bundle_path).expanduser()
    if requested.is_symlink():
        raise Readiness99EvidenceError("개발 증거 번들은 심볼릭 링크일 수 없습니다")
    source = requested.resolve(strict=True)
    root = pathlib.Path(project_root).resolve(strict=True)
    if _within(source, root) or not source.is_file() or not 0 < source.stat().st_size <= MAX_BUNDLE_BYTES:
        raise Readiness99EvidenceError("개발 증거는 프로젝트 밖의 허용 크기 파일이어야 합니다")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Readiness99EvidenceError("개발 증거는 UTF-8 JSON이어야 합니다") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise Readiness99EvidenceError(f"schema는 {SCHEMA}여야 합니다")
    _reject_sensitive(payload)
    captured = _utc(payload.get("verified_at"))
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if captured > clock + timedelta(minutes=5) or clock - captured > timedelta(days=MAX_AGE_DAYS):
        raise Readiness99EvidenceError("개발 증거 시각이 허용 범위를 벗어났습니다")
    gates = payload.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != set(DEVELOPMENT_GATES) or any(state not in ALLOWED_STATES for state in gates.values()):
        raise Readiness99EvidenceError("개발 게이트 4개의 상태가 올바르지 않습니다")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise Readiness99EvidenceError("개발 증거 artifacts가 비어 있습니다")
    base, seen_ids, seen_paths, covered = source.parent.resolve(), set(), set(), set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise Readiness99EvidenceError("개발 artifact는 객체여야 합니다")
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not _ARTIFACT_ID.fullmatch(artifact_id) or artifact_id in seen_ids:
            raise Readiness99EvidenceError("개발 artifact_id가 잘못됐거나 중복됐습니다")
        seen_ids.add(artifact_id)
        gate_ids = artifact.get("gate_ids")
        if artifact.get("kind") not in ALLOWED_KINDS or not isinstance(gate_ids, list) or not gate_ids or any(item not in DEVELOPMENT_GATES for item in gate_ids):
            raise Readiness99EvidenceError(f"{artifact_id}의 종류 또는 gate_ids가 올바르지 않습니다")
        if artifact.get("contains_secret") is not False or artifact.get("contains_identifier") is not False:
            raise Readiness99EvidenceError(f"{artifact_id}의 비밀값·식별값 제거 확인이 필요합니다")
        relative = artifact.get("path")
        pure = pathlib.PurePath(relative) if isinstance(relative, str) else None
        if not pure or pure.is_absolute() or ".." in pure.parts:
            raise Readiness99EvidenceError(f"{artifact_id}의 path 경계가 올바르지 않습니다")
        target = (base / pathlib.Path(relative)).resolve(strict=True)
        if not _within(target, base) or _within(target, root) or not target.is_file() or target in seen_paths or not 0 < target.stat().st_size <= MAX_ARTIFACT_BYTES:
            raise Readiness99EvidenceError(f"{artifact_id}의 파일 경계 또는 크기가 올바르지 않습니다")
        seen_paths.add(target)
        if not isinstance(artifact.get("sha256"), str) or not _SHA256.fullmatch(artifact["sha256"]) or _sha(target) != artifact["sha256"]:
            raise Readiness99EvidenceError(f"{artifact_id}의 SHA-256이 일치하지 않습니다")
        if target.stat().st_size <= 5_000_000 and (_SENSITIVE_TEXT.search(target.read_bytes()) or _IPV4_TEXT.search(target.read_bytes())):
            raise Readiness99EvidenceError(f"{artifact_id}에 제거되지 않은 비밀값 또는 네트워크 주소가 있습니다")
        covered.update(gate_ids)
    missing = [gate for gate, state in gates.items() if state == "pass" and gate not in covered]
    if missing:
        raise Readiness99EvidenceError(f"원본 증거가 없는 통과 개발 게이트: {missing}")
    return VerifiedDevelopmentEvidence(_sha(source), captured.isoformat(), dict(gates), len(artifacts))


def _verify_evidence_basis(
    evidence_records: Mapping[str, Any] | None, *, now: datetime
) -> tuple[dict[str, bool], dict[str, tuple[str, ...]], dict[str, str]]:
    """영역별 직접 출처·통과·신선도를 확인한다. 누락은 점수 0이지 예외가 아니다."""
    if evidence_records is None:
        return ({area: False for area in AREA_EVIDENCE_REQUIREMENTS}, {area: () for area in AREA_EVIDENCE_REQUIREMENTS}, {area: "missing" for area in AREA_EVIDENCE_REQUIREMENTS})
    if not isinstance(evidence_records, Mapping) or set(evidence_records) - set(AREA_EVIDENCE_REQUIREMENTS):
        raise Readiness99EvidenceError("증거 기준표의 영역이 올바르지 않습니다")
    eligible: dict[str, bool] = {}
    ids: dict[str, tuple[str, ...]] = {}
    freshness: dict[str, str] = {}
    for area, required_sources in AREA_EVIDENCE_REQUIREMENTS.items():
        raw_records = evidence_records.get(area, [])
        if not isinstance(raw_records, list):
            raise Readiness99EvidenceError(f"{area} 증거 목록은 배열이어야 합니다")
        try:
            verified = [validate_evidence_record(item, now=now) for item in raw_records]
        except EvidenceContractError as exc:
            raise Readiness99EvidenceError(f"{area} 공통 증거 계약 오류: {exc}") from exc
        ids[area] = tuple(record.evidence_id for record in verified)
        current = [record for record in verified if record.result == "pass" and evidence_freshness(record, now=now) == "fresh"]
        eligible[area] = required_sources <= {record.source_class for record in current}
        freshness[area] = "fresh" if eligible[area] else ("stale_or_missing" if verified else "missing")
    return eligible, ids, freshness


def verify_and_evaluate_readiness_99(*, mobile_receipt: pathlib.Path | str, pc_receipt: pathlib.Path | str, operations_bundle: pathlib.Path | str, development_bundle: pathlib.Path | str, project_root: pathlib.Path | str, evidence_records: Mapping[str, Any] | None = None, now: datetime | None = None) -> dict[str, Any]:
    """모바일·PC·상용화·개발이 최신의 직접 출처 증거로 99%를 넘는지 반환한다."""
    try:
        release = verify_and_evaluate_release_95(mobile_receipt=mobile_receipt, pc_receipt=pc_receipt, operations_bundle=operations_bundle, project_root=project_root, now=now)
    except Release95EvidenceError as exc:
        raise Readiness99EvidenceError(str(exc)) from exc
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    development = verify_development_evidence(development_bundle, project_root=project_root, now=clock)
    basis_ready, basis_ids, basis_freshness = _verify_evidence_basis(evidence_records, now=clock)
    areas = {
        "mobile": 100 if release["states"]["MOBILE_CONNECTION"] == "pass" and basis_ready["mobile"] else 0,
        "pc": 100 if release["states"]["PC_CONNECTION"] == "pass" and basis_ready["pc"] else 0,
        "commercial": 100 if release["commercial_100_ready"] and basis_ready["commercial"] else 0,
        "development": 100 if development.ready and basis_ready["development"] else 0,
    }
    blockers = [name for name, score in areas.items() if score < 99]
    return {
        "schema": SCHEMA,
        "computed_at": clock.isoformat(),
        "areas": areas,
        "target_99_ready": not blockers,
        "blockers": blockers,
        "release_evidence_gate_score": release["evidence_gate_score"],
        "development_states": dict(development.states),
        "evidence_basis": {area: {"required_sources": sorted(AREA_EVIDENCE_REQUIREMENTS[area]), "evidence_ids": list(basis_ids[area]), "freshness": basis_freshness[area]} for area in AREA_EVIDENCE_REQUIREMENTS},
        "evidence_hashes": {**release["evidence_hashes"], "development": development.bundle_sha256},
    }
