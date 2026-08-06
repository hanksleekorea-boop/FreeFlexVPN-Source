#!/usr/bin/env python3
"""PC-1 1280/1920 와이드 렌더, 1024 미만 무변화, CSS 음성 대조."""
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


def column_count(page) -> int:
    value = page.locator('[data-screen="home"] .moment-grid').evaluate(
        "el=>getComputedStyle(el).gridTemplateColumns"
    )
    return len([part for part in value.split(" ") if part])


with sync_playwright() as pw, server_for(ROOT / "30_DEPLOY") as base:
    browser = pw.chromium.launch()
    for width in (1280, 1920):
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(f"{base}/app.html?view=app&review=1")
        page.wait_for_function("document.documentElement.dataset.pcLayout === 'wide'")
        desk_display = page.locator(".pc-desk-banner").evaluate("el=>getComputedStyle(el).display")
        grid = page.locator(".pc-home-grid").bounding_box()
        checks.append((f"{width}px PC 와이드 모드", page.locator("body.pc-wide").count() == 1))
        checks.append((f"{width}px 책상형 홈 가시", desk_display == "flex" and bool(grid and grid["width"] > 700)))
        checks.append((f"{width}px 갤러리 4열", column_count(page) == 4))
        page.close()

    tablet = browser.new_page(viewport={"width": 900, "height": 900})
    tablet.goto(f"{base}/app.html?view=app&review=1")
    tablet.wait_for_function("document.documentElement.dataset.pcLayout === 'mobile'")
    checks.append(("900px PC CSS 미적용", tablet.locator("body.pc-wide").count() == 0))
    checks.append(("900px 기존 갤러리 2열", column_count(tablet) == 2))
    checks.append(("900px PC 배너 숨김", tablet.locator(".pc-desk-banner").evaluate("el=>getComputedStyle(el).display") == "none"))
    tablet.close()

    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto(f"{base}/app.html?view=app&review=1")
    mobile.wait_for_function("document.documentElement.dataset.pcLayout === 'mobile'")
    phone = mobile.locator(".phone").bounding_box()
    checks.append(("390px 기존 전체 화면", bool(phone and abs(phone["width"] - 390) < 3 and abs(phone["height"] - 844) < 3)))
    checks.append(("390px 기존 갤러리 2열", column_count(mobile) == 2))
    checks.append(("390px PC 배너 숨김", mobile.locator(".pc-desk-banner").evaluate("el=>getComputedStyle(el).display") == "none"))
    mobile.close(); browser.close()

with tempfile.TemporaryDirectory(prefix="freeflex-pc1-broken-") as tmp, sync_playwright() as pw:
    broken_dir = pathlib.Path(tmp)
    source = APP.read_text(encoding="utf-8")
    marker = "@media(min-width:1024px)"
    assert marker in source, "PC-1 negative-control mutation point missing"
    (broken_dir / "broken.html").write_text(source.replace(marker, "@media(min-width:2048px)", 1), encoding="utf-8")
    with server_for(broken_dir) as broken_base:
        browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{broken_base}/broken.html?view=app&review=1")
        page.wait_for_function("document.documentElement.dataset.pcLayout === 'wide'")
        checks.append(("음성 대조: PC CSS 제거 감지", column_count(page) != 4 and page.locator(".pc-desk-banner").evaluate("el=>getComputedStyle(el).display") == "none"))
        browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"pc_viewport_test 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
