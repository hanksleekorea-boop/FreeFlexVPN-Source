#!/usr/bin/env python3
"""설정 전용 증거와 실제 서버 실행을 같은 후보·같은 설정으로 결속한다."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any, Mapping


MAX_EVIDENCE_BYTES = 1_000_000
CANDIDATE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{5,79}")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_preflight_evidence(
    path: pathlib.Path,
    *,
    schema: str,
    candidate_id: str,
    config_sha256: str,
    extra_required: Mapping[str, Any] | None = None,
) -> str:
    """증거 파일을 읽되 경로·크기·경계·후보·설정 불일치를 모두 거부한다."""
    if not path.is_absolute():
        raise ValueError("설정검사 증거는 절대 경로여야 합니다")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError("설정검사 증거 파일을 확인할 수 없습니다") from exc
    if size <= 0 or size > MAX_EVIDENCE_BYTES:
        raise ValueError("설정검사 증거 크기가 허용 범위를 벗어났습니다")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("설정검사 증거 JSON을 읽을 수 없습니다") from exc
    if not isinstance(payload, dict):
        raise ValueError("설정검사 증거는 JSON 객체여야 합니다")
    required: dict[str, Any] = {
        "schema": schema,
        "mode": "config_only",
        "configuration_ready": True,
        "ready": False,
        "network_attempted": False,
        "candidate_id": candidate_id,
        "config_sha256": config_sha256,
        "contains_secrets": False,
    }
    required.update(extra_required or {})
    mismatched = [name for name, expected in required.items() if payload.get(name) != expected]
    if mismatched:
        raise ValueError(f"설정검사 증거가 현재 후보와 일치하지 않습니다: {', '.join(mismatched)}")
    return sha256_file(path)
