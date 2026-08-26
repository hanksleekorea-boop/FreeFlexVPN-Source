#!/usr/bin/env python3
"""GCP-TASK-1-01의 출처 분리 코드가 원본·서비스 화면에 남는지 확인한다."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / "20_SRC" / "app" / "protection_evidence.js").read_text(encoding="utf-8")
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")

required_module = (
    "ALLOWED_SOURCE_CLASSES",
    "directAndroidEvidence",
    "source_class: evidence.source_class",
    "evidence_id: evidence.evidence_id",
    "웹·자동 확인만으로는 실제 Android 보호 상태를 확정하지 않습니다.",
)
required_shell = ("직접 기기 근거 없음", "실제 Android 근거", "detail.evidence_id")

missing = [value for value in (*required_module, *required_shell) if value not in MODULE and value not in SHELL]
assert not missing, f"보호 출처 분리 코드 누락: {missing}"
assert "source_class === \"android\" && evidence.evidence_id !== null" in MODULE
assert "source_class:'automatic'" in (ROOT / "40_TESTS" / "test_cc_protection_card.py").read_text(encoding="utf-8")
print("보호 증거 출처 분리 원본 계약 1/1 통과")
