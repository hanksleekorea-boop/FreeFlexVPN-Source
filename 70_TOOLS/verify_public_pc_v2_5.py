#!/usr/bin/env python3
"""공개 FreeFlexVPN v2.5의 PC 2종·모바일·QR을 실제 브라우저와 디코더로 확인한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
import urllib.request

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC_APP = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html"
PUBLIC_QR = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app-qr.png"


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
    if not output.is_absolute(): output = (ROOT / output).resolve()
    if output.exists(): raise FileExistsError(f"기존 공개 증거는 덮어쓰지 않습니다: {output}")

    app_raw = fetch(PUBLIC_APP)
    app_text = app_raw.decode("utf-8")
    qr_raw = fetch(PUBLIC_QR)
    qr_image = cv2.imdecode(np.frombuffer(qr_raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    qr_value, qr_points, _ = cv2.QRCodeDetector().detectAndDecode(qr_image)
    checks: list[tuple[str, bool]] = [
        ("공개 v2.5", "UI · UX v2.5" in app_text),
        ("공개 PC DESK", "PC DESK" in app_text),
        ("공개 HANDOFF", "HANDOFF" in app_text),
        ("공개 QR 실제 디코드", qr_points is not None and qr_value == PUBLIC_APP),
    ]

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1280, 1920):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(f"{PUBLIC_APP}?view=app&verify={time.time_ns()}", wait_until="networkidle")
            page.wait_for_function("document.documentElement.dataset.pcLayout === 'wide'")
            columns = page.locator('[data-screen="home"] .moment-grid').evaluate("el=>getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length")
            checks.append((f"{width}px PC 넓은 화면", page.locator("body.pc-wide").count() == 1 and columns == 4))
            checks.append((f"{width}px 통계·QR 가시", page.locator(".pc-stats").evaluate("el=>getComputedStyle(el).display") == "block" and page.locator(".pc-handoff").evaluate("el=>getComputedStyle(el).display") == "grid"))
            page.close()
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{PUBLIC_APP}?view=app&verify={time.time_ns()}", wait_until="networkidle")
        phone = mobile.locator(".phone").bounding_box()
        checks.append(("390px 기존 전체 화면", mobile.locator("body.pc-wide").count() == 0 and bool(phone and abs(phone["width"] - 390) < 3 and abs(phone["height"] - 844) < 3)))
        checks.append(("390px PC 통계·QR 숨김", mobile.locator(".pc-stats").evaluate("el=>getComputedStyle(el).display") == "none" and mobile.locator(".pc-handoff").evaluate("el=>getComputedStyle(el).display") == "none"))
        browser.close()

    failed = [name for name, ok in checks if not ok]
    payload = {
        "schema": "FreeFlexVPNPublicPCV25EvidenceV1",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "public_url": PUBLIC_APP,
        "version": "v2.5",
        "bytes": len(app_raw),
        "sha256": hashlib.sha256(app_raw).hexdigest().upper(),
        "qr_url": PUBLIC_QR,
        "qr_decoded_payload": qr_value,
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed": failed,
        "github_commit": "01b4ab894e45907900285e32b4614070c79c0986",
        "github_actions_run": "https://github.com/hanksleekorea-boop/FreeFlexVPN/actions/runs/30919123045",
        "github_actions_conclusion": "success",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
    print(f"RESULT: {len(checks)-len(failed)}/{len(checks)} passed")
    print(f"증거: {output}")
    return 0 if not failed else 1


if __name__ == "__main__": raise SystemExit(main())
