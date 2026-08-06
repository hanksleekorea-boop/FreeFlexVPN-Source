#!/usr/bin/env python3
"""PC·모바일 앱 모드의 실제 렌더와 저장 실패·깨진 CSS 음성 대조."""
from __future__ import annotations

import contextlib
import pathlib
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "30_DEPLOY" / "app.html"
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


with sync_playwright() as pw, server_for(ROOT / "30_DEPLOY") as base:
    browser = pw.chromium.launch()
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()
    page.goto(f"{base}/app.html?view=app&app_layout_probe=1&review=1")
    page.wait_for_function("document.documentElement.dataset.appLayoutSafe")
    phone = page.locator(".phone").bounding_box()
    checks.append(("PC 앱 모드 자동 진입", page.locator("body.app-mode").count() == 1))
    checks.append(("PC 실제 레이아웃 PASS", page.get_attribute("html", "data-app-layout-safe") == "pass"))
    checks.append(("PC 작업 영역 520px 이상", bool(phone and phone["width"] >= 520)))
    checks.append(("설계 노트 숨김", page.locator(".notes").evaluate("el=>getComputedStyle(el).display") == "none"))
    checks.append(("앱 모드 토글 상태", page.get_attribute("#appModeToggle", "aria-pressed") == "true"))
    page.locator("#appModeToggle").click()
    checks.append(("설계 보기 되돌림", page.locator("body.app-mode").count() == 0 and page.get_attribute("#appModeToggle", "aria-pressed") == "false"))
    page.locator("#appModeToggle").click()
    checks.append(("앱 모드 선택 보존", page.evaluate("localStorage.getItem('ffvpn-app-mode')") == "1"))
    context.close()

    mobile = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
    mobile.goto(f"{base}/app.html?view=app&app_layout_probe=1&review=1")
    mobile.wait_for_function("document.documentElement.dataset.appLayoutSafe")
    mobile_phone = mobile.locator(".phone").bounding_box()
    checks.append(("모바일 앱 모드 PASS", mobile.get_attribute("html", "data-app-layout-safe") == "pass"))
    checks.append(("모바일 전체 화면", bool(mobile_phone and abs(mobile_phone["width"] - 390) < 3 and abs(mobile_phone["height"] - 844) < 3)))
    mobile.context.close()

    blocked_context = browser.new_context(viewport={"width": 1400, "height": 900})
    blocked_context.add_init_script("Storage.prototype.getItem=()=>{throw new Error('blocked')};Storage.prototype.setItem=()=>{throw new Error('blocked')};")
    blocked = blocked_context.new_page(); errors: list[str] = []
    blocked.on("pageerror", lambda error: errors.append(str(error)))
    blocked.goto(f"{base}/app.html?view=app&app_layout_probe=1&review=1")
    blocked.wait_for_function("document.documentElement.dataset.appLayoutSafe")
    checks.append(("저장 차단에도 앱 모드 유지", blocked.locator("body.app-mode").count() == 1 and not errors))
    blocked_context.close(); browser.close()

with tempfile.TemporaryDirectory(prefix="freeflex-broken-") as tmp, sync_playwright() as pw:
    broken_dir = pathlib.Path(tmp)
    source = APP.read_text(encoding="utf-8")
    marker = "body.pc-wide .phone{width:100%"
    assert marker in source, "desktop negative-control mutation point missing"
    (broken_dir / "broken.html").write_text(source.replace(marker, "body.pc-wide .phone{width:min(100%,390px)", 1), encoding="utf-8")
    with server_for(broken_dir) as broken_base:
        browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"{broken_base}/broken.html?view=app&app_layout_probe=1&review=1")
        page.wait_for_function("document.documentElement.dataset.appLayoutSafe")
        checks.append(("음성 대조: 좁은 PC 레이아웃 거부", page.get_attribute("html", "data-app-layout-safe") == "fail"))
        browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"PC 앱 모드 검사 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
