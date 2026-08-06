#!/usr/bin/env python3
"""PC-2 책상형 3영역·대형 통계·정직한 미측정 상태와 음성 대조."""
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
    browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{base}/app.html?view=app&review=1")
    page.wait_for_function("document.documentElement.dataset.pcLayout === 'wide'")
    displays = [page.locator(selector).evaluate("el=>getComputedStyle(el).display") for selector in ('[data-screen="home"] .balance-card', ".pc-moments", ".pc-connection")]
    checks.append(("PC 홈 3영역 동시 가시", all(value != "none" for value in displays)))
    areas = page.locator(".pc-home-grid").evaluate("el=>getComputedStyle(el).gridTemplateAreas")
    checks.append(("1200px 이상 3열 책상 배치", '"balance moments connection"' in areas))
    checks.append(("대형 통계 패널 가시", page.locator(".pc-stats").evaluate("el=>getComputedStyle(el).display") == "block"))
    stats_text = page.locator(".pc-stats").inner_text()
    checks.append(("기간 비교 도달", "최근 7일" in stats_text and "이전 7일" in stats_text))
    checks.append(("미측정 정직 표기", "측정 없음" in stats_text and "계정 API" in stats_text))
    page.evaluate("document.getElementById('balanceValue').textContent='2.25'")
    page.wait_for_function("document.getElementById('pcBalanceValue').textContent === '2.25'")
    checks.append(("홈 잔액 통계 동기화", page.locator("#pcBalanceValue").inner_text() == "2.25"))
    page.locator("body").press("Space")
    page.wait_for_function("document.querySelector('#statusCard').dataset.connectionState === 'limited'")
    checks.append(("보호 판정 통계 동기화", page.locator("#pcProtectionValue").inner_text() == "일부 확인 불가"))
    browser.close()

with tempfile.TemporaryDirectory(prefix="freeflex-pc-home-broken-") as tmp, sync_playwright() as pw:
    broken_dir = pathlib.Path(tmp); source = APP.read_text(encoding="utf-8")
    marker = "body.pc-wide .pc-stats{display:block"
    assert marker in source, "PC-2 negative-control mutation point missing"
    (broken_dir / "broken.html").write_text(source.replace(marker, "body.pc-wide .pc-stats{display:none", 1), encoding="utf-8")
    with server_for(broken_dir) as broken_base:
        browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{broken_base}/broken.html?view=app&review=1")
        checks.append(("음성 대조: 통계 숨김 감지", page.locator(".pc-stats").evaluate("el=>getComputedStyle(el).display") == "none"))
        browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"pc_home_test 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
