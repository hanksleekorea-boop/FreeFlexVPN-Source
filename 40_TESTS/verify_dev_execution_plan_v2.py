from __future__ import annotations

import argparse
import json
from pathlib import Path

import verify_app_service_plan_v2 as base


base.REQUIRED = [
    "새 기획의 핵심 가치를 실제 기능과 디자인 UX로 먼저 구현해 가장 빠른 안전 알파를 공개한다",
    "무료 실제 VPN + 순간 중심 UX + 3잔액 데이터 지갑 + 실제 보호 확인 + 양쪽 추천 보상",
    "4~6 개발시간",
    "44~60 개발시간",
    "최단 5개 작업일",
    "A0 무료 알파",
    "A1 유료 알파",
    "실제 터널·출구 IP·최근 확인 시각",
    "친구의 첫 실제 터널 + 누적 100MB 후 양쪽 500MB",
    "Moment Card",
    "Truth Orb",
    "Wallet Stack",
    "Referral Rail",
    "SQLite WAL + append-only 원장",
    "wallet_entries",
    "POST /v1/claims/exchange",
    "20_SRC/html_templates/app_v2.html",
    "R3-ui-truth",
    "R4-moment-home",
    "R5-wallet",
    "R7-referral",
    "R6-real-vpn",
    "A0-alpha",
    "서울 서버를 카탈로그에 넣으면 실패",
    "개인키가 네트워크 요청·로그·DOM 영구 저장에 나타나면 실패",
    "실사용자 증거가 없으면 알파 후보 또는 대상환경 준비 완료",
]

base.FORBIDDEN_CLAIMS = [
    "검사를 생략해 맞춘 일정이 유효하다",
    "WireGuard 개인키를 서버에 저장",
    "PWA가 OS VPN을 직접 제어한다",
    "실사용자 없이 알파 완료라고 선언",
    "대한민국 · 서울표준 서버",
]


def validate_text(text: str):
    normalized = text.replace("**", "").replace("`", "")
    return {
        "missing": [value for value in base.REQUIRED if value not in normalized],
        "forbidden": [value for value in base.FORBIDDEN_CLAIMS if value in normalized],
    }


base.validate_text = validate_text


def negative_control(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    needle = base.REQUIRED[0]
    mutated = text.replace(needle, "의도적으로 제거된 알파 목표", 1)
    result = base.validate_text(mutated)
    passed = needle in result["missing"]
    return {"status": "PASS" if passed else "FAIL", "detected_missing": result["missing"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("docx", type=Path, nargs="?")
    parser.add_argument("--negative-control", action="store_true")
    args = parser.parse_args()
    if args.negative_control:
        report = negative_control(args.markdown)
    else:
        if args.docx is None:
            parser.error("docx is required unless --negative-control is used")
        report = base.run(args.markdown, args.docx)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
