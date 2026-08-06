#!/usr/bin/env python3
"""Browser-consumed contract tests for client-side WireGuard key handling."""
from __future__ import annotations

import asyncio
import contextlib
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.async_api import async_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "20_SRC" / "app" / "client_keygen.js"
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
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def run() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    check("개인키 브라우저 영속저장 API 미사용", "localStorage" not in source and "sessionStorage" not in source)
    check("로그 출력 API 미사용", "console." not in source)

    with local_server() as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(f"{base}/20_SRC/app/client_keygen.js")
            result = await page.evaluate(
                """async (base) => {
                  const m = await import(base + '/20_SRC/app/client_keygen.js');
                  const supported = await m.supportsBrowserX25519();
                  if (!supported) return { supported, fallback: m.manualFallback };
                  const pair = await m.generateWireGuardKeyPair();
                  let captured = null;
                  const registration = {
                    address: '10.66.0.2/32',
                    endpoint: 'vpn.example.test:51820',
                    dns: '1.1.1.1',
                    server_public_key: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
                  };
                  const fakeFetch = async (url, request) => {
                    captured = { url, headers: request.headers, body: request.body, credentials: request.credentials, cache: request.cache };
                    return { ok: true, json: async () => registration };
                  };
                  const profile = await m.createDeviceProfile({
                    apiBase: 'https://api.example.test',
                    sessionToken: 'session-token-at-least-twenty-characters',
                    serverId: 'sg-edge-1',
                    fetchImpl: fakeFetch,
                  });
                  let unsupported = '';
                  try { await m.generateWireGuardKeyPair({}); } catch (error) { unsupported = error.message; }
                  let invalid = '';
                  try { m.renderWireGuardConfig(pair.privateKey, {...registration, address: '10.66.0.1/32'}); }
                  catch (error) { invalid = error.message; }
                  return { supported, pair, captured, profile, unsupported, invalid };
                }""",
                base,
            )
            await browser.close()

    check("Chromium X25519 실제 생성 지원", result.get("supported") is True, str(result)[:160])
    if result.get("supported"):
        pair = result["pair"]
        import base64

        check("개인키 32바이트", len(base64.b64decode(pair["privateKey"])) == 32)
        check("공개키 32바이트", len(base64.b64decode(pair["publicKey"])) == 32)
        body = result["captured"]["body"]
        profile = result["profile"]
        profile_private = next(
            line.split(" = ", 1)[1]
            for line in profile["config"].splitlines()
            if line.startswith("PrivateKey = ")
        )
        check("등록 요청은 공개키만 전송", profile["publicKey"] in body and profile_private not in body, body)
        check("등록 요청은 쿠키·캐시 배제", result["captured"]["credentials"] == "omit" and result["captured"]["cache"] == "no-store")
        check("개인키는 로컬 구성에만 포함", profile_private not in body and "PrivateKey = " in profile["config"])
        check("지원 불가 환경은 명시적 실패", result["unsupported"] == "BROWSER_X25519_UNAVAILABLE", result["unsupported"])
        check("서버가 배정할 수 없는 주소 거부", result["invalid"] == "ADDRESS_INVALID", result["invalid"])
    check("브라우저 실행 오류 0", not errors, "; ".join(errors))


asyncio.run(run())
failed = [(label, detail) for label, ok, detail in checks if not ok]
if failed:
    for label, detail in failed:
        print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"클라이언트 키 생성 검사 {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"클라이언트 키 생성 검사 {len(checks)}/{len(checks)} 통과")
