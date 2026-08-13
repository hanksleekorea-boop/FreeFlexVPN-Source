#!/usr/bin/env python3
"""모바일 출시 점검 엔진과 오프라인 복구 카드의 안전 계약을 검증한다."""
from __future__ import annotations

import contextlib
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None: pass


@contextlib.contextmanager
def local_server():
    factory = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)


with local_server() as base, sync_playwright() as pw:
    browser = pw.chromium.launch(); page = browser.new_page()
    page.goto(f"{base}/20_SRC/app/mobile_readiness.js")
    checks = page.evaluate("""async url=>{
      const {evaluateMobileReadiness,createMobileRecoveryCard}=await import(url);const out=[];const check=(n,v)=>out.push([n,Boolean(v)]);
      const empty=evaluateMobileReadiness();
      check('기본값 fail-closed',empty.completedCount===0&&empty.verifiedCount===0&&!empty.readyForCandidateReview&&!empty.commercialEvidenceReady);
      check('모바일 점검 8종',empty.checks.length===8);
      check('잘못된 플랫폼 차단',evaluateMobileReadiness({platform:'windows'}).platform==='other');
      const full=evaluateMobileReadiness({platform:'android',secureContext:true,online:true,apiMode:'live',standalone:true,wireguardClientConfirmed:true,profileImportedConfirmed:true,protectionState:'protected',recoveryDrillConfirmed:true});
      check('후보 점검 8/8',full.completedCount===8&&full.readyForCandidateReview);
      check('자가 확인은 검증 아님',full.verifiedCount===5&&!full.commercialEvidenceReady);
      check('자가 확인 3종 분리',full.checks.filter(item=>item.state==='self_reported').length===3);
      check('끊김 실패',evaluateMobileReadiness({protectionState:'disconnected'}).checks.find(item=>item.id==='protection').state==='fail');
      const android=createMobileRecoveryCard({platform:'android',privateKey:'DROP',configuration:'DROP',ipAddress:'DROP'});const raw=JSON.stringify(android);
      check('Android 공식 앱 주소',android.officialWireGuardUrl.includes('com.wireguard.android'));
      check('복구 3단계',android.steps.length===3&&android.steps.some(step=>step.includes('삭제하거나 덮어쓰지')));
      check('복구 카드 최소 필드',Object.keys(android).sort().join(',')==='officialWireGuardUrl,platform,privacy,schema,steps');
      check('자동 전송 없음',android.privacy.automaticallyTransmitted===false);
      check('iPhone 공식 앱 주소',createMobileRecoveryCard({platform:'ios'}).officialWireGuardUrl.includes('id1441195209'));
      check('기타 공식 안내',createMobileRecoveryCard({platform:'unknown'}).officialWireGuardUrl==='https://www.wireguard.com/install/');
      return out;
    }""", f"{base}/20_SRC/app/mobile_readiness.js")
    browser.close()

failed=[name for name,ok in checks if not ok]
for name,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"모바일 출시 점검 엔진 실패: {', '.join(failed)}")
print(f"모바일 출시 점검 엔진 {len(checks)}/{len(checks)} 통과")
