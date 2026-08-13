#!/usr/bin/env python3
"""공통 상용 운영 관문의 문서/실제 증거 분리와 지원 묶음 안전성을 검증한다."""
from __future__ import annotations

import contextlib,pathlib,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,_format,*_args): pass
@contextlib.contextmanager
def server():
    factory=lambda *args,**kwargs:Quiet(*args,directory=str(ROOT),**kwargs);http=ThreadingHTTPServer(('127.0.0.1',0),factory);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{http.server_port}'
    finally:http.shutdown();http.server_close();thread.join(timeout=5)

with server() as base,sync_playwright() as pw:
    browser=pw.chromium.launch();page=browser.new_page();page.goto(f'{base}/20_SRC/app/commercial_readiness.js')
    checks=page.evaluate("""async url=>{const {evaluateCommercialReadiness,createRedactedSupportBundle,createIncidentChecklist}=await import(url);const out=[];const check=(n,v)=>out.push([n,Boolean(v)]);
      const empty=evaluateCommercialReadiness();check('기본 8관문 차단',empty.checks.length===8&&empty.documentedCount===0&&empty.verifiedCount===0&&!empty.commercialEvidenceReady);
      const docs=evaluateCommercialReadiness({documented:['privacy-rights','support-diagnostic','rollback-playbook','unknown']});check('문서화 3개 분리',docs.documentedCount===3&&docs.verifiedCount===0&&!docs.commercialEvidenceReady);
      const all=['privacy-rights','support-diagnostic','rollback-playbook','payment-roundtrip','refund-roundtrip','legal-review','operations-monitoring','limited-release'];const full=evaluateCommercialReadiness({verified:all});check('실제 8개만 완전 준비',full.verifiedCount===8&&full.commercialEvidenceReady);
      const bundle=createRedactedSupportBundle({platformFamily:'android',browserFamily:'chromium',online:true,standalone:true,apiMode:'live',protectionState:'protected',privateKey:'DROP',ipAddress:'DROP',configuration:'DROP',paymentMethod:'DROP',commercial:{documented:all}});check('지원 묶음 최소 필드',Object.keys(bundle).sort().join(',')==='apiMode,browserFamily,commercialChecks,generatedAt,online,platformFamily,privacy,protectionState,schema,standalone');check('자동 전송 없음',bundle.privacy.automaticallyTransmitted===false);check('문서화는 검증 아님',bundle.commercialChecks.every(item=>item.state==='documented'));
      const incident=createIncidentChecklist({platform:'pc'});check('장애 절차 4단계',incident.steps.length===4);check('삭제 권한 없음',incident.destructiveActionsAuthorized===false&&incident.sensitiveValuesRequired===false);check('기존 설정 보존',incident.steps.some(step=>step.includes('삭제·덮어쓰지')));return out;}""",f'{base}/20_SRC/app/commercial_readiness.js');browser.close()
failed=[n for n,ok in checks if not ok]
for n,ok in checks:print(f"{'PASS' if ok else 'FAIL'}: {n}")
if failed:raise SystemExit(f"상용 운영 관문 실패: {', '.join(failed)}")
print(f"상용 운영 관문 {len(checks)}/{len(checks)} 통과")
