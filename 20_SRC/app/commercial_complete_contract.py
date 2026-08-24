#!/usr/bin/env python3
"""Commercial-Complete v2 정본과 작업 영수증을 fail-closed로 검증한다."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_IDS = tuple(f"CC-BASE-{number:02d}" for number in range(1, 11))
IMPROVEMENT_IDS = tuple(f"CC-{number:02d}" for number in range(1, 25))
TASK_IDS = (
    *(f"CC-TASK-1-{number:02d}" for number in range(17)),
    *(f"CC-TASK-2-{number:02d}" for number in range(1, 8)),
    *(f"CC-TASK-3-{number:02d}" for number in range(1, 6)),
)
ALLOWED_RECEIPT_STATUS = {
    "ready", "planned", "in_progress", "waiting_external", "blocked",
    "done_code", "done_verified",
}
EVIDENCE_STATUS = {"not_run", "pass", "fail", "partial", "not_applicable"}
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|cookie|private[_-]?key|configuration|config_text|"
    r"serial|account_raw|observed[_-]?ip|ip_address)", re.IGNORECASE
)
ALLOWED_CHANGED_ROOTS = {
    "00_START", "10_PLAN", "10_STATE", "20_SRC", "30_DEPLOY", "40_TESTS",
    "50_RELEASE", "60_OUTPUTS", "70_TOOLS", ".project-continuity",
}


class CommercialContractError(ValueError):
    """정본 또는 작업 영수증이 안전 계약을 어겼다."""


def _ordered_unique_matches(pattern: str, text: str) -> tuple[str, ...]:
    values = tuple(re.findall(pattern, text, re.MULTILINE))
    if len(values) != len(set(values)):
        raise CommercialContractError("duplicate_contract_id")
    return values


def _expand_dependencies(text: str) -> tuple[str, ...]:
    if "없음" in text:
        return ()
    dependencies: list[str] = []
    for start, end in re.findall(r"([123]-\d{2})(?:~([123]-\d{2}))?", text):
        if not end:
            dependencies.append(f"CC-TASK-{start}")
            continue
        stage, first = start.split("-")
        end_stage, last = end.split("-")
        if stage != end_stage or int(last) < int(first):
            raise CommercialContractError("invalid_dependency_range")
        dependencies.extend(f"CC-TASK-{stage}-{number:02d}" for number in range(int(first), int(last) + 1))
    if not dependencies:
        raise CommercialContractError("unreadable_dependency")
    return tuple(dependencies)


def validate_canonical_documents(service_text: str, development_text: str) -> dict[str, Any]:
    """정확한 제품 계약·상용 관문·작업 순서와 비하향 문구를 검증한다."""
    bases = _ordered_unique_matches(r"^- `(CC-BASE-\d{2})`:", service_text)
    improvements = _ordered_unique_matches(r"^\| (CC-\d{2}) \|", service_text)
    gates = re.findall(r"^(\d{1,2})\. .+$", service_text[service_text.find("### 14.8 1단계 완전 상용화 통과 조건 CC-GATE-1"):], re.MULTILINE)
    tasks = _ordered_unique_matches(r"^#### (CC-TASK-[123]-\d{2})\b", development_text)
    if bases != BASE_IDS:
        raise CommercialContractError("base_contract_order_or_count")
    if improvements != IMPROVEMENT_IDS:
        raise CommercialContractError("improvement_order_or_count")
    if tuple(gates[:18]) != tuple(str(number) for number in range(1, 19)):
        raise CommercialContractError("commercial_gate_order_or_count")
    if tasks != TASK_IDS:
        raise CommercialContractError("task_order_or_count")

    required_phrases = (
        "매월 무료 1GB", "공식 WireGuard", "기존 `ffvpn`", "자동 삭제·덮어쓰기·자동 활성화하지 않는다",
        "Drive B를 연결·읽기·쓰기·복원·삭제에 사용하지 않는다", "실제 IP·개인키·VPN 설정 원문·방문 기록",
        "DONE-CODE", "DONE-VERIFIED", "없는 증거는 `not_run`",
    )
    for phrase in required_phrases:
        if phrase not in service_text and phrase not in development_text:
            raise CommercialContractError(f"missing_non_regression_phrase:{phrase}")

    rows = re.findall(
        r"^\| ([123]-\d{2}) \| [^|]+ \| [^|]+ \| ([^|]+) \| ([^|]+) \| [^|]+ \|$",
        development_text,
        re.MULTILINE,
    )
    if len(rows) != len(TASK_IDS):
        raise CommercialContractError("task_dependency_table_count")
    positions = {task_id: index for index, task_id in enumerate(TASK_IDS)}
    graph: dict[str, tuple[str, ...]] = {}
    for short_id, dependency_text, initial_status in rows:
        task_id = f"CC-TASK-{short_id}"
        if "DONE" in initial_status.upper():
            raise CommercialContractError("false_initial_completion")
        dependencies = _expand_dependencies(dependency_text)
        if task_id == TASK_IDS[0] and dependencies:
            raise CommercialContractError("first_task_has_dependency")
        for dependency in dependencies:
            if dependency not in positions:
                raise CommercialContractError("unknown_dependency")
            if positions[dependency] >= positions[task_id]:
                raise CommercialContractError("forward_or_cyclic_dependency")
        graph[task_id] = dependencies
    return {"bases": len(bases), "improvements": len(improvements), "gates": 18, "tasks": len(tasks), "dependencies": graph}


def _walk_for_sensitive_keys(value: Any, path: str = "receipt") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_KEY.search(str(key)):
                raise CommercialContractError(f"sensitive_receipt_key:{path}.{key}")
            _walk_for_sensitive_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_for_sensitive_keys(item, f"{path}[{index}]")


def validate_task_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """거짓 완료와 작업 범위 밖·민감정보 포함 영수증을 거부한다."""
    if not isinstance(receipt, dict):
        raise CommercialContractError("receipt_not_object")
    _walk_for_sensitive_keys(receipt)
    if receipt.get("schema") != "FreeFlexVPNCommercialTaskReceiptV2":
        raise CommercialContractError("receipt_schema")
    task_id = receipt.get("task_id")
    if task_id not in TASK_IDS:
        raise CommercialContractError("receipt_task_id")
    status = receipt.get("status")
    if status not in ALLOWED_RECEIPT_STATUS:
        raise CommercialContractError("receipt_status")
    changed_paths = receipt.get("changed_paths")
    if not isinstance(changed_paths, list):
        raise CommercialContractError("changed_paths_not_list")
    for raw_path in changed_paths:
        if not isinstance(raw_path, str):
            raise CommercialContractError("changed_path_not_string")
        path = Path(raw_path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] not in ALLOWED_CHANGED_ROOTS:
            raise CommercialContractError("changed_path_outside_workspace_contract")
    preserved = receipt.get("preserved_contracts")
    if not isinstance(preserved, list) or not set(BASE_IDS).issubset(preserved):
        raise CommercialContractError("base_contracts_not_preserved")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        raise CommercialContractError("evidence_not_object")
    for kind in ("automatic", "browser", "device", "external", "rollback"):
        item = evidence.get(kind)
        if not isinstance(item, dict) or item.get("status") not in EVIDENCE_STATUS:
            raise CommercialContractError(f"evidence_status:{kind}")
    unknowns = receipt.get("unknowns")
    if not isinstance(unknowns, list):
        raise CommercialContractError("unknowns_not_list")
    if status == "done_verified":
        if unknowns:
            raise CommercialContractError("verified_with_unknowns")
        if any(evidence[kind]["status"] != "pass" for kind in ("automatic", "browser", "device", "external", "rollback")):
            raise CommercialContractError("verified_without_all_evidence")
    if status == "done_code" and evidence["automatic"]["status"] != "pass":
        raise CommercialContractError("done_code_without_automatic_pass")
    return {"task_id": task_id, "status": status, "changed_paths": tuple(changed_paths)}
