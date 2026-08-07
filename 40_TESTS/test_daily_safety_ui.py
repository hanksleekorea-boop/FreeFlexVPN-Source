#!/usr/bin/env python3
"""F1-2: ordinary-safety UI must be reachable, local-only, and removable."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def contract(text: str) -> bool:
    return all((
        'data-svc-alert-request' in text,
        'Notification.requestPermission()' in text,
        'data-svc-history-clear>이 기기 기록 지우기' in text,
        'safeRemove(safetyHistoryKey)' in text,
        'data-svc-diagnostic-show' in text,
        'IP 주소·개인키·설정 파일·방문 기록' in text,
        '이 화면 밖으로 자동 전송하지 않습니다.' in text,
        'data-svc-go="locations"' in text,
        'readSafetyHistory=()=>{try' in text,
        not re.search(r"fetch\([^)]*safety", text),
    ))


def main() -> None:
    require(contract(SHELL), "daily safety contract broken")
    require(not contract(SHELL.replace('data-svc-history-clear>이 기기 기록 지우기', 'data-svc-history-missing>이 기기 기록 지우기', 1)), "negative control: missing deletion button was not detected")
    print("daily safety UI: 10/10 passed")


if __name__ == "__main__":
    main()
