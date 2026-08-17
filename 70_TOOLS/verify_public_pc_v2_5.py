#!/usr/bin/env python3
"""현재 공개 FreeFlexVPN 서비스 UI v3의 PC·모바일·대시보드·QR을 검증한다."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import time
import urllib.request

import cv2
import numpy as np
from playwright.sync_api import sync_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC_ROOT = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f"
PUBLIC_APP = f"{PUBLIC_ROOT}/app.html"
PUBLIC_DASHBOARD = f"{PUBLIC_ROOT}/development-dashboard.html"
PUBLIC_QR = f"{PUBLIC_ROOT}/app-qr.png"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        f"{url}?verify={time.time_ns()}",
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "FreeFlexVPN-public-check"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()
    output = pathlib.Path(args.json_output)
    if not output.is_absolute():
        output = (ROOT / output).resolve()
    if output.exists():
        raise FileExistsError(f"기존 공개 증거는 덮어쓰지 않습니다: {output}")

    app_raw = fetch(PUBLIC_APP)
    app_text = app_raw.decode("utf-8")
    dashboard_raw = fetch(PUBLIC_DASHBOARD)
    dashboard_text = dashboard_raw.decode("utf-8")
    qr_raw = fetch(PUBLIC_QR)
    qr_image = cv2.imdecode(np.frombuffer(qr_raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    qr_value, qr_points, _ = cv2.QRCodeDetector().detectAndDecode(qr_image)
    checks: list[tuple[str, bool]] = [
        ("공개 고객 서비스 셸", "data-service-shell" in app_text),
        ("공개 PC 3열 계약", "grid-template-columns:230px minmax(0,1fr) 300px" in app_text),
        ("공개 개발 대시보드 분리", "data-progress-dashboard" not in app_text and "data-progress-dashboard" in dashboard_text),
        ("공개 QR 실제 디코드", qr_points is not None and qr_value == PUBLIC_APP),
    ]

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1280, 1920):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(f"{PUBLIC_APP}?view=app&verify={time.time_ns()}", wait_until="networkidle")
            page.locator("[data-service-shell]").wait_for(state="visible")
            state = page.evaluate(
                """() => {
                  const side=document.querySelector('.svc-side').getBoundingClientRect();
                  const main=document.querySelector('.svc-main').getBoundingClientRect();
                  const aside=document.querySelector('.svc-aside').getBoundingClientRect();
                  const handoff=document.querySelector('[data-svc-handoff-qr]');
                  return {
                    side:side.width, main:main.width, aside:aside.width,
                    scroll:document.documentElement.scrollWidth, view:innerWidth,
                    mobileNav:getComputedStyle(document.querySelector('.svc-mobile-nav')).display,
                    handoff:Boolean(handoff && handoff.complete && handoff.naturalWidth > 0)
                  };
                }"""
            )
            checks.append(
                (
                    f"{width}px 고객 PC 3열·무가로넘침",
                    state["side"] >= 200
                    and state["main"] >= 500
                    and state["aside"] >= 280
                    and state["scroll"] <= state["view"] + 1
                    and state["mobileNav"] == "none",
                )
            )
            checks.append((f"{width}px 휴대폰 이어보기 QR 가시", state["handoff"]))
            page.close()

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{PUBLIC_APP}?view=app&verify={time.time_ns()}", wait_until="networkidle")
        mobile.locator("[data-service-shell]").wait_for(state="visible")
        mobile_state = mobile.evaluate(
            """() => ({
              side:getComputedStyle(document.querySelector('.svc-side')).display,
              aside:getComputedStyle(document.querySelector('.svc-aside')).display,
              nav:getComputedStyle(document.querySelector('.svc-mobile-nav')).display,
              progress:Boolean(document.querySelector('[data-progress-dashboard]')),
              scroll:document.documentElement.scrollWidth,
              view:innerWidth
            })"""
        )
        checks.append(
            (
                "390px 고객 모바일 탐색 전환",
                mobile_state["side"] == "none"
                and mobile_state["aside"] == "none"
                and mobile_state["nav"] == "grid"
                and not mobile_state["progress"],
            )
        )
        checks.append(("390px 고객 모바일 가로 넘침 없음", mobile_state["scroll"] <= mobile_state["view"] + 1))
        mobile.close()

        for width in (1280, 390):
            page = browser.new_page(viewport={"width": width, "height": 900 if width > 390 else 844})
            page.goto(f"{PUBLIC_DASHBOARD}?verify={time.time_ns()}", wait_until="networkidle")
            dashboard_state = page.evaluate(
                """() => ({
                  marker:Boolean(document.querySelector('[data-progress-dashboard]')),
                  service:Boolean(document.querySelector('[data-service-link]')),
                  scroll:document.documentElement.scrollWidth,
                  view:innerWidth
                })"""
            )
            checks.append(
                (
                    f"{width}px 별도 개발 대시보드",
                    dashboard_state["marker"]
                    and dashboard_state["service"]
                    and dashboard_state["scroll"] <= dashboard_state["view"] + 1,
                )
            )
            page.close()
        browser.close()

    failed = [name for name, ok in checks if not ok]
    payload = {
        "schema": "FreeFlexVPNPublicServiceEvidenceV2",
        "measured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "public_url": PUBLIC_APP,
        "service_version": "service-ui-v3",
        "app_bytes": len(app_raw),
        "app_sha256": hashlib.sha256(app_raw).hexdigest().upper(),
        "dashboard_url": PUBLIC_DASHBOARD,
        "dashboard_bytes": len(dashboard_raw),
        "dashboard_sha256": hashlib.sha256(dashboard_raw).hexdigest().upper(),
        "qr_url": PUBLIC_QR,
        "qr_decoded_payload": qr_value,
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed": failed,
        "contains_sensitive_data": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    print(f"RESULT: {len(checks) - len(failed)}/{len(checks)} passed")
    print(f"증거: {output}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
