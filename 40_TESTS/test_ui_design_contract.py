#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공식 채택 UI·UX 정본과 프로토타입의 동기화를 검사한다."""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import cost_model  # noqa: E402


UI_DOC = ROOT / "10_STATE" / "UI_DESIGN_v1.1_2026-08-01.md"
PROTOTYPE = ROOT / "60_OUTPUTS" / "prototype" / "FreeFlexVPN_app_prototype_v1.1.html"
DECISIONS = ROOT / "10_STATE" / "DECISIONS.md"
PRIORITIES = ROOT / "10_STATE" / "PRIORITIES.md"


def declared_hash(text: str) -> str | None:
    match = re.search(r"기준 파일 SHA-256:\s*`([0-9a-f]{64})`", text)
    return match.group(1) if match else None


def hash_matches(doc_text: str, prototype_bytes: bytes) -> bool:
    return declared_hash(doc_text) == hashlib.sha256(prototype_bytes).hexdigest()


def main() -> None:
    results: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        results.append((name, bool(condition)))

    check("UI 정본 존재", UI_DOC.is_file())
    check("프로토타입 존재", PROTOTYPE.is_file())
    if not UI_DOC.is_file() or not PROTOTYPE.is_file():
        for name, passed in results:
            print(f"{'PASS' if passed else 'FAIL'}  {name}")
        raise SystemExit(1)

    doc = UI_DOC.read_text(encoding="utf-8")
    prototype_bytes = PROTOTYPE.read_bytes()
    html = prototype_bytes.decode("utf-8")
    decisions = DECISIONS.read_text(encoding="utf-8")
    priorities = PRIORITIES.read_text(encoding="utf-8")

    check("채택 상태", "DESIGN_COMPLETE · ADOPTED" in doc)
    check("결정 원장 D12", "| D12 |" in decisions and "UI_DESIGN_v1.1_2026-08-01.md" in decisions)
    check("우선순위 동기화", "공식 UI·UX 채택" in priorities and "채택 UI v1.1" in priorities)
    check("프로토타입 채택 표식", "ADOPTED" in html and "UI · UX v1.1" in html)
    check("정본 해시 일치", hash_matches(doc, prototype_bytes))

    scope = doc.split("## 1. 채택 범위", 1)[1].split("## 2. 시각 계약", 1)[0]
    declared_screens = [
        row.split("|")[1].strip()
        for row in scope.splitlines()
        if re.match(r"^\|[^|-]+\|", row) and row.split("|")[1].strip() != "화면"
    ]
    implemented_screens = re.findall(r'<section[^>]+data-screen="([^"]+)"', html)
    check("화면 수 정본 일치", len(declared_screens) == len(implemented_screens))
    check("구현 화면 중복 없음", len(implemented_screens) == len(set(implemented_screens)))

    packs = cost_model.contracts()["packs"]
    check(
        "가격팩 전건 반영",
        all(f"{pack['gb']}GB" in html and f"{pack['price']:,}원" in html for pack in packs),
    )
    check("가격 미검증 경계", "지불의사 미검증" in doc and "지불의사 미검증" in html)
    check("실서비스 미연결 경계", "실제 VPN·결제·계정 발급 기능 없음" in html)
    check("터치 겹침 교정 계약", "position:relative;height:72px;margin:18px -12px -82px" in html)

    mutated = prototype_bytes.replace(b"ADOPTED", b"REMOVED", 1)
    check("음성 대조: 한 표식 변조를 거부", hashlib.sha256(mutated).hexdigest() != declared_hash(doc))

    failures = [(name, passed) for name, passed in results if not passed]
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"UI·UX 채택 검사 {len(results) - len(failures)}/{len(results)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
