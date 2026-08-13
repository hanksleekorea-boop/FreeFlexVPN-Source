#!/usr/bin/env python3
"""390px Chromium에서 모바일 점검·오프라인 복구·PC 분리 UI를 검증한다."""
from __future__ import annotations

import contextlib
import json
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'20_SRC'))
import build_web_assets
build_web_assets.build()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,_format,*_args): pass


@contextlib.contextmanager
def local_server():
    factory=lambda *args,**kwargs:QuietHandler(*args,directory=str(ROOT/'30_DEPLOY'),**kwargs)
    server=ThreadingHTTPServer(('127.0.0.1',0),factory);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown();server.server_close();thread.join(timeout=5)


checks=[]
def check(label,ok,detail=''): checks.append((label,bool(ok),detail))


with local_server() as base,sync_playwright() as pw:
    browser=pw.chromium.launch();context=browser.new_context(accept_downloads=True,viewport={'width':390,'height':844},user_agent='Mozilla/5.0 (Linux; Android 15; Mobile) Chrome/138 Safari/537.36')
    page=context.new_page();page.set_default_timeout(10000);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'{base}/app.html?view=app');page.locator('[data-svc-go="account"]').last.dispatch_event('click')
    panel=page.locator('[data-mobile-readiness]')
    check('390px 모바일 패널 표시',panel.is_visible())
    check('PC 패널 숨김',page.locator('[data-pc-readiness]').is_hidden())
    check('보안·온라인 2종만 자동 통과',page.locator('[data-mobile-check][data-state="pass"]').count()==2,panel.inner_text())
    page.evaluate("localStorage.setItem('freeflex-mobile-readiness-v1',JSON.stringify({recoveryDrill:true}))");page.evaluate("window.dispatchEvent(new Event('online'))")
    recovery=page.locator('[data-mobile-confirm="recovery-drill"]')
    check('보호 전 복구 저장값 차단',recovery.is_disabled() and not recovery.is_checked())
    page.locator('[data-mobile-confirm="wireguard-client"]').check();page.locator('[data-mobile-confirm="profile-import"]').check()
    check('자가 확인 2종 분리',page.locator('[data-mobile-check][data-state="self_reported"]').count()==2)
    check('자가 확인 뒤에도 후보 아님','4 / 8 · 준비 중' in page.locator('[data-mobile-readiness-badge]').inner_text())
    with page.expect_download() as info: page.locator('[data-mobile-download-recovery]').click()
    card=json.loads(pathlib.Path(info.value.path()).read_text(encoding='utf-8'));raw=json.dumps(card)
    check('오프라인 복구 카드 다운로드',card['schema']=='freeflex-mobile-recovery-v1' and card['platform']=='android')
    check('복구 카드 자동 전송 없음',card['privacy']['automaticallyTransmitted'] is False)
    check('복구 카드 최소 필드',set(card)=={'schema','platform','officialWireGuardUrl','steps','privacy'})
    check('390px 가로 넘침 0',page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth'))
    check('모바일 하단 메뉴 4개',page.locator('.svc-mobile-nav [data-svc-go]').count()==4)
    check('브라우저 오류 0',not errors,'; '.join(errors))
    desktop=context.new_page();desktop.set_viewport_size({'width':1280,'height':900});desktop.goto(f'{base}/app.html?view=app');desktop.locator('[data-svc-go="account"]').first.dispatch_event('click')
    check('PC에서는 모바일 전용 패널 숨김',desktop.locator('[data-mobile-readiness]').is_hidden())
    browser.close()

failed=[(label,detail) for label,ok,detail in checks if not ok]
if failed:
    for label,detail in failed: print(f'  FAIL {label} — {detail}')
    raise SystemExit(f"모바일 출시 점검 UI {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"모바일 출시 점검 UI {len(checks)}/{len(checks)} 통과")
