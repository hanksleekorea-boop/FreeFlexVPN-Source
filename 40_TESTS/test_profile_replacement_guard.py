#!/usr/bin/env python3
"""G1-R: 기존 프로필 보존형 후보 교체 보호장치 계약."""
from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_app_v2  # noqa: E402


def contract(html: str, runtime: str) -> bool:
    return all(
        (
            'id="replacementGuard"' in html,
            'data-replacement-state="idle"' in html,
            'id="confirmReturnPathButton"' in html,
            "기존 WireGuard 설정은 자동으로 지우거나 바꾸지 않습니다." in html,
            "candidateDeviceId && activeIds.includes(candidateDeviceId)" in runtime,
            'replacementPhase === "ready_to_replace"' in runtime,
            '["tunnel", "exit_ip", "handshake", "server", "dns"]' in runtime,
            "기존 설정 폐기는 되돌릴 수 없습니다." in runtime,
            "if (!accepted)" in runtime,
            "device.assigned_address" not in runtime,
            "activeDeviceId = active[0]" not in runtime,
        )
    )


def main() -> None:
    html = build_app_v2.build().read_text(encoding="utf-8")
    runtime = (ROOT / "20_SRC" / "app" / "pwa_runtime.js").read_text(encoding="utf-8")
    checks = [
        ("기존 프로필 보존형 교체 계약", contract(html, runtime)),
        (
            "음성 대조: 후보 우선 선택 제거 감지",
            not contract(html, runtime.replace("candidateDeviceId && activeIds.includes(candidateDeviceId)", "false", 1)),
        ),
        (
            "음성 대조: 마지막 취소 분기 제거 감지",
            not contract(html, runtime.replace("if (!accepted)", "if (false)", 1)),
        ),
        (
            "음성 대조: 실제 주소 노출 회귀 감지",
            not contract(html, runtime + "\ndevice.assigned_address;"),
        ),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"G1-R 프로필 교체 보호장치 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
