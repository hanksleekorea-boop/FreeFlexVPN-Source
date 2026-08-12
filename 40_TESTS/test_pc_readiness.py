#!/usr/bin/env python3
"""PC 출시 점검 엔진의 fail-closed·비밀값 제외 계약을 Chromium에서 검증한다."""
from __future__ import annotations

import contextlib
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


@contextlib.contextmanager
def local_server():
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


with local_server() as base, sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    page.goto(f"{base}/20_SRC/app/pc_readiness.js")
    checks = page.evaluate("""async (url) => {
      const {createPcPreferenceBackup,createRedactedPcDiagnostic,evaluatePcReadiness,sanitizePcPreferenceBackup}=await import(url);
      const out=[];const check=(name,ok)=>out.push([name,Boolean(ok)]);
      const empty=evaluatePcReadiness();
      check('기본값 fail-closed',empty.completedCount===0&&empty.verifiedCount===0&&!empty.readyForCandidateReview&&!empty.commercialEvidenceReady);
      check('기본 점검 7종',empty.checks.length===7);
      check('잘못된 enum 차단',evaluatePcReadiness({apiMode:'forged',protectionState:'protected-ish'}).apiMode==='unconfigured'&&evaluatePcReadiness({protectionState:'protected-ish'}).protectionState==='unverified');
      const partial=evaluatePcReadiness({secureContext:true,online:true,apiMode:'live',wireguardClientConfirmed:true,profileImportedConfirmed:true,protectionState:'protected',recoveryDrillConfirmed:true});
      check('후보 검토 7/7',partial.completedCount===7&&partial.readyForCandidateReview);
      check('자가 확인은 검증 아님',partial.verifiedCount===4&&!partial.commercialEvidenceReady);
      check('자가 확인 상태 구분',partial.checks.filter(item=>item.state==='self_reported').length===3);
      check('보호 끊김 실패',evaluatePcReadiness({protectionState:'disconnected'}).checks.find(item=>item.id==='protection').state==='fail');
      const diagnostic=createRedactedPcDiagnostic({secureContext:true,online:true,apiMode:'live',protectionState:'protected',browserFamily:'chromium',platformFamily:'windows',standalone:true,generatedAt:'2026-08-12T00:00:00Z',ipAddress:'203.0.113.9',privateKey:'NEVER_EXPORT',configuration:'SECRET_CONFIG',userAgent:'FULL_UA'});
      const raw=JSON.stringify(diagnostic);
      check('진단 스키마 고정',diagnostic.schema==='freeflex-pc-diagnostic-v1'&&diagnostic.generatedAt==='2026-08-12T00:00:00Z');
      check('진단 환경 범주만 포함',diagnostic.browserFamily==='chromium'&&diagnostic.platformFamily==='windows'&&diagnostic.standalone===true);
      check('민감 입력값 제거',!raw.includes('203.0.113.9')&&!raw.includes('NEVER_EXPORT')&&!raw.includes('SECRET_CONFIG')&&!raw.includes('FULL_UA'));
      check('자동 전송 없음 명시',diagnostic.privacy.automaticallyTransmitted===false);
      check('필수 제외 목록 명시',['ip_address','private_key','configuration','browsing_history','account_identifier','full_user_agent'].every(value=>diagnostic.privacy.excluded.includes(value)));
      const backup=createPcPreferenceBackup({accessibility:{large:true,contrast:false,secret:'drop'},focusMode:true,account:'drop'});
      check('백업 최소 필드',JSON.stringify(backup)==='{"schema":"freeflex-pc-preferences-v1","accessibility":{"large":true,"contrast":false},"focusMode":true}');
      const sanitized=sanitizePcPreferenceBackup({schema:'freeflex-pc-preferences-v1',accessibility:{large:1,contrast:true},focusMode:'yes',extra:'drop'});
      check('백업 엄격 boolean',sanitized.accessibility.large===false&&sanitized.accessibility.contrast===true&&sanitized.focusMode===false&&!('extra' in sanitized));
      let badSchema=false;try{sanitizePcPreferenceBackup({schema:'other'})}catch(error){badSchema=error.message==='BACKUP_SCHEMA_UNSUPPORTED'}
      check('다른 스키마 거부',badSchema);
      let badShape=false;try{sanitizePcPreferenceBackup([])}catch(error){badShape=error.message==='BACKUP_INVALID'}
      check('배열 백업 거부',badShape);
      return out;
    }""", f"{base}/20_SRC/app/pc_readiness.js")
    browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed:
    raise SystemExit(f"PC 출시 점검 엔진 실패: {', '.join(failed)}")
print(f"PC 출시 점검 엔진 {len(checks)}/{len(checks)} 통과")
