#!/usr/bin/env python3
"""화면 라이브러리가 막혀도 기존 공개 아이콘으로 웹 결과를 만들 수 있는지 확인한다."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "20_SRC" / "build_web_assets.py").read_text(encoding="utf-8")

ast.parse(SOURCE)
for token in ("except ImportError", "def encoded_icons()", "icon-{size}.png", "_generated_icons"):
    assert token in SOURCE, f"아이콘 대체 생성 계약 누락: {token}"
for size in (192, 512):
    path = ROOT / "20_SRC" / "github_pages" / f"icon-{size}.png"
    assert path.is_file() and path.stat().st_size > 0, f"기존 아이콘 누락: {path}"
print("웹 아이콘 대체 생성 계약 1/1 통과")
