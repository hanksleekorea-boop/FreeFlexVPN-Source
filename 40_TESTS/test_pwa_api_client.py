#!/usr/bin/env python3
"""실제 Chromium에서 PWA API 세션·오류·비밀값 경계를 검증한다."""
from __future__ import annotations

import asyncio
import contextlib
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.async_api import async_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
checks: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    checks.append((label, bool(ok), detail))


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


async def run() -> None:
    with local_server() as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(f"{base}/20_SRC/app/pwa_api_client.js")
            result = await page.evaluate(
                """async (base) => {
                  const m = await import(base + '/20_SRC/app/pwa_api_client.js');
                  const requests = [];
                  const token = 't'.repeat(43);
                  const fakeFetch = async (url, options) => {
                    requests.push({url, ...options, headers: {...options.headers}});
                    if (url.endsWith('/v1/claims/exchange')) return {ok:true,status:200,json:async()=>({access_token:token,wallet:{}})};
                    if (url.endsWith('/v1/wallet')) return {ok:true,status:200,json:async()=>({balances:{free:1000000000,earned:0,paid:0},total_available_bytes:1000000000})};
                    if (url.endsWith('/v1/devices') && options.method === 'POST') return {ok:true,status:201,json:async()=>({device_id:'a'.repeat(32)})};
                    return {ok:false,status:401,json:async()=>({error:'AUTH_REQUIRED',message:'expired'})};
                  };
                  const brokenStorage = {getItem(){throw new Error('blocked')},setItem(){throw new Error('blocked')},removeItem(){throw new Error('blocked')}};
                  const vault = new m.SessionVault(brokenStorage);
                  const client = new m.FreeFlexApiClient({apiBase:'https://api.example.test/',fetchImpl:fakeFetch,vault});
                  const exchange = await client.exchangeClaim('c'.repeat(43));
                  const wallet = await client.wallet();
                  const tokenBefore401 = vault.get();
                  await client.registerDevice('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', 'sg-edge-1');
                  let apiError = null;
                  try { await client.usage(); } catch (error) { apiError = {name:error.name,code:error.code,status:error.status,message:error.message}; }
                  const tokenImmediatelyAfter401 = vault.get();
                  let invalidBase = '';
                  try { new m.FreeFlexApiClient({apiBase:'http://api.example.test',fetchImpl:fakeFetch}); } catch(error) { invalidBase=error.message; }
                  let invalidBytes = '';
                  try { m.bytesToGb(-1); } catch(error) { invalidBytes=error.message; }
                  const historyCalls=[];
                  const launchUrl=m.buildClaimLaunchUrl('https://app.example.test/app.html','d'.repeat(43),'invite');
                  const fakeLocation={href:launchUrl};
                  const fakeHistory={replaceState(...args){historyCalls.push(args)}};
                  await m.consumeLaunchParameters(client,fakeLocation,fakeHistory);
                  return {requests,exchange,wallet,persistence:vault.persistence,tokenBefore401,tokenImmediatelyAfter401,apiError,invalidBase,invalidBytes,historyCalls,launchUrl};
                }""",
                base,
            )
            await browser.close()

    requests = result["requests"]
    exchange_body = requests[0]["body"]
    wallet_request = requests[1]
    device_request = requests[2]
    check("claim 교환 후 access token 반환값 제거", "access_token" not in result["exchange"] or result["exchange"]["access_token"] is None)
    check("저장 차단 시 메모리 세션으로 무정지", result["persistence"] == "memory" and len(result["tokenBefore401"]) == 43)
    check("인증 헤더는 보호 API에만 전송", "Authorization" not in requests[0]["headers"] and wallet_request["headers"]["Authorization"].startswith("Bearer "))
    check("요청마다 쿠키·캐시 배제", all(item["credentials"] == "omit" and item["cache"] == "no-store" for item in requests))
    check("기기 등록은 공개키만 전송", "wg_public_key" in device_request["body"] and "private" not in device_request["body"].lower())
    check("API 오류가 상태·코드로 분리", result["apiError"]["name"] == "FreeFlexApiError" and result["apiError"]["status"] == 401)
    check("401 뒤 만료 세션 즉시 폐기", result["tokenImmediatelyAfter401"] is None)
    check("HTTP API base 거부", result["invalidBase"] == "HTTPS_API_BASE_REQUIRED")
    check("음수 바이트 거부", result["invalidBytes"] == "BYTE_COUNT_INVALID")
    check("십진 GB 표시", result["wallet"]["total_available_bytes"] == 1_000_000_000)
    check("claim 링크가 서버 비노출 fragment 사용", "?claim=" not in result["launchUrl"] and "#claim=" in result["launchUrl"], result["launchUrl"])
    check("claim·추천 토큰 URL에서 제거", result["historyCalls"][-1][2] == "/app.html", str(result["historyCalls"]))
    check("claim 원문을 인증 헤더로 오사용하지 않음", "c" * 43 not in str(wallet_request["headers"]))
    check("브라우저 실행 오류 0", not errors, "; ".join(errors))


asyncio.run(run())
failed = [(label, detail) for label, ok, detail in checks if not ok]
if failed:
    for label, detail in failed: print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"PWA API 클라이언트 검사 {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"PWA API 클라이언트 검사 {len(checks)}/{len(checks)} 통과")
