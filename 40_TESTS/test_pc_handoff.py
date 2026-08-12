#!/usr/bin/env python3
"""PC-3 상시 QR의 실제 디코드·정본 링크·모바일 비노출과 음성 대조."""
from __future__ import annotations

import base64
import contextlib
import pathlib
import re
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "30_DEPLOY" / "app.html"
CANONICAL = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html"
checks: list[tuple[str, bool]] = []


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None: pass


@contextlib.contextmanager
def server_for(directory: pathlib.Path):
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)


def handoff_contract(source: str) -> tuple[bool, str]:
    match = re.search(r'<aside class="pc-handoff".*?<img src="data:image/png;base64,([^"]+)".*?<a href="([^"]+)"', source, re.S)
    if not match: return False, ""
    image = cv2.imdecode(np.frombuffer(base64.b64decode(match.group(1)), dtype=np.uint8), cv2.IMREAD_COLOR)
    decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return bool(points is not None and decoded == match.group(2) == CANONICAL), decoded


source = APP.read_text(encoding="utf-8")
valid, decoded = handoff_contract(source)
checks.append(("내장 QR 실제 디코드", bool(decoded)))
checks.append(("QR·링크·정본 주소 일치", valid))
checks.append(("단일 HTML QR 내장", "__APP_QR_B64__" not in source and "data:image/png;base64," in source))

with sync_playwright() as pw, server_for(ROOT / "30_DEPLOY") as base:
    browser = pw.chromium.launch(); pc = browser.new_page(viewport={"width": 1280, "height": 900})
    pc.goto(f"{base}/app.html?view=app&review=1")
    checks.append(("PC 홈 상시 QR 가시", pc.locator(".pc-handoff").evaluate("el=>getComputedStyle(el).display") == "grid"))
    checks.append(("PC 정본 링크 도달", pc.get_attribute(".pc-handoff a", "href") == CANONICAL))
    checks.append(("PC QR 이미지 렌더", pc.locator(".pc-handoff img").evaluate("el=>el.complete&&el.naturalWidth>0")))
    mobile = browser.new_page(viewport={"width": 390, "height": 844}); mobile.goto(f"{base}/app.html?view=app&review=1")
    checks.append(("모바일 기존 화면에서 PC QR 숨김", mobile.locator(".pc-handoff").evaluate("el=>getComputedStyle(el).display") == "none"))
    browser.close()

broken = source.replace(CANONICAL, "https://example.invalid/wrong", 1)
broken_valid, _ = handoff_contract(broken)
checks.append(("음성 대조: 링크 불일치 거부", not broken_valid))

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"pc_handoff_test 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
