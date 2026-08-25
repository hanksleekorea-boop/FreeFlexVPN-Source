#!/usr/bin/env python3
"""CC-TASK-1-01 보호 카드의 상태·신선도·비밀값 제외 계약을 Chromium에서 검증한다."""
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
    page.goto(f"{base}/20_SRC/app/protection_evidence.js")
    checks = page.evaluate("""async (url) => {
      const {deriveProtectionEvidencePresentation,sanitizeProtectionEvidence}=await import(url);
      const out=[];const check=(name,ok)=>out.push([name,Boolean(ok)]);
      const now='2026-08-24T12:00:00Z';
      const full={state:'protected',checked_at:'2026-08-24T11:59:00Z',checks:{tunnel:true,exit_ip:true,dns:true,ipv6:true,webrtc:true,kill_switch:true}};
      const protectedResult=deriveProtectionEvidencePresentation(full,{now});
      check('최신 전체 근거만 보호됨',protectedResult.presentation==='protected'&&protectedResult.evidence_grade==='confirmed'&&protectedResult.counts.passed===5);
      const partial=deriveProtectionEvidencePresentation({state:'limited',checked_at:'2026-08-24T11:59:00Z',checks:{tunnel:true,exit_ip:true}},{now});
      check('2026-08-22형 IPv4 부분 증거',partial.presentation==='partial'&&partial.evidence_grade==='partial'&&partial.counts.missing===3);
      const stale=deriveProtectionEvidencePresentation({...full,checked_at:'2026-08-24T10:00:00Z'},{now});
      check('오래된 근거 다시 확인',stale.presentation==='stale'&&stale.freshness==='stale');
      const missing=deriveProtectionEvidencePresentation({state:'limited'},{now});
      check('자료 없음 확인 필요',missing.presentation==='unverified'&&missing.evidence_grade==='unconfirmed');
      const mismatch=deriveProtectionEvidencePresentation({...full,checks:{...full.checks,dns:false}},{now});
      check('불일치 보호 안 됨',mismatch.presentation==='error'&&mismatch.title==='보호 안 됨');
      const error=deriveProtectionEvidencePresentation({state:'error'},{now});
      check('검사 오류 보호 안 됨',error.presentation==='error'&&error.evidence_grade==='unconfirmed');
      const cancelled=deriveProtectionEvidencePresentation({state:'cancelled',checks:{tunnel:true}},{now});
      check('취소 별도 표시',cancelled.presentation==='cancelled');
      const redacted=sanitizeProtectionEvidence({...full,observed_ip:'198.51.100.7',private_key:'NEVER',checks:{...full.checks,ip_address:'198.51.100.7'}});
      const raw=JSON.stringify(redacted);
      check('IP·개인키 원문 제거',!raw.includes('198.51.100.7')&&!raw.includes('NEVER')&&!('observed_ip' in redacted));
      return out;
    }""", f"{base}/20_SRC/app/protection_evidence.js")
    for width in (360, 390, 1280, 1920):
        viewport = browser.new_page(viewport={"width": width, "height": 900})
        viewport.goto(f"{base}/30_DEPLOY/app.html", wait_until="domcontentloaded")
        layout = viewport.evaluate("""() => ({
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
          card: Boolean(document.querySelector('[data-svc-evidence-grade]')),
          history: Boolean(document.querySelector('[data-svc-evidence-history]')),
        })""")
        checks.append((f"{width}px 보호 카드·가로 넘침 없음", not layout["overflow"] and layout["card"] and layout["history"]))
        viewport.close()
    browser.close()

shell = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
checks.extend([
    ("현재 근거 등급 UI", "data-svc-evidence-grade" in shell and "현재 기기 · 최신 자료 없음" in shell),
    ("모바일·PC 같은 계산 사용", "data-svc-workbench-protection" in shell and "workbenchTitle.textContent=detail.title" in shell),
    ("과거 기록을 현재와 분리", "지난 실제 확인 기록 · 현재 상태가 아님" in shell and "부분 증거:" in shell),
    ("과거 미확인 범위 공개", all(value in shell for value in ("DNS·IPv6·WebRTC·차단 스위치·장시간 안정성은 미확인", "태국에서 미국 IPv4 경로"))),
    ("주소·키 비노출 안내", "실제 주소 원문·개인키·설정 원문은 이 카드에 저장하거나 표시하지 않습니다" in shell),
])
failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed:
    raise SystemExit(f"CC 보호 카드 실패: {', '.join(failed)}")
print(f"CC 보호 카드 {len(checks)}/{len(checks)} 통과")
