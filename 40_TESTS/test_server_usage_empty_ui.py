#!/usr/bin/env python3
"""F1-1: 운영 자료 없음·오류·오래됨이 가짜 수치 없이 보이는지 검사한다."""
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
    app = (deploy / "app.html").read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = []
    def check(label: str, passed: bool) -> None:
        checks.append((label, bool(passed)))

    check("운영 자료 출처·측정시각·가용성·혼잡도", all(token in app for token in ("data-svc-operations-source", "data-svc-operations-measured", "data-svc-operations-availability", "data-svc-operations-congestion")))
    check("사용량 빈 상태·소진 예상", all(token in app for token in ("data-svc-usage-empty", "data-svc-usage-forecast", "계산 불가")))
    check("가짜 7일 막대 제거", "svc-usage-bar" not in app)
    check("오래된 자료 처리", "state: \"stale\"" in app and "유효 기간을 지났습니다" in app)
    shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
    check("음성 대조: 출처 제거 감지", "data-svc-operations-source" not in shell.replace("data-svc-operations-source", "data-removed-source", 1))

    with server_for(deploy) as base, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980})
        page.goto(f"{base}/app.html#locations")
        check("자료 미연결은 판정 불가", page.locator("[data-svc-operations-state='unconfigured']").is_visible() and page.locator("[data-svc-operations-availability]").inner_text() == "판정 불가")
        page.get_by_role("button", name="사용량", exact=True).first.click()
        check("사용량 미연결은 소진 예상 없음", page.locator("[data-svc-usage-forecast]").inner_text() == "계산 불가")
        state = page.evaluate("""() => {
          const copy=document.querySelector('[data-svc-operations-copy]');
          const source=document.querySelector('[data-svc-operations-source]');
          copy.textContent='서버 자료의 갱신 시각이 없거나 유효 기간을 지났습니다. 연결 가능 여부를 표시하지 않습니다.';
          source.textContent='서버 자료';
          document.querySelector('[data-svc-operations-state]').dataset.svcOperationsState='stale';
          return {state:document.querySelector('[data-svc-operations-state]').dataset.svcOperationsState,copy:copy.textContent,source:source.textContent};
        }""")
        check("오래된 자료는 연결 가능으로 바꾸지 않음", state["state"] == "stale" and "유효 기간" in state["copy"] and state["source"] == "서버 자료")
        browser.close()

    failed = [label for label, passed in checks if not passed]
    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {label}")
    print(f"F1-1 서버·사용량 빈 상태 UI {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
