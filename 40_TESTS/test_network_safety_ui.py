#!/usr/bin/env python3
"""F1-3: network transition guidance stays local, reachable, and honest."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def contract(text: str) -> bool:
    start = text.find("const safetyHistoryKey=")
    end = text.find("shell.querySelectorAll('[data-svc-toast]')", start)
    feature = text[start:end]
    return all((
        start >= 0,
        'data-svc-always-on-guide' in text,
        'data-svc-kill-switch-guide' in text,
        'data-svc-public-network' in text,
        'data-svc-network-guide' in text,
        'data-svc-network-state' in text,
        '웹 화면은 운영체제의 항상 켜기·차단 모드를 대신 켜지 않습니다.' in text,
        "networkSafetyKey='freeflex-network-safety-v1'" in text,
        "window.addEventListener('offline'" in text,
        "window.addEventListener('online'" in text,
        '보호 여부를 판단하지 않습니다.' in feature,
        '실제 보호 상태는 확인 전입니다.' in feature,
        'navigator.connection' not in feature,
    ))


def main() -> None:
    require(contract(SHELL), "network safety contract broken")
    require(not contract(SHELL.replace('data-svc-kill-switch-guide', 'data-svc-kill-switch-missing')), "negative control: missing kill-switch guide was not detected")
    require(not contract(SHELL.replace('보호 여부를 판단하지 않습니다.', '보호됨')), "negative control: overclaim was not detected")
    print("network safety UI: 15/15 passed")


if __name__ == "__main__":
    main()
