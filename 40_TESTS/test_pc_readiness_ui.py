#!/usr/bin/env python3
"""실제 Chromium에서 PC 점검·가린 진단·읽기 설정 복구 UI를 검증한다."""
from __future__ import annotations

import contextlib
import json
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
import build_web_assets

build_web_assets.build()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


@contextlib.contextmanager
def local_server():
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT / "30_DEPLOY"), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


checks: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    checks.append((label, bool(ok), detail))


with local_server() as base, sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(10_000)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base}/app.html?view=app")
    page.locator('[data-svc-go="account"]').first.dispatch_event("click")
    panel = page.locator("[data-pc-readiness]")
    check("PC 점검 패널 표시", panel.is_visible())
    check("로컬 보안·온라인만 자동 통과", page.locator('[data-pc-check][data-state="pass"]').count() == 2, panel.inner_text())
    page.evaluate("localStorage.setItem('freeflex-pc-readiness-v1',JSON.stringify({recoveryDrill:true}))")
    page.evaluate("window.dispatchEvent(new Event('online'))")
    recovery = page.locator('[data-pc-confirm="recovery-drill"]')
    check("보호 전 저장값으로 복구 통과 불가", recovery.is_disabled() and not recovery.is_checked())
    page.locator('[data-pc-confirm="wireguard-client"]').check()
    page.locator('[data-pc-confirm="profile-import"]').check()
    check("자가 확인을 별도 상태로 표시", page.locator('[data-pc-check][data-state="self_reported"]').count() == 2)
    check("자가 확인 뒤에도 후보 아님", "4 / 7 · 준비 중" in page.locator('[data-pc-readiness-badge]').inner_text())
    with page.expect_download() as info:
        page.locator("[data-pc-download-diagnostic]").click()
    diagnostic = json.loads(pathlib.Path(info.value.path()).read_text(encoding="utf-8"))
    check("가린 진단 다운로드", diagnostic["schema"] == "freeflex-pc-diagnostic-v1")
    check("진단 자동 전송 없음", diagnostic["privacy"]["automaticallyTransmitted"] is False)
    check("진단 민감 필드 없음", set(diagnostic) == {"schema", "generatedAt", "browserFamily", "platformFamily", "standalone", "apiMode", "protectionState", "checks", "privacy"})
    page.locator('[data-svc-text-size="large"]').click()
    page.locator('[data-svc-contrast]').click()
    page.locator('button[data-svc-pc-focus]').click()
    with page.expect_download() as info:
        page.locator("[data-pc-export-preferences]").click()
    backup = json.loads(pathlib.Path(info.value.path()).read_text(encoding="utf-8"))
    check("읽기 설정만 백업", backup == {"schema": "freeflex-pc-preferences-v1", "accessibility": {"large": True, "contrast": True}, "focusMode": True}, str(backup))
    restored = {"schema": "freeflex-pc-preferences-v1", "accessibility": {"large": False, "contrast": False}, "focusMode": False, "ignored": "secret"}
    page.locator('[data-pc-import-preferences]').set_input_files({"name": "preferences.json", "mimeType": "application/json", "buffer": json.dumps(restored).encode("utf-8")})
    page.wait_for_function("document.documentElement.dataset.textSize === 'normal' && document.documentElement.dataset.highContrast === 'false' && document.querySelector('[data-service-shell]').dataset.svcPcFocus === 'false'")
    check("복원 즉시 화면 반영", page.get_attribute("html", "data-text-size") == "normal" and page.get_attribute("html", "data-high-contrast") == "false" and page.get_attribute("[data-service-shell]", "data-svc-pc-focus") == "false")
    before = page.evaluate("localStorage.getItem('freeflex-accessibility-v1')")
    page.locator('[data-pc-import-preferences]').set_input_files({"name": "bad.json", "mimeType": "application/json", "buffer": b'{"schema":"wrong"}'})
    check("잘못된 백업은 기존 설정 보존", page.evaluate("localStorage.getItem('freeflex-accessibility-v1')") == before)
    check("브라우저 오류 0", not errors, "; ".join(errors))
    mobile = context.new_page()
    mobile.set_viewport_size({"width": 390, "height": 844})
    mobile.goto(f"{base}/app.html?view=app")
    mobile.locator('[data-svc-go="account"]').last.dispatch_event("click")
    check("모바일에서는 PC 전용 패널 숨김", mobile.locator("[data-pc-readiness]").is_hidden())
    browser.close()

failed = [(label, detail) for label, ok, detail in checks if not ok]
if failed:
    for label, detail in failed:
        print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"PC 출시 점검 UI {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"PC 출시 점검 UI {len(checks)}/{len(checks)} 통과")
