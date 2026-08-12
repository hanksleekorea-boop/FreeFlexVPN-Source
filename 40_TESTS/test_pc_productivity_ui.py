#!/usr/bin/env python3
"""PC 생산성 제어판·키보드 이동·입력 보호의 화면 회귀 검사."""
from __future__ import annotations

import contextlib
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "20_SRC" / "html_templates" / "service_shell.html"
CSS = ROOT / "20_SRC" / "html_templates" / "service_shell.css"
APP = ROOT / "30_DEPLOY" / "app.html"
checks: list[tuple[str, bool]] = []


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextlib.contextmanager
def server_for(directory: pathlib.Path):
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


source = SOURCE.read_text(encoding="utf-8")
contract_source = source + CSS.read_text(encoding="utf-8")
required = (
    'data-svc-pc-help',
    'data-svc-pc-help-panel',
    'PC 빠른 제어',
    'data-svc-pc-focus',
    '본문으로 건너뛰기',
    "const pcPages={1:'home',2:'locations',3:'usage',4:'account'}",
    "target.matches('input,textarea,select,[contenteditable=\"true\"]')",
    '.svc-skip-link',
    '.svc-pc-help',
)
checks.append(("PC 생산성 구성 존재", all(marker in contract_source for marker in required)))
checks.append(("음성 대조: 단축키 도움말 제거 감지", 'data-svc-pc-help-panel' not in source.replace('data-svc-pc-help-panel', 'removed')))
checks.append(("음성 대조: 입력 보호 제거 감지", "target.matches('input,textarea,select,[contenteditable=\"true\"]')" not in source.replace("target.matches('input,textarea,select,[contenteditable=\"true\"]')", "false", 1)))

with sync_playwright() as pw, server_for(ROOT / "30_DEPLOY") as base:
    browser = pw.chromium.launch()
    desktop = browser.new_page(viewport={"width": 1440, "height": 980})
    desktop.goto(f"{base}/app.html")
    help_button = desktop.locator('[data-svc-pc-help]')
    help_panel = desktop.locator('[data-svc-pc-help-panel]')
    checks.append(("PC 도움말 버튼 표시", help_button.is_visible()))
    help_button.click()
    checks.append(("PC 제어판 클릭으로 열림", help_panel.is_visible() and 'PC 빠른 제어' in help_panel.inner_text()))
    desktop.keyboard.press("Escape")
    checks.append(("Esc로 PC 제어판 닫힘", help_panel.is_hidden()))
    desktop.keyboard.press("?")
    checks.append(("물음표 단축키로 도움말 열림", help_panel.is_visible()))
    desktop.keyboard.press("Escape")
    focus_toggle = desktop.locator('button[data-svc-pc-focus]')
    focus_toggle.click()
    checks.append(("집중 보기로 PC 보조 영역 숨김", desktop.locator('[data-service-shell]').get_attribute('data-svc-pc-focus') == 'true' and desktop.locator('.svc-side').evaluate("el=>getComputedStyle(el).display") == 'none'))
    desktop.keyboard.press("f")
    checks.append(("F 키로 집중 보기 해제", desktop.locator('[data-service-shell]').get_attribute('data-svc-pc-focus') == 'false'))
    desktop.keyboard.press("2")
    checks.append(("숫자 키 위치 화면 이동", desktop.locator('[data-svc-view="locations"].active').is_visible()))
    travel = desktop.locator('[data-svc-travel-country]')
    travel.focus()
    desktop.keyboard.press("3")
    checks.append(("입력 중 숫자 단축키 차단", desktop.locator('[data-svc-view="locations"].active').is_visible()))
    desktop.goto(f"{base}/app.html")
    desktop.locator('.svc-skip-link').focus()
    checks.append(("본문 건너뛰기 키보드 도달", desktop.locator('.svc-skip-link').evaluate("el=>document.activeElement===el")))
    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto(f"{base}/app.html")
    checks.append(("모바일에서는 PC 도움말 숨김", mobile.locator('[data-svc-pc-help]').evaluate("el=>getComputedStyle(el).display") == 'none'))
    checks.append(("모바일 가로 넘침 없음", mobile.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")))
    # 1440px PC 화면을 브라우저 200% 확대했을 때처럼, CSS 기준 폭이 약 720px인
    # 환경에서도 핵심 행동이 남고 가로 넘침이 없어야 한다. 실제 OS/보조기술
    # 검증을 대체하지는 않지만, 확대에서 가장 흔한 레이아웃 회귀를 자동으로 막는다.
    zoomed = browser.new_page(viewport={"width": 720, "height": 900})
    zoomed.goto(f"{base}/app.html")
    checks.append(("200% 상당 폭에서 가로 넘침 없음", zoomed.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")))
    checks.append(("200% 상당 폭에서 하단 메뉴 표시", zoomed.locator('.svc-mobile-nav').is_visible()))
    zoomed.get_by_role("button", name="내 정보").click()
    checks.append(("200% 상당 폭에서 핵심 화면 이동", zoomed.locator('[data-svc-view="account"].active').is_visible()))
    zoomed.locator('.svc-skip-link').focus()
    checks.append(("200% 상당 폭에서 건너뛰기 링크 도달", zoomed.locator('.svc-skip-link').evaluate("el=>document.activeElement===el")))
    browser.close()

failed = [name for name, passed in checks if not passed]
for name, passed in checks:
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
if failed:
    raise SystemExit(f"PC 생산성 UI 실패: {', '.join(failed)}")
print(f"PC 생산성 UI: {len(checks)}/{len(checks)} passed")
