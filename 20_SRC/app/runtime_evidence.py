#!/usr/bin/env python3
"""프로젝트 밖 T1~T10 증거 번들의 파일 무결성을 검증한다.

JSON의 참/거짓 값만으로 실제 증거가 되지 않도록 각 테스트를 원본 파일의
SHA-256, 수집 시각, 동일 후보 ID에 결속한다. 원본 경로와 파일 내용은 결과에
반환하지 않아 저장소 산출물에 운영 주소나 사용자 자료가 복사되지 않게 한다.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from app.runtime_acceptance import TEST_IDS


SCHEMA = "FreeFlexVPNRuntimeEvidenceBundleV2"
MAX_BUNDLE_BYTES = 1_000_000
MAX_ARTIFACT_BYTES = 50_000_000
MAX_ARTIFACT_AGE_DAYS = 60
ALLOWED_KINDS = frozenset({"log", "screenshot", "pcap_summary", "receipt", "consent_record", "measurement"})
REQUIRED_KINDS_BY_TEST = {
    "T1": frozenset({"log", "screenshot"}),
    "T2": frozenset({"measurement", "screenshot"}),
    "T3": frozenset({"pcap_summary", "measurement"}),
    "T4": frozenset({"measurement"}),
    "T5": frozenset({"log", "screenshot"}),
    "T6": frozenset({"log", "screenshot"}),
    "T7": frozenset({"log", "screenshot"}),
    "T8": frozenset({"pcap_summary", "measurement"}),
    "T9": frozenset({"log", "screenshot"}),
    "T10": frozenset({"consent_record"}),
}
_ARTIFACT_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_CANDIDATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,99}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceBundleError(ValueError):
    """증거 번들이 출시 판정에 안전하지 않을 때 발생한다."""


@dataclass(frozen=True)
class VerifiedArtifacts:
    candidate_id: str
    bundle_sha256: str
    covered_tests: tuple[str, ...]
    artifacts: tuple[Mapping[str, Any], ...]

    @property
    def complete(self) -> bool:
        return self.covered_tests == TEST_IDS


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceBundleError(f"{field}가 필요합니다")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceBundleError(f"{field}가 ISO-8601 형식이 아닙니다") from exc
    if parsed.tzinfo is None:
        raise EvidenceBundleError(f"{field}에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    return path == parent or parent in path.parents


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_bundle(path: pathlib.Path) -> tuple[bytes, Mapping[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceBundleError("번들은 일반 파일이어야 하며 심볼릭 링크를 허용하지 않습니다")
    size = path.stat().st_size
    if size <= 0 or size > MAX_BUNDLE_BYTES:
        raise EvidenceBundleError("번들 크기가 허용 범위를 벗어났습니다")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceBundleError("번들은 UTF-8 JSON이어야 합니다") from exc
    if not isinstance(payload, Mapping):
        raise EvidenceBundleError("번들 최상위 값은 객체여야 합니다")
    return raw, payload


def verify_evidence_bundle(
    bundle_path: pathlib.Path | str,
    *,
    project_root: pathlib.Path | str,
    now: datetime | None = None,
) -> tuple[dict[str, Any], VerifiedArtifacts]:
    """외부 번들과 원본 파일을 검증하고 경로가 제거된 증명만 반환한다."""
    requested = pathlib.Path(bundle_path).expanduser()
    if requested.is_symlink():
        raise EvidenceBundleError("번들은 심볼릭 링크일 수 없습니다")
    source = requested.resolve(strict=True)
    root = pathlib.Path(project_root).resolve(strict=True)
    if _is_within(source, root):
        raise EvidenceBundleError("실환경 증거 번들은 프로젝트 밖에 두어야 합니다")

    raw, payload = _read_bundle(source)
    if payload.get("schema") != SCHEMA:
        raise EvidenceBundleError(f"schema는 {SCHEMA}여야 합니다")
    candidate_id = payload.get("candidate_id")
    if not isinstance(candidate_id, str) or not _CANDIDATE_ID.fullmatch(candidate_id):
        raise EvidenceBundleError("candidate_id 형식이 올바르지 않습니다")
    run_at = _utc(payload.get("run_at"), "run_at")
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if run_at > clock + timedelta(minutes=5):
        raise EvidenceBundleError("run_at이 현재보다 5분 넘게 미래입니다")

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping):
        raise EvidenceBundleError("evidence 객체가 필요합니다")
    if evidence.get("candidate_id") != candidate_id:
        raise EvidenceBundleError("번들과 evidence의 candidate_id가 다릅니다")
    if evidence.get("run_at") != payload.get("run_at"):
        raise EvidenceBundleError("번들과 evidence의 run_at이 다릅니다")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceBundleError("artifacts가 비어 있습니다")
    base = source.parent.resolve()
    seen_ids: set[str] = set()
    seen_paths: set[pathlib.Path] = set()
    seen_hashes: set[str] = set()
    covered: set[str] = set()
    sanitized: list[Mapping[str, Any]] = []

    for index, artifact in enumerate(artifacts):
        field = f"artifacts[{index}]"
        if not isinstance(artifact, Mapping):
            raise EvidenceBundleError(f"{field}는 객체여야 합니다")
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not _ARTIFACT_ID.fullmatch(artifact_id):
            raise EvidenceBundleError(f"{field}.artifact_id 형식이 올바르지 않습니다")
        if artifact_id in seen_ids:
            raise EvidenceBundleError(f"중복 artifact_id: {artifact_id}")
        seen_ids.add(artifact_id)
        if artifact.get("candidate_id") != candidate_id:
            raise EvidenceBundleError(f"{artifact_id}의 candidate_id가 다릅니다")

        kind = artifact.get("kind")
        if kind not in ALLOWED_KINDS:
            raise EvidenceBundleError(f"{artifact_id}의 kind가 허용되지 않습니다")
        tests = artifact.get("test_ids")
        if not isinstance(tests, list) or not tests or any(item not in TEST_IDS for item in tests):
            raise EvidenceBundleError(f"{artifact_id}의 test_ids가 올바르지 않습니다")
        if len(set(tests)) != len(tests):
            raise EvidenceBundleError(f"{artifact_id}의 test_ids가 중복됩니다")
        incompatible = [test_id for test_id in tests if kind not in REQUIRED_KINDS_BY_TEST[test_id]]
        if incompatible:
            raise EvidenceBundleError(f"{artifact_id}의 kind가 {incompatible} 증거에 맞지 않습니다")
        captured_at = _utc(artifact.get("captured_at"), f"{artifact_id}.captured_at")
        if captured_at > run_at + timedelta(minutes=5):
            raise EvidenceBundleError(f"{artifact_id}가 판정 시각 뒤에 수집됐습니다")
        if run_at - captured_at > timedelta(days=MAX_ARTIFACT_AGE_DAYS):
            raise EvidenceBundleError(f"{artifact_id}가 {MAX_ARTIFACT_AGE_DAYS}일보다 오래됐습니다")
        if artifact.get("contains_secret") is not False:
            raise EvidenceBundleError(f"{artifact_id}의 비밀값 제거 확인이 필요합니다")

        relative = artifact.get("path")
        if not isinstance(relative, str) or not relative.strip():
            raise EvidenceBundleError(f"{artifact_id}의 path가 필요합니다")
        relative_path = pathlib.PurePath(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise EvidenceBundleError(f"{artifact_id}의 path는 번들 폴더 안 상대경로여야 합니다")
        target_input = base / pathlib.Path(relative)
        cursor = base
        path_has_symlink = False
        for part in relative_path.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                path_has_symlink = True
                break
        if path_has_symlink:
            raise EvidenceBundleError(f"{artifact_id}는 심볼릭 링크일 수 없습니다")
        try:
            target = target_input.resolve(strict=True)
        except OSError as exc:
            raise EvidenceBundleError(f"{artifact_id} 파일을 찾을 수 없습니다") from exc
        if not _is_within(target, base) or _is_within(target, root) or not target.is_file():
            raise EvidenceBundleError(f"{artifact_id} 파일 경계가 올바르지 않습니다")
        if target in seen_paths:
            raise EvidenceBundleError(f"같은 원본 경로가 중복 등록됐습니다: {artifact_id}")
        seen_paths.add(target)
        size = target.stat().st_size
        if size <= 0 or size > MAX_ARTIFACT_BYTES:
            raise EvidenceBundleError(f"{artifact_id} 파일 크기가 허용 범위를 벗어났습니다")
        expected_hash = artifact.get("sha256")
        if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
            raise EvidenceBundleError(f"{artifact_id}의 sha256 형식이 올바르지 않습니다")
        actual_hash = _sha256(target)
        if actual_hash != expected_hash:
            raise EvidenceBundleError(f"{artifact_id}의 SHA-256이 일치하지 않습니다")
        if actual_hash in seen_hashes:
            raise EvidenceBundleError(f"동일 내용의 원본이 중복 등록됐습니다: {artifact_id}")
        seen_hashes.add(actual_hash)

        covered.update(tests)
        sanitized.append({
            "artifact_id": artifact_id,
            "kind": kind,
            "test_ids": tuple(tests),
            "captured_at": captured_at.isoformat(),
            "sha256": actual_hash,
            "size_bytes": size,
        })

    ordered_coverage = tuple(item for item in TEST_IDS if item in covered)
    missing = [item for item in TEST_IDS if item not in covered]
    if missing:
        raise EvidenceBundleError(f"원본 증거가 없는 테스트: {missing}")
    verified = VerifiedArtifacts(
        candidate_id=candidate_id,
        bundle_sha256=hashlib.sha256(raw).hexdigest(),
        covered_tests=ordered_coverage,
        artifacts=tuple(sanitized),
    )
    return dict(evidence), verified
