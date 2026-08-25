#!/usr/bin/env python3
from __future__ import annotations
import contextlib, pathlib, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,_format,*_args): pass
@contextlib.contextmanager
def server():
    factory=lambda *a,**k:Quiet(*a,directory=str(ROOT),**k); http=ThreadingHTTPServer(("127.0.0.1",0),factory); thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{http.server_port}"
    finally:http.shutdown();http.server_close();thread.join(timeout=5)
with server() as base,sync_playwright() as pw:
    browser=pw.chromium.launch();page=browser.new_page();page.goto(f"{base}/20_SRC/app/error_recovery.js")
    checks=page.evaluate("""async url=>{const {createRecoveryAction:c,RECOVERY_CODES:codes}=await import(url);const o=[],check=(n,v)=>o.push([n,!!v]);check('오류 8종',codes.length===8);for(const code of codes){const a=c(code,0);check(code,a.code===code&&a.existing_profile_action==='preserve'&&!a.automatic_profile_deletion&&!a.automatic_payment_retry&&a.next_action.length>10)}const retry=c('NO_INTERNET',2);check('재시도 2회 상한',!retry.retry_allowed&&retry.focus_target==='support');const pay=c('PAYMENT_PENDING',0);check('결제 자동 재시도 금지',!pay.retry_allowed&&!pay.automatic_payment_retry);const unknown=c('FORGED',0);check('모르는 오류 안전 중단',unknown.code==='UNKNOWN'&&!unknown.retry_allowed);return o}""",f"{base}/20_SRC/app/error_recovery.js");browser.close()
runtime=(ROOT/'20_SRC/app/pwa_runtime.js').read_text(encoding='utf-8');shell=(ROOT/'20_SRC/html_templates/service_shell.html').read_text(encoding='utf-8')
checks += [('실행 오류와 화면 결속','freeflex:recovery-action' in runtime and 'freeflex:recovery-action' in shell),('오류 초점 이동','output.focus()' in shell)]
failed=[n for n,v in checks if not v]
for n,v in checks:print(f"{'PASS' if v else 'FAIL'}: {n}")
if failed:raise SystemExit(', '.join(failed))
print(f"CC 오류 복구 {len(checks)}/{len(checks)} 통과")
