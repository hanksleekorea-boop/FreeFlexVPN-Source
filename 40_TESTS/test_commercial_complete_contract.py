#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "20_SRC" / "app" / "commercial_complete_contract.py"
SPEC = importlib.util.spec_from_file_location("commercial_complete_contract", MODULE_PATH)
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


service = (ROOT / "10_PLAN" / "CURRENT_SERVICE_PLAN.md").read_text(encoding="utf-8")
development = (ROOT / "10_PLAN" / "CURRENT_DEVELOPMENT_EXECUTION_PLAN.md").read_text(encoding="utf-8")
checks: list[tuple[str, bool]] = []


def check(name: str, condition: bool) -> None:
    checks.append((name, bool(condition)))


def rejects(name: str, callback, expected: str) -> None:
    try:
        callback()
    except contract.CommercialContractError as error:
        check(name, expected in str(error))
    else:
        check(name, False)


summary = contract.validate_canonical_documents(service, development)
check("정상 정본 10·24·18·29", tuple(summary[key] for key in ("bases", "improvements", "gates", "tasks")) == (10, 24, 18, 29))
rejects("무료 1GB 삭제 거부", lambda: contract.validate_canonical_documents(service.replace("매월 무료 1GB", "무료 권리"), development), "missing_non_regression_phrase")
rejects("WireGuard 삭제 거부", lambda: contract.validate_canonical_documents(service.replace("공식 WireGuard", "통신 방식"), development.replace("공식 WireGuard", "통신 방식")), "missing_non_regression_phrase")
rejects("기존 프로필 보존 삭제 거부", lambda: contract.validate_canonical_documents(service.replace("자동 삭제·덮어쓰기·자동 활성화하지 않는다", "관리한다"), development), "missing_non_regression_phrase")
rejects("Drive B 제외 삭제 거부", lambda: contract.validate_canonical_documents(service.replace("Drive B를 연결·읽기·쓰기·복원·삭제에 사용하지 않는다", "외장 저장소를 사용하지 않는다"), development), "missing_non_regression_phrase")
rejects("기본 계약 누락 거부", lambda: contract.validate_canonical_documents(service.replace("- `CC-BASE-10`:", "- `CC-BASE-X`:", 1), development), "base_contract_order_or_count")
rejects("작업 거짓 완료 거부", lambda: contract.validate_canonical_documents(service, development.replace("| READY | 안전한 시작점 |", "| DONE | 안전한 시작점 |", 1)), "false_initial_completion")
rejects("순방향 선행 거부", lambda: contract.validate_canonical_documents(service, development.replace("| 1-01 | 보호 카드·증거 결속 | CC-01 | 1-00 |", "| 1-01 | 보호 카드·증거 결속 | CC-01 | 1-02 |", 1)), "forward_or_cyclic_dependency")

template = json.loads((ROOT / "10_STATE" / "CC_TASK_RECEIPT_TEMPLATE_v2.json").read_text(encoding="utf-8"))
validated = contract.validate_task_receipt(template)
check("준비 영수증 정상", validated["status"] == "ready")
done_code = copy.deepcopy(template)
done_code["status"] = "done_code"
rejects("자동 검사 없는 코드 완료 거부", lambda: contract.validate_task_receipt(done_code), "done_code_without_automatic_pass")
done_verified = copy.deepcopy(template)
done_verified["status"] = "done_verified"
done_verified["unknowns"] = []
rejects("외부 증거 없는 검증 완료 거부", lambda: contract.validate_task_receipt(done_verified), "verified_without_all_evidence")
sensitive = copy.deepcopy(template)
sensitive["private_key"] = "forbidden"
rejects("민감 필드 거부", lambda: contract.validate_task_receipt(sensitive), "sensitive_receipt_key")
outside = copy.deepcopy(template)
outside["changed_paths"] = ["../outside.txt"]
rejects("작업 폴더 밖 경로 거부", lambda: contract.validate_task_receipt(outside), "changed_path_outside_workspace_contract")
for receipt_path in sorted((ROOT / "10_STATE").glob("CC_TASK_?-??_*.json")):
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    validated_receipt = contract.validate_task_receipt(receipt)
    check(f"실제 영수증 검증 {validated_receipt['task_id']}", validated_receipt["status"] == "done_code")

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed:
    raise SystemExit(f"Commercial-Complete v2 계약 실패: {', '.join(failed)}")
print(f"Commercial-Complete v2 계약 {len(checks)}/{len(checks)} 통과")
