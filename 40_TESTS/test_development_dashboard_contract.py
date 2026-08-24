#!/usr/bin/env python3
"""The current Markdown dashboard must keep the required user-facing sections."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT = (ROOT / "00_START" / "DEVELOPMENT_DASHBOARD.md").read_text(encoding="utf-8")

required = (
    "## 서비스 요약",
    "## 기준 대시보드와 공개 화면",
    "## 전체 신호등",
    "## 진척률",
    "## 기능별 상태",
    "## 오류·병목·위험",
    "## 다음 우선 작업 1~3개",
    "## 다음 실행 우선순위 20",
    "## 사용자 없이 단독 실행 가능한 우선순위 20",
    "## 증거 구분",
    "## 화면 검증",
    "→ 이 그림의 뜻:",
    "⚠ 실제 Android 검사 필요",
    "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
    "공개 개발 진척 대시보드",
    "app-qr.png",
)

missing = [value for value in required if value not in TEXT]
assert not missing, f"대시보드 필수 항목 누락: {missing}"
assert TEXT.count("## 서비스 요약") == 2, "서비스 요약은 처음과 끝에 있어야 합니다"
assert "실제 Android 검사: **IPv4 핵심 경로 부분 통과**" in TEXT
assert "2026-08-22 태국→미국 출구" in TEXT
assert "새 Android 검증 프로필 별도 발급·가져오기" in TEXT
assert "CC-TASK-1-00" in TEXT
assert "CC-TASK-1-04" in TEXT
assert "예산 알림은 자동 지출 차단이 아니" in TEXT
assert "(Resolve-Path .\\30_DEPLOY\\app-qr.png).Path" in TEXT
assert "C:/Users/x13" not in TEXT
print("개발·디자인·UX 대시보드 계약 1/1 통과")
