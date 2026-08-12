#!/usr/bin/env python3
"""F2-2: PC-to-phone handoff is reachable and does not overstate iPhone support."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def contract(text: str) -> bool:
    start = text.find("data-svc-ios-guide")
    end = text.find("const recoveryCopy=", start)
    feature = text[start:end]
    return all((
        'data-svc-handoff-qr' in text,
        'src="app-qr.png"' in text,
        'data-svc-ios-guide' in feature,
        'data-svc-handoff-scope' in feature,
        'data-svc-handoff-guide' in text,
        'QR에는 서비스 주소만 들어 있으며 개인키·기기 정보는 넣지 않습니다.' in text,
        '실제 설치·연결·재연결은 아직 검증 전입니다.' in text,
        'VPN 설정 QR과 서비스 주소 QR은 서로 다릅니다.' in text,
        '운영 API와 실기기 검증 뒤에만 추가합니다.' in feature,
        'window.open(' not in feature,
        'fetch(' not in feature,
    ))


def main() -> None:
    require(contract(SHELL), "device handoff contract broken")
    require(not contract(SHELL.replace('data-svc-handoff-qr', 'data-svc-handoff-missing')), "negative control: missing QR was not detected")
    require(not contract(SHELL.replace('실제 설치·연결·재연결은 아직 검증 전입니다.', 'iPhone 연결이 확인되었습니다.')), "negative control: iPhone overclaim was not detected")
    print("device handoff UI: 13/13 passed")


if __name__ == "__main__":
    main()
