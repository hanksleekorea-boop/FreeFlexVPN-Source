#!/usr/bin/env python3
"""v2.6 고객용 서비스 UI, 4메뉴, 반응형, 내부 검토 분리를 검사한다."""
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
    app_text = (deploy / "app.html").read_text(encoding="utf-8")
    index_text = (deploy / "index.html").read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = []

    def check(label: str, passed: bool) -> None:
        checks.append((label, bool(passed)))

    shell_start = app_text.index('<section class="svc-shell"')
    shell_text = app_text[shell_start:]
    check("서비스 홈·4메뉴 정적 계약", all(token in shell_text for token in ('data-svc-view="home"', 'data-svc-view="locations"', 'data-svc-view="usage"', 'data-svc-view="account"', "무료 1GB로 시작")))
    check("고객 화면 알파·스토리보드 문구 0", not any(token in shell_text for token in ("ALPHA", "Storyboard", "Design rationale", "화면 14개")))
    check("가짜 잔액 금지", "확인 전" in shell_text and '<span data-svc-balance>1.00</span>' not in shell_text)
    check("검토 모드 분리", "query.get('review')==='1'" in app_text and "body.review-mode>.svc-shell" in app_text)
    check("정식 랜딩 계약", all(token in index_text for token in ("매달 내지 말고", "무료 1GB로 시작", "세 단계면 충분합니다", "상태 과장 없음")) and "개발 진행 중" not in index_text)
    themed = [path for path in deploy.glob("*.html") if path.name not in {"index.html", "app.html", "development-dashboard.html"}]
    check("보조 공개 페이지 6종 공통 서비스 디자인", len(themed) == 6 and all("data-freeflex-global-theme" in path.read_text(encoding="utf-8") for path in themed))

    with server_for(deploy) as base, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        desktop = browser.new_page(viewport={"width": 1440, "height": 980})
        desktop.goto(f"{base}/app.html")
        check("PC 고객 서비스 기본 노출", desktop.locator(".svc-shell").is_visible() and not desktop.locator("body>.page").is_visible())
        check("PC 4메뉴", desktop.locator(".svc-side [data-svc-go]").count() == 4)
        desktop.locator('.svc-side [data-svc-go="locations"]').click()
        check("위치 메뉴 실제 전환", desktop.locator('[data-svc-view="locations"].active').is_visible())
        desktop.locator('.svc-side [data-svc-go="home"]').click()
        desktop.get_by_role("button", name="무료 1GB로 시작", exact=True).click()
        check("연결 준비 안내창", desktop.locator("[data-svc-setup-panel]").is_visible() and desktop.get_by_role("button", name="닫기", exact=True).count() == 1)
        desktop.get_by_role("button", name="닫기", exact=True).click()
        desktop_metrics = desktop.evaluate("() => ({scroll:document.documentElement.scrollWidth,view:innerWidth})")
        check("PC 가로 넘침 0", desktop_metrics["scroll"] <= desktop_metrics["view"] + 1)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{base}/app.html")
        mobile_metrics = mobile.evaluate("() => ({scroll:document.documentElement.scrollWidth,view:innerWidth})")
        check("모바일 서비스·하단 4메뉴", mobile.locator(".svc-shell").is_visible() and mobile.locator(".svc-mobile-nav [data-svc-go]").count() == 4 and mobile.locator(".svc-mobile-nav").is_visible())
        check("모바일 가로 넘침 0", mobile_metrics["scroll"] <= mobile_metrics["view"] + 1)

        review = browser.new_page(viewport={"width": 1280, "height": 900})
        review.goto(f"{base}/app.html?review=1")
        check("내부 검토판 역접근", review.locator("body>.page").is_visible() and not review.locator(".svc-shell").is_visible())
        browser.close()

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"서비스 UI v2.6 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
