#!/usr/bin/env python3
"""소비자 서비스급 v3 화면 구조와 반응형 품질을 고정한다."""
from __future__ import annotations

import contextlib
import http.server
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_web_assets  # noqa: E402


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        return


@contextlib.contextmanager
def server_for(directory: pathlib.Path):
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    with socketserver.TCPServer(("127.0.0.1", 0), factory) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            thread.join(timeout=2)


def main() -> None:
    build_web_assets.build()
    deploy = ROOT / "30_DEPLOY"
    index = (deploy / "index.html").read_text(encoding="utf-8")
    app = (deploy / "app.html").read_text(encoding="utf-8")
    service_shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    support = [path for path in deploy.glob("*.html") if path.name not in {"index.html", "app.html"}]
    checks: list[tuple[str, bool]] = []

    def check(label: str, passed: bool) -> None:
        checks.append((label, bool(passed)))

    check("밝은 소비자 서비스 랜딩", "color-scheme:light" in index and "개발 진행 중" not in index)
    check("랜딩 주요 탐색 4개", all(f'href="#{name}"' in index for name in ("moments", "wallet", "how", "privacy")))
    check("빠른 서비스 메뉴 5개", index.count('class="quick-link"') == 5)
    check("고객 앱 PC 3열 구조", "grid-template-columns:230px minmax(0,1fr) 300px" in app)
    check("고객 앱 빠른 실행 영역", 'class="svc-aside"' in app and "빠른 실행" in app)
    public_pages = [index, app, *(path.read_text(encoding="utf-8") for path in support)]
    check("공개 화면 8종 진행상황 대시보드", len(public_pages) == 8 and all('data-progress-dashboard' in page for page in public_pages))
    check(
        "진행상황 네 단계와 현재 단계",
        app.count('data-progress-step=') == 4 and 'data-progress-step="second-server"' in app and "현재: 두 번째 서버 준비" in app,
    )
    check(
        "Android 연결·재연결 확인 기록 보존",
        "2026-08-04 Android 연결·재연결 실기기 확인" in service_shell,
    )
    check(
        "현재 연결 상태 과장 금지",
        "data-svc-operations-availability>판정 불가" in service_shell and "현재 연결됨" not in service_shell,
    )
    check("보조 문서 밝은 기본값", len(support) == 6 and all('data-theme="light"' in path.read_text(encoding="utf-8") for path in support))
    check("음성 대조: 빠른 메뉴 제거 감지", index.replace('class="quick-link"', 'class="removed"', 1).count('class="quick-link"') != 5)
    check("음성 대조: 우측 실행 영역 제거 감지", 'class="svc-aside"' not in app.replace('class="svc-aside"', 'class="removed"', 1))
    check("음성 대조: 진행상황 대시보드 제거 감지", 'data-progress-dashboard' not in app.replace('data-progress-dashboard', 'data-removed-dashboard', 1))

    with server_for(deploy) as base, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        desktop = browser.new_page(viewport={"width": 1440, "height": 980})
        desktop.goto(f"{base}/app.html")
        columns = desktop.evaluate(
            """() => {
              const side=document.querySelector('.svc-side').getBoundingClientRect();
              const main=document.querySelector('.svc-main').getBoundingClientRect();
              const aside=document.querySelector('.svc-aside').getBoundingClientRect();
              const progress=document.querySelector('[data-progress-dashboard]');
              return {side:side.width,main:main.width,aside:aside.width,scroll:document.documentElement.scrollWidth,view:innerWidth,progress:progress?getComputedStyle(progress).position:null,steps:progress?.querySelectorAll('[data-progress-step]').length};
            }"""
        )
        check("PC 실제 3열 표시", columns["side"] >= 200 and columns["main"] >= 650 and columns["aside"] >= 280)
        check("PC 가로 넘침 없음", columns["scroll"] <= columns["view"] + 1)
        check("PC 진행상황 대시보드 고정 표시", columns["progress"] == "sticky" and columns["steps"] == 4)
        desktop.goto(f"{base}/app.html#usage")
        usage_view = desktop.locator('[data-svc-view="usage"].active')
        usage_view.wait_for(state="visible")
        check("주소로 사용량 바로가기", usage_view.is_visible())

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{base}/app.html")
        mobile_state = mobile.evaluate(
            """() => ({
              side:getComputedStyle(document.querySelector('.svc-side')).display,
              aside:getComputedStyle(document.querySelector('.svc-aside')).display,
              nav:getComputedStyle(document.querySelector('.svc-mobile-nav')).display,
              progress:getComputedStyle(document.querySelector('[data-progress-dashboard]')).position,
              steps:document.querySelectorAll('[data-progress-step]').length,
              scroll:document.documentElement.scrollWidth,
              view:innerWidth
            })"""
        )
        check("모바일 전용 탐색 전환", mobile_state["side"] == "none" and mobile_state["aside"] == "none" and mobile_state["nav"] == "grid")
        check("모바일 진행상황 대시보드 고정 표시", mobile_state["progress"] == "sticky" and mobile_state["steps"] == 4)
        check("모바일 390px 가로 넘침 없음", mobile_state["scroll"] <= mobile_state["view"] + 1)
        browser.close()

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"서비스 UI v3 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
