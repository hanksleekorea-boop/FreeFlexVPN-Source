#!/usr/bin/env python3
"""F0-1: 증거 부족을 보호 완료처럼 표시하지 않는 UI 계약."""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_app_v2  # noqa: E402
from app.connection_check import evaluate_connection  # noqa: E402


def ui_contract(html: str, shell: str, css: str) -> bool:
    return all(
        (
            'data-connection-state="limited" data-presentation-state="unverified"' in html,
            "보호 상태 확인 불가" in html,
            "presentation:'unverified'" in html,
            "const engineState=connectionStates[state]?state:'limited'" in html,
            "setConnectionState('protected')" not in html,
            'data-state="unverified" data-engine-state="limited"' in shell,
            "limited:'unverified'" in shell,
            "setup_needed:'unverified'" in shell,
            "status.dataset.engineState=state" in shell,
            '.svc-status-row[data-state="unverified"]' in css,
        )
    )


def main() -> None:
    html = build_app_v2.build().read_text(encoding="utf-8")
    shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    css = (ROOT / "20_SRC" / "html_templates" / "service_shell.css").read_text(encoding="utf-8")
    limited = evaluate_connection(
        profile_present=True,
        tunnel_started=True,
        observed_exit_ip="198.51.100.10",
        expected_exit_ip="198.51.100.10",
        server_health="healthy",
        handshake_at=datetime.now(timezone.utc),
        dns_protected=None,
        ipv6_protected=True,
        kill_switch_protected=True,
    )
    checks = [
        ("엔진은 근거 부족에서 limited를 유지", limited["state"] == "limited" and not limited["protected"]),
        ("초기 UI는 확인 불가 표현", ui_contract(html, shell, css)),
        ("protected는 검사 호출로 하드코딩되지 않음", "setConnectionState('protected')" not in html),
        ("음성 대조: limited를 checking으로 바꾸면 계약 거부", not ui_contract(html, shell.replace("limited:'unverified'", "limited:'checking'"), css)),
        ("음성 대조: 확인 불가 스타일 제거 시 계약 거부", not ui_contract(html, shell, css.replace('.svc-status-row[data-state="unverified"]', '.removed'))),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"F0-1 보호 상태 UI {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
