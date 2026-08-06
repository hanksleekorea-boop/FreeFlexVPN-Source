#!/usr/bin/env python3
"""F0-2: 첫 사용 오류별 복구와 보호 범위 안내 계약."""
from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_app_v2  # noqa: E402


RECOVERY = ("qr-unreadable", "camera-denied", "qr-expired", "file-empty", "file-unsupported")


def contract(html: str, shell: str, css: str) -> bool:
    return all(
        (
            all(f'data-svc-recovery="{name}"' in shell for name in RECOVERY),
            "const recoveryCopy=" in shell,
            "data-svc-recovery-output" in shell,
            "WireGuard 스위치가 켜지고 터널·외부 IP·DNS·IPv6·차단 스위치가 확인된 경우만 보호됨으로 표시합니다." in shell,
            "이 웹 화면은 스위치를 대신 켜지 않습니다." in shell,
            ".svc-recovery-options button" in css,
            'data-service-shell' in html,
            "file-unsupported" in html,
        )
    )


def main() -> None:
    html = build_app_v2.build().read_text(encoding="utf-8")
    shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    css = (ROOT / "20_SRC" / "html_templates" / "service_shell.css").read_text(encoding="utf-8")
    checks = [
        ("오류 5종과 보호 범위 안내", contract(html, shell, css)),
        ("음성 대조: 카메라 거부 경로 제거 거부", not contract(html, shell.replace('data-svc-recovery="camera-denied"', 'data-removed="camera-denied"'), css)),
        ("음성 대조: 웹이 스위치를 켠다는 오표기 거부", not contract(html, shell.replace('이 웹 화면은 스위치를 대신 켜지 않습니다.', '이 웹 화면이 스위치를 켭니다.'), css)),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"F0-2 첫 사용 복구 UI {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
