#!/usr/bin/env python3
"""공개 v2.3 기준에서 공개 v2.5 PC판까지의 배포·증거 차이 원장을 만든다."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TRACKED = (
    "20_SRC/app/runtime_acceptance.py",
    "20_SRC/app/runtime_evidence.py",
    "70_TOOLS/evaluate_runtime_acceptance.py",
    "70_TOOLS/build_runtime_evidence_workbench.py",
    "70_TOOLS/check_inline_html_js.mjs",
    "20_SRC/html_templates/runtime_evidence_workbench_v2_17.html",
    "60_OUTPUTS/FreeFlexVPN_runtime_evidence_workbench_v2.17_2026-08-03.html",
    "10_STATE/RUNTIME_EVIDENCE_CONTRACT_v2.17_2026-08-03.md",
    "10_STATE/RUNTIME_ACCEPTANCE_PLAN_v2.16_2026-08-03.md",
    "10_STATE/POLICY_CODE_CONSISTENCY_v0.2_2026-08-03.md",
    "20_SRC/cost_model.py",
)
PC_TRACKED = (
    "20_SRC/build_app_v2.py",
    "20_SRC/build_web_assets.py",
    "20_SRC/html_templates/app_v2.html",
    "30_DEPLOY/app.html",
    "60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.4_PC1.html",
    "60_OUTPUTS/prototype/FreeFlexVPN_app_prototype_v2.5_PC2_PC3.html",
    "40_TESTS/test_pc_viewport.py",
    "40_TESTS/test_keyboard.py",
    "40_TESTS/test_pc_home.py",
    "40_TESTS/test_pc_handoff.py",
    "40_TESTS/test_desktop_app_mode.py",
)


def file_record(relative: str) -> dict[str, object]:
    path = ROOT / relative
    data = path.read_bytes()
    return {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()}


def build_release_diff() -> dict[str, object]:
    handoff = json.loads((ROOT / "10_STATE" / "HANDOFF_EVIDENCE_2026-08-03.json").read_text(encoding="utf-8"))
    progress = json.loads((ROOT / "10_STATE" / "GENERATED_PROGRESS_V2_15_R2_2026-08-03.json").read_text(encoding="utf-8"))
    baseline_public = handoff["public_readback"]
    public = json.loads((ROOT / "10_STATE" / "PUBLIC_EVIDENCE_PC_WEB_V2_5_2026-08-04.json").read_text(encoding="utf-8"))
    local_shell = file_record("30_DEPLOY/app.html")
    shell_equal = local_shell["bytes"] == public["bytes"] and local_shell["sha256"] == public["sha256"]
    return {
        "schema": "FreeFlexVPNReleaseDiffV2",
        "generated_on": "2026-08-04",
        "from": {
            "handoff_candidate": handoff["candidate"],
            "public_version": baseline_public["version"],
            "public_url": baseline_public["url"],
            "public_bytes": baseline_public["bytes_each"],
            "public_sha256": baseline_public["sha256"],
        },
        "to": {
            "local_candidate": "v2.21-pc-public",
            "deployed": True,
            "public_version": public["version"],
            "public_url": public["public_url"],
            "public_bytes": public["bytes"],
            "public_sha256": public["sha256"],
            "github_commit": public["github_commit"],
            "github_actions_conclusion": public["github_actions_conclusion"],
            "progress_percent": progress["actual_percent"],
            "progress_changed": False,
        },
        "app_shell": {
            "local_deploy": local_shell,
            "equal_to_verified_public_v2_5": shell_equal,
            "visible_change": "PC-2·3: 3영역 책상형 홈·정직한 대형 통계·상시 QR 핸드오프",
            "deployment_action": "completed_and_publicly_verified",
        },
        "local_changes": [
            {
                "area": "pc_responsive_web_train",
                "summary": "단일 HTML 반응형 PC 홈, 대형 통계, 상시 QR, 키보드와 1024px 미만 무변화 검사",
                "evidence_level": "implementation_local_and_public_browser_regression",
                "public_effect": "deployed_v2_5",
                "files": [file_record(path) for path in PC_TRACKED],
            },
            {
                "area": "runtime_acceptance",
                "summary": "T1~T10 실패 폐쇄형 대상환경·독립 사용자 판정과 원본 해시 결속",
                "evidence_level": "implementation_and_local_only",
                "public_effect": "none",
                "files": [record for record in map(file_record, TRACKED) if "runtime_acceptance" in record["path"] or "runtime_evidence" in record["path"] or "RUNTIME_ACCEPTANCE" in record["path"] or "inline_html" in record["path"]],
            },
            {
                "area": "policy_code_consistency",
                "summary": "저장·비저장·미확정 값의 정책-코드 대조 안전망",
                "evidence_level": "implementation_and_local_only_not_legal_review",
                "public_effect": "none",
                "files": [file_record("10_STATE/POLICY_CODE_CONSISTENCY_v0.2_2026-08-03.md")],
            },
            {
                "area": "provider_cost_input",
                "summary": "혼합 통화·fair-use·속도캡·VPN 재판매 약관 입력 검증",
                "evidence_level": "implementation_and_local_only",
                "public_effect": "none",
                "files": [file_record("20_SRC/cost_model.py")],
                "contract_numbers_changed": False,
            },
        ],
        "still_missing": [
            "GCP S-1 project/billing/credit/cost/budget readback",
            "actual VPN server runtime",
            "actual device tunnel and T1~T9 evidence",
            "independent user T10 evidence",
            "actual payment/refund evidence",
        ],
        "claim_boundary": "공개 앱은 UI 앱 셸 v2.5이며 실제 VPN 연결 서비스가 아닙니다",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    if not output.is_absolute():
        output = (ROOT / output).resolve()
    if output.exists():
        raise FileExistsError(f"기존 릴리스 원장은 덮어쓰지 않습니다: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_release_diff(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"릴리스 차이 원장 생성 PASS — {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
