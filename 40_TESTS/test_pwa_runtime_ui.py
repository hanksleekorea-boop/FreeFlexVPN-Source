#!/usr/bin/env python3
"""실제 Chromium에서 API 연결 PWA의 계정·키·상태 UI를 왕복 검증한다."""
from __future__ import annotations

import asyncio
import contextlib
import json
import pathlib
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.async_api import Route, async_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "30_DEPLOY" / "app.html"
checks: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    checks.append((label, bool(ok), detail))


class AppHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path == "/app.html":
            raw = APP.read_text(encoding="utf-8").replace(
                '<meta name="freeflex-api-base" content="">',
                '<meta name="freeflex-api-base" content="https://api.example.test">',
                1,
            ).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        return super().do_GET()


@contextlib.contextmanager
def local_server():
    factory = lambda *args, **kwargs: AppHandler(*args, directory=str(ROOT / "30_DEPLOY"), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)


async def run() -> None:
    requests: list[dict] = []
    state = {"device": False}
    with local_server() as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            context = await browser.new_context()
            await context.add_init_script("Object.defineProperty(navigator,'share',{value:async()=>true,configurable:true});")
            page = await context.new_page()
            page.set_default_timeout(10_000)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            async def api(route: Route):
                request = route.request
                path = urllib.parse.urlsplit(request.url).path
                requests.append({"path": path, "method": request.method, "body": request.post_data or "", "headers": request.headers})
                if request.method == "OPTIONS":
                    await route.fulfill(
                        status=204,
                        body="",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-FreeFlex-Device",
                        },
                    )
                    return
                if path == "/v1/claims/exchange":
                    payload = {"access_token": "s" * 43, "wallet": {}}
                elif path == "/v1/catalog":
                    payload = {"servers": [{"server_id": "sg-edge-1", "country_code": "SG", "country": "Singapore", "city": "Singapore", "health": "healthy", "capacity_percent": 12}], "available_count": 1}
                elif path == "/v1/wallet":
                    payload = {"balances": {"free": 900000000, "earned": 500000000, "paid": 3000000000}, "total_available_bytes": 4400000000}
                elif path == "/v1/devices" and request.method == "GET":
                    payload = {"devices": ([{"device_id": "a" * 32, "server_id": "sg-edge-1", "assigned_address": "10.66.0.2/32", "status": "active", "created_at": "2026-08-02T00:00:00+00:00", "revoked_at": None}] if state["device"] else []), "active_count": int(state["device"]), "active_limit": 2}
                elif path == "/v1/devices" and request.method == "POST":
                    state["device"] = True
                    payload = {"device_id": "a" * 32, "status": "active", "private_key_received": False, "configuration": {"addresses": ["10.66.0.2/32"], "dns": ["1.1.1.1"], "peer": {"public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", "endpoint": "vpn.example.test:51820", "allowed_ips": ["0.0.0.0/0", "::/0"], "persistent_keepalive": 25}}}
                elif path == "/v1/check":
                    payload = {"state": "protected", "checks": {"tunnel": True, "exit_ip": True, "dns": True, "ipv6": True, "kill_switch": True}, "checked_at": "2026-08-02T00:01:00+00:00"}
                elif path == "/v1/referrals" and request.method == "POST":
                    payload = {"share_url": "https://app.example.test/app.html?ref=safe-referral"}
                else:
                    await route.fulfill(status=404, json={"error": "NOT_FOUND", "message": "not found"}, headers={"Access-Control-Allow-Origin": "*"}); return
                await route.fulfill(status=201 if request.method == "POST" and path in ("/v1/devices", "/v1/referrals") else 200, json=payload, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type, X-FreeFlex-Device"})

            await page.route("https://api.example.test/**", api)
            print("PWA UI 단계 1/4: 브라우저·API 준비", flush=True)
            await page.goto(f"{base}/app.html?review=1#claim={'c'*43}")
            try:
                await page.wait_for_function("document.documentElement.dataset.apiMode === 'live'", timeout=10_000)
            except Exception:
                mode = await page.get_attribute("html", "data-api-mode")
                banner = await page.text_content("#runtimeBanner")
                raise AssertionError(f"api mode={mode!r}; banner={banner!r}; errors={errors!r}; requests={requests!r}")
            await page.wait_for_function(
                "document.getElementById('walletTotalValue').textContent === '4.40' "
                "&& !document.getElementById('createProfileButton').disabled",
                timeout=10_000,
            )
            check("fragment claim URL이 즉시 제거됨", "claim=" not in page.url, page.url)
            check("실제 API 모드 전환", await page.get_attribute("html", "data-api-mode") == "live")
            check("health 서버 1대 렌더", await page.get_attribute("#serverCatalog", "data-server-count") == "1")
            check("실제 지갑 4.40GB 동기화", await page.text_content("#walletTotalValue") == "4.40")
            check("키 생성 버튼 활성화", not await page.is_disabled("#createProfileButton"))
            print("PWA UI 단계 2/4: 계정·카탈로그·지갑 동기화", flush=True)

            await page.evaluate("go('moments')")
            check("Moment 30 전체 렌더", await page.locator(".recommendation-card").count() == 30)
            await page.select_option("#currentCountrySelect", "CN")
            await page.select_option("#destinationCountrySelect", "SG")
            check("중국 제한 환경 정직 고지", "전문 서비스를 이용" in await page.text_content("#countryPolicyBanner"))
            check("중국에서 일반 서버 추천 비활성", await page.locator(".recommendation-card button:not([disabled])").count() == 0)
            await page.select_option("#currentCountrySelect", "KR")
            await page.select_option("#momentCategorySelect", "research")
            await page.click('[data-tier-filter="paid"]')
            target_card = page.locator('[data-moment-id="local-search-qa"]')
            check("목적국 SG 유료 조사 추천 활성", await target_card.locator("button:not([disabled])").count() == 1)
            await target_card.locator("button").click()
            check("추천이 실제 SG 서버 선택 화면으로 이동", await page.locator('[data-screen="locations"].active').count() == 1 and await page.locator('[data-server-id="sg-edge-1"].selected').count() == 1)

            await page.evaluate("go('platforms')")
            check("PC·모바일 플랫폼 5종 렌더", await page.locator("[data-platform]").count() == 5)
            await page.locator('[data-platform="windows"]').dispatch_event("click")
            windows_install_copy = await page.text_content("#platformPwaCopy")
            check("Windows Chrome 설치 안내", "Chrome" in windows_install_copy and "설치" in windows_install_copy, windows_install_copy)
            check("공식 WireGuard 설치 링크", await page.get_attribute("#wireguardInstallLink", "href") == "https://www.wireguard.com/install/")
            check("서버·로그인 후 PC 구성 가능 표시", await page.text_content("#platformVpnState") == "이 기기 구성 발급 가능")
            await page.locator("#platformInstallButton").dispatch_event("click")
            await page.wait_for_timeout(50)
            check("PWA 설치 도움 경로", not await page.is_hidden("#installBanner"))

            await page.evaluate("go('setup')")
            await page.click("#createProfileButton")
            await page.wait_for_function("!document.getElementById('profilePanel').hidden")
            config = await page.input_value("#profileConfig")
            device_posts = [item for item in requests if item["path"] == "/v1/devices" and item["method"] == "POST"]
            check("WireGuard 구성에 로컬 개인키 포함", "PrivateKey = " in config and "[Peer]" in config)
            check("기기 요청에 개인키 미전송", len(device_posts) == 1 and "private" not in device_posts[0]["body"].lower(), str(device_posts))
            await page.wait_for_function(
                "document.getElementById('deviceCountValue').textContent === '1 / 2'",
                timeout=10_000,
            )
            check("생성 뒤 기기 1/2 동기화", await page.text_content("#deviceCountValue") == "1 / 2")
            print("PWA UI 단계 3/4: 기기 키·구성 생성", flush=True)

            await page.evaluate("go('home')")
            await page.locator("[data-direct-check]").dispatch_event("click")
            await page.wait_for_function("document.getElementById('statusCard').dataset.connectionState === 'protected'")
            await page.wait_for_timeout(800)
            check("실측 protected가 가짜 타이머에 덮이지 않음", await page.get_attribute("#statusCard", "data-connection-state") == "protected")

            await page.evaluate("go('referral')")
            await page.locator("#shareReferralButton").dispatch_event("click")
            await page.wait_for_function("!document.getElementById('shareReferralOutput').hidden")
            check("추천 링크 실제 API 발급", "safe-referral" in await page.input_value("#shareReferralOutput"))
            serialized_requests = json.dumps(requests, ensure_ascii=False)
            check("목적·현재 국가·플랫폼 선택 값 API 미전송", all(value not in serialized_requests for value in ("public-wifi", "local-search-qa", "currentCountry", "destinationCountry", "platformId", "selectedPlatform")))
            check("보호 API에 기기 헤더 사용", any(item["path"] == "/v1/check" and item["headers"].get("x-freeflex-device") == "a" * 32 for item in requests))
            check("브라우저 실행 오류 0", not errors, "; ".join(errors))
            print("PWA UI 단계 4/4: 보호 확인·추천 링크", flush=True)
            await browser.close()


asyncio.run(run())
failed = [(label, detail) for label, ok, detail in checks if not ok]
if failed:
    for label, detail in failed: print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"PWA 런타임 UI 검사 {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"PWA 런타임 UI 검사 {len(checks)}/{len(checks)} 통과")
