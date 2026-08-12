#!/usr/bin/env python3
"""Commercialization plan must retain all release gates and honest status."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT = (ROOT / "10_PLAN" / "COMMERCIAL_RELEASE_GATE_PLAN_v1_2026-08-10.md").read_text(encoding="utf-8")

for gate in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"):
    assert gate in TEXT, f"출시 관문 누락: {gate}"
for required in ("월 USD 10", "실제 Android", "상용화 준비 미완료", "비밀키", "다음 첫 행동"):
    assert required in TEXT, f"상용화 계획 필수 항목 누락: {required}"
assert "G0·G1은 진행 단계" in TEXT
assert "예산 알림은 자동 중지가 아니" in TEXT
print("상용화 출시 관문 계획 계약 1/1 통과")
