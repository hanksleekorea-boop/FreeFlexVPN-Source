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
    dashboard = (deploy / "development-dashboard.html").read_text(encoding="utf-8")
    service_shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    support = [path for path in deploy.glob("*.html") if path.name not in {"index.html", "app.html", "development-dashboard.html"}]
    checks: list[tuple[str, bool]] = []

    def check(label: str, passed: bool) -> None:
        checks.append((label, bool(passed)))

    check("밝은 소비자 서비스 랜딩", "color-scheme:light" in index and "개발 진행 중" not in index)
    check("랜딩 주요 탐색 4개", all(f'href="#{name}"' in index for name in ("moments", "wallet", "how", "privacy")))
    check("빠른 서비스 메뉴 5개", index.count('class="quick-link"') == 5)
    check("고객 앱 PC 3열 구조", "grid-template-columns:230px minmax(0,1fr) 300px" in app)
    check("고객 앱 빠른 실행 영역", 'class="svc-aside"' in app and "빠른 실행" in app)
    service_pages = [index, app, *(path.read_text(encoding="utf-8") for path in support)]
    check("고객 서비스와 개발 대시보드 분리", len(service_pages) == 8 and all('data-progress-dashboard' not in page for page in service_pages))
    check(
        "별도 개발 대시보드와 서비스 링크",
        'data-progress-dashboard' in dashboard and 'data-dashboard-page' in dashboard and dashboard.count('data-service-link') >= 2 and 'href="development-dashboard.html"' in index and 'href="development-dashboard.html"' in app,
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
    check("음성 대조: 고객 앱에 개발 대시보드 삽입 감지", 'data-progress-dashboard' in app.replace('data-service-shell', 'data-service-shell data-progress-dashboard', 1))
    check("음성 대조: 별도 대시보드 제거 감지", 'data-progress-dashboard' not in dashboard.replace('data-progress-dashboard', 'data-removed-dashboard', 1))

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
              return {side:side.width,main:main.width,aside:aside.width,scroll:document.documentElement.scrollWidth,view:innerWidth,progress:Boolean(progress)};
            }"""
        )
        check("PC 실제 3열 표시", columns["side"] >= 200 and columns["main"] >= 650 and columns["aside"] >= 280)
        check("PC 가로 넘침 없음", columns["scroll"] <= columns["view"] + 1)
        check("PC 고객 앱에는 개발 대시보드 없음", columns["progress"] is False)
        desktop.goto(f"{base}/development-dashboard.html")
        dashboard_state = desktop.evaluate(
            """() => ({marker:Boolean(document.querySelector('[data-progress-dashboard]')),service:Boolean(document.querySelector('[data-service-link]')),scroll:document.documentElement.scrollWidth,view:innerWidth})"""
        )
        check("PC 별도 개발 대시보드 표시", dashboard_state["marker"] and dashboard_state["service"])
        check("PC 대시보드 가로 넘침 없음", dashboard_state["scroll"] <= dashboard_state["view"] + 1)
        desktop.goto(f"{base}/app.html#usage")
        usage_view = desktop.locator('[data-svc-view="usage"].active')
        usage_view.wait_for(state="visible")
        check("주소로 사용량 바로가기", usage_view.is_visible())
        desktop.goto(f"{base}/app.html#locations")
        travel_country = desktop.locator('[data-svc-travel-country]')
        travel_country.wait_for(state="visible")
        travel_country.select_option("thailand")
        travel_copy = desktop.locator('[data-svc-travel-check]').text_content() or ""
        check("PC 여행지는 이 기기에만 기록", "태국" in travel_copy and "실제 경로와 현지 규칙은 확인 전입니다." in travel_copy)
        desktop.locator('[data-svc-travel-favorite]').click()
        travel_local = desktop.locator('[data-svc-travel-local-copy]').text_content() or ""
        check("PC 여행 추천은 근거 전까지 꺼짐", "추천 꺼짐" in travel_local)
        desktop.goto(f"{base}/app.html#account")
        network_button = desktop.locator('[data-svc-public-network]')
        network_button.wait_for(state="visible")
        network_button.click()
        network_copy = desktop.locator('[data-svc-network-guide]').text_content() or ""
        check("PC 공용망 안내는 보호 상태를 과장하지 않음", "실제 보호 상태는 확인 전입니다." in network_copy and "보호됨" not in network_copy)
        desktop.evaluate("window.dispatchEvent(new Event('offline'))")
        offline_copy = desktop.locator('[data-svc-network-guide]').text_content() or ""
        check("PC 망 끊김 안내는 직접 확인을 요구", "보호 여부를 판단하지 않습니다." in offline_copy and "WireGuard 앱" in offline_copy)
        handoff_qr = desktop.locator('[data-svc-handoff-qr]')
        handoff_qr.wait_for(state="visible")
        check("PC 휴대폰 이어보기 QR 표시", handoff_qr.evaluate("image => image.complete && image.naturalWidth > 0"))
        desktop.locator('[data-svc-ios-guide]').click()
        ios_copy = desktop.locator('[data-svc-handoff-guide]').text_content() or ""
        check("PC iPhone 안내는 실기기 검증 전을 표시", "실제 iPhone에서 아직 검증 전입니다." in ios_copy)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{base}/app.html")
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
        check("모바일 전용 탐색 전환", mobile_state["side"] == "none" and mobile_state["aside"] == "none" and mobile_state["nav"] == "grid")
        check("모바일 고객 앱에는 개발 대시보드 없음", mobile_state["progress"] is False)
        check("모바일 390px 가로 넘침 없음", mobile_state["scroll"] <= mobile_state["view"] + 1)
        mobile.goto(f"{base}/development-dashboard.html")
        mobile_dashboard = mobile.evaluate("""() => ({marker:Boolean(document.querySelector('[data-progress-dashboard]')),service:Boolean(document.querySelector('[data-service-link]')),scroll:document.documentElement.scrollWidth,view:innerWidth})""")
        check("모바일 별도 개발 대시보드·서비스 링크", mobile_dashboard["marker"] and mobile_dashboard["service"] and mobile_dashboard["scroll"] <= mobile_dashboard["view"] + 1)
        mobile.goto(f"{base}/app.html#account")
        mobile.locator('[data-svc-always-on-guide]').wait_for(state="visible")
        check("모바일 망 전환 안내 도달 가능", mobile.locator('[data-svc-always-on-guide]').is_visible())
        mobile.locator('[data-svc-handoff-qr]').wait_for(state="visible")
        check("모바일 휴대폰 이어보기 도달 가능", mobile.locator('[data-svc-handoff-qr]').is_visible())
        mobile.goto(f"{base}/app.html#locations")
        mobile.locator('[data-svc-travel-country]').wait_for(state="visible")
        check("모바일 여행 준비 도달 가능", mobile.locator('[data-svc-travel-country]').is_visible())
        browser.close()

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"서비스 UI v3 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
