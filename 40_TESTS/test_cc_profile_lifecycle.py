#!/usr/bin/env python3
from __future__ import annotations
import contextlib, pathlib, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args): pass
@contextlib.contextmanager
def server():
    factory=lambda *a,**k: Quiet(*a,directory=str(ROOT),**k); http=ThreadingHTTPServer(("127.0.0.1",0),factory)
    thread=threading.Thread(target=http.serve_forever,daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{http.server_port}"
    finally: http.shutdown(); http.server_close(); thread.join(timeout=5)

with server() as base, sync_playwright() as pw:
    browser=pw.chromium.launch(); page=browser.new_page(); page.goto(f"{base}/20_SRC/app/profile_lifecycle.js")
    checks=page.evaluate("""async url=>{const {evaluateProfileLifecycle:e}=await import(url);const o=[],c=(n,v)=>o.push([n,!!v]);const now='2026-08-24T12:00:00Z',base={issued_at:'2026-08-24T11:55:00Z',delivery_expires_at:'2026-08-24T12:05:00Z',existing_profile_count:1,protection_grade:'unconfirmed',return_path_confirmed:false};
    c('발급 전',e({}, {now}).state==='ready_to_issue');c('한 번 저장 대기',e({...base,delivery_state:'ready'},{now}).state==='download_required');c('가져오기 대기',e({...base,delivery_state:'downloaded'},{now}).state==='import_required');c('보호 확인 대기',e({...base,delivery_state:'imported'},{now}).state==='protection_required');c('복귀 확인 대기',e({...base,delivery_state:'imported',protection_grade:'confirmed'},{now}).state==='return_path_required');const done=e({...base,delivery_state:'imported',protection_grade:'confirmed',return_path_confirmed:true},{now});c('후보 검증 뒤에도 기존 보존',done.state==='candidate_verified'&&done.existing_profile_action==='preserve'&&!done.automatic_legacy_revocation);c('만료 자료 차단',e({...base,delivery_state:'ready'},{now:'2026-08-24T12:06:00Z'}).state==='expired');c('취소 뒤 기존 보존',e({...base,delivery_state:'cancelled'},{now}).existing_profile_action==='preserve');c('시각 누락 닫힘',e({delivery_state:'ready'},{now}).state==='invalid_evidence');let bad=false;try{e({...base,delivery_expires_at:'2026-08-24T11:00:00Z'},{now})}catch(x){bad=x.message==='DELIVERY_EXPIRY_INVALID'}c('역전 시각 거부',bad);const raw=JSON.stringify(e({...base,delivery_state:'ready',configuration:'SECRET',private_key:'NEVER'},{now}));c('설정·키 원문 제외',!raw.includes('SECRET')&&!raw.includes('NEVER')&&raw.includes('contains_configuration'));return o}""",f"{base}/20_SRC/app/profile_lifecycle.js"); browser.close()
source=(ROOT/'20_SRC/app/pwa_runtime.js').read_text(encoding='utf-8'); builder=(ROOT/'20_SRC/build_app_v2.py').read_text(encoding='utf-8'); api=(ROOT/'20_SRC/app/control_api.py').read_text(encoding='utf-8')
checks += [('10분 수령 계약','delivery_expires_at' in api and 'timedelta(minutes=10)' in api),('한 번 저장 뒤 원문 지움','currentConfig = null; profileConfig.value = ""' in source),('수명주기 UI','profileLifecycleCopy' in source and 'data-profile-lifecycle' in builder),('기존 자동 폐기 없음','automatic_legacy_revocation:false' in (ROOT/'20_SRC/app/profile_lifecycle.js').read_text(encoding='utf-8'))]
failed=[n for n,v in checks if not v]
for n,v in checks: print(f"{'PASS' if v else 'FAIL'}: {n}")
if failed: raise SystemExit(', '.join(failed))
print(f"CC 설정 수명주기 {len(checks)}/{len(checks)} 통과")
