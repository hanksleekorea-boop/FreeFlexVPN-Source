#!/usr/bin/env python3
"""PC-1 키보드 보호 확인·화면 이동·입력 보호와 키 핸들러 음성 대조."""
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


def active_screen(page) -> str:
    return page.locator("section.screen.active").get_attribute("data-screen") or ""


with sync_playwright() as pw, server_for(ROOT / "30_DEPLOY") as base:
    browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{base}/app.html?view=app&review=1")
    page.locator("body").press("Space")
    checks.append(("Space 보호 확인 실행", page.get_attribute("#statusCard", "data-connection-state") == "checking"))
    page.wait_for_function("document.querySelector('#statusCard').dataset.connectionState === 'limited'")
    checks.append(("Space 실제 상태 기록", page.get_attribute("#statusCard", "data-connection-state") == "limited" and "가동 서버" in page.locator("#connectionDetail").inner_text()))
    page.locator("body").press("Enter")
    checks.append(("Enter 보호 확인 실행", page.get_attribute("#statusCard", "data-connection-state") == "checking"))
    page.wait_for_function("document.querySelector('#statusCard').dataset.connectionState === 'limited'")
    page.locator("body").press("ArrowRight")
    checks.append(("오른쪽 방향키 다음 화면", active_screen(page) == "moments"))
    page.locator("body").press("ArrowLeft")
    checks.append(("왼쪽 방향키 이전 화면", active_screen(page) == "home"))
    page.locator("body").press("?")
    checks.append(("단축키 도움말", "Space / Enter" in page.locator("#toast").inner_text()))
    page.evaluate("go('moments')")
    search = page.locator("#momentSearchInput"); search.focus(); search.press("Space")
    checks.append(("입력 중 단축키 차단", active_screen(page) == "moments" and page.get_attribute("#statusCard", "data-connection-state") == "limited"))
    browser.close()

with tempfile.TemporaryDirectory(prefix="freeflex-keyboard-broken-") as tmp, sync_playwright() as pw:
    broken_dir = pathlib.Path(tmp)
    source = APP.read_text(encoding="utf-8")
    marker = "if((event.key===' '||event.key==='Enter')&&screens[activeIndex]?.dataset.screen==='home')"
    assert marker in source, "keyboard negative-control mutation point missing"
    (broken_dir / "broken.html").write_text(source.replace(marker, "if(false&&screens[activeIndex]?.dataset.screen==='home')", 1), encoding="utf-8")
    with server_for(broken_dir) as broken_base:
        browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{broken_base}/broken.html?view=app&review=1"); page.locator("body").press("Space")
        checks.append(("음성 대조: 키 핸들러 제거 감지", page.get_attribute("#statusCard", "data-connection-state") == "disconnected"))
        browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"keyboard_test 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
