#!/usr/bin/env python3
"""F2-1: travel planning remains local and never invents routes or legal advice."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def contract(text: str) -> bool:
    start = text.find("const travelNames=")
    end = text.find("renderDailySafety();", start)
    feature = text[start:end]
    return all((
        'data-svc-travel-country' in text,
        'data-svc-travel-state' in text,
        'data-svc-travel-favorite' in text,
        'data-svc-travel-clear' in text,
        'data-svc-travel-no-recommendation' in text,
        "travelSafetyKey='freeflex-travel-plan-v1'" in text,
        '실제 경로와 현지 규칙은 확인 전입니다.' in feature,
        '이 화면은 법률 조언이 아닙니다.' in text,
        '추천 꺼짐' in feature,
        'safeRemove(travelSafetyKey)' in feature,
        'fetch(' not in feature,
        'navigator.geolocation' not in feature,
    ))


def main() -> None:
    require(contract(SHELL), "travel safety contract broken")
    require(not contract(SHELL.replace('data-svc-travel-clear', 'data-svc-travel-missing')), "negative control: missing local deletion was not detected")
    require(not contract(SHELL.replace('이 화면은 법률 조언이 아닙니다.', '현지 규칙은 보장합니다.')), "negative control: legal-scope warning was not detected")
    print("travel safety UI: 14/14 passed")


if __name__ == "__main__":
    main()
