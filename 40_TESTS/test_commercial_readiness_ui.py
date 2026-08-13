#!/usr/bin/env python3
"""PC·모바일에서 상용 관문과 지원/장애 파일의 안전한 표시를 검증한다."""
from __future__ import annotations

import contextlib,json,pathlib,sys,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'20_SRC'));import build_web_assets;build_web_assets.build()
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,_format,*_args):pass
@contextlib.contextmanager
def server():
    factory=lambda *args,**kwargs:Quiet(*args,directory=str(ROOT/'30_DEPLOY'),**kwargs);http=ThreadingHTTPServer(('127.0.0.1',0),factory);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{http.server_port}'
    finally:http.shutdown();http.server_close();thread.join(timeout=5)
checks=[]
def check(n,v,d=''):checks.append((n,bool(v),d))
with server() as base,sync_playwright() as pw:
    browser=pw.chromium.launch();context=browser.new_context(accept_downloads=True,viewport={'width':1280,'height':900});page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'{base}/app.html?view=app');page.locator('[data-svc-go="account"]').first.dispatch_event('click');panel=page.locator('[data-commercial-readiness]')
    check('PC 상용 관문 표시',panel.is_visible());check('문서 3·실제0 분리','3 / 8 문서화 · 실제 검증 0' in page.locator('[data-commercial-readiness-badge]').inner_text());check('문서화 3행',page.locator('[data-commercial-check][data-state="documented"]').count()==3);check('외부 차단 5행',page.locator('[data-commercial-check][data-state="blocked"]').count()==5)
    with page.expect_download() as info:page.locator('[data-commercial-download-support]').click()
    support=json.loads(pathlib.Path(info.value.path()).read_text(encoding='utf-8'));check('가린 지원 묶음',support['schema']=='freeflex-support-bundle-v1' and support['privacy']['automaticallyTransmitted'] is False);check('지원 묶음 최소 필드',set(support)=={'schema','generatedAt','platformFamily','browserFamily','online','standalone','apiMode','protectionState','commercialChecks','privacy'})
    with page.expect_download() as info:page.locator('[data-commercial-download-incident]').click()
    incident=json.loads(pathlib.Path(info.value.path()).read_text(encoding='utf-8'));check('PC 장애 체크리스트',incident['platform']=='pc' and incident['destructiveActionsAuthorized'] is False)
    mobile=context.new_page();mobile.set_viewport_size({'width':390,'height':844});mobile.goto(f'{base}/app.html?view=app');mobile.locator('[data-svc-go="account"]').last.dispatch_event('click');check('모바일 상용 관문 표시',mobile.locator('[data-commercial-readiness]').is_visible());check('모바일 가로 넘침 0',mobile.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth'));check('브라우저 오류 0',not errors,'; '.join(errors));browser.close()
failed=[(n,d) for n,ok,d in checks if not ok]
if failed:
    for n,d in failed:print(f'  FAIL {n} — {d}')
    raise SystemExit(f"상용 운영 UI {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"상용 운영 UI {len(checks)}/{len(checks)} 통과")
