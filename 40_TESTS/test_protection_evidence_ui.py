#!/usr/bin/env python3
"""F0-2: 보호 판정 근거를 고객 화면에 항목별로 보여 주는 계약."""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_app_v2  # noqa: E402
from app.connection_check import evaluate_connection  # noqa: E402


EVIDENCE = ("tunnel", "exit-ip", "dns", "ipv6", "kill-switch")


def service_contract(html: str, shell: str, runtime: str, css: str) -> bool:
    return all(
        (
            all(f'data-svc-evidence="{name}"' in shell for name in EVIDENCE),
            "모든 항목이 확인돼야 보호됨으로 표시합니다." in shell,
            "const evidenceKeys=" in shell,
            "freeflex:protection-evidence" in shell,
            "data-protection-retry" in html,
            all(f'data-check="{name}"' in html for name in (*EVIDENCE, "checked-at")),
            "freeflex:protection-evidence" in runtime,
            all(key in runtime for key in ("exit_ip", "kill_switch", "ipv6", "checks.dns")),
            "observed_exit_ip" not in runtime[runtime.index('freeflex:protection-evidence'):runtime.index('const map', runtime.index('freeflex:protection-evidence'))],
            '.svc-evidence-row[data-pass="true"]' in css,
            '.svc-evidence-row[data-pass="false"]' in css,
            "setConnectionState('protected')" not in html,
        )
    )


def main() -> None:
    html = build_app_v2.build().read_text(encoding="utf-8")
    shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    css = (ROOT / "20_SRC" / "html_templates" / "service_shell.css").read_text(encoding="utf-8")
    runtime = (ROOT / "20_SRC" / "app" / "pwa_runtime.js").read_text(encoding="utf-8")
    limited = evaluate_connection(
        profile_present=True,
        tunnel_started=True,
        observed_exit_ip="198.51.100.10",
        expected_exit_ip="198.51.100.10",
        server_health="healthy",
        handshake_at=datetime.now(timezone.utc),
        dns_protected=False,
        ipv6_protected=True,
        kill_switch_protected=True,
    )
    checks = [
        ("DNS 실패는 protected가 아님", limited["state"] == "limited" and limited["checks"]["dns"] is False),
        ("고객용 5개 근거표", service_contract(html, shell, runtime, css)),
        ("음성 대조: 차단 스위치 행 제거 거부", not service_contract(html, shell.replace('data-svc-evidence="kill-switch"', 'data-removed="kill-switch"'), runtime, css)),
        ("음성 대조: 실제 IP를 화면 전달값에 넣으면 거부", not service_contract(html, shell, runtime.replace('checked_at: presentation.checked_at,', 'checked_at: presentation.checked_at, observed_exit_ip: result?.observed_exit_ip,', 1), css)),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"F0-2 보호 근거 UI {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
