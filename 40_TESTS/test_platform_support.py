#!/usr/bin/env python3
"""Chromium에서 모든 기기 지원 모듈의 감지·역할·fail-closed 계약을 검증한다."""
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
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)


with local_server() as base, sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    page.goto(f"{base}/20_SRC/app/platform_support.js")
    checks = page.evaluate("""async (url) => {
      const { PLATFORM_PROFILES, WIREGUARD_INSTALL_URL, detectBrowser, detectPlatform, getInstallGuidance, getPlatformReadiness } = await import(url);
      const out=[]; const check=(name, ok)=>out.push([name, Boolean(ok)]);
      check("플랫폼 5종", Object.keys(PLATFORM_PROFILES).length === 5);
      check("Windows 감지", detectPlatform({userAgent:"Mozilla Windows",platform:"Win32"}) === "windows");
      check("macOS 감지", detectPlatform({userAgent:"Mozilla Macintosh",platform:"MacIntel",maxTouchPoints:0}) === "macos");
      check("iPad 데스크톱 UA 감지", detectPlatform({userAgent:"Mozilla Macintosh",platform:"MacIntel",maxTouchPoints:5}) === "ios");
      check("Android 감지", detectPlatform({userAgent:"Mozilla Android",platform:"Linux armv8"}) === "android");
      check("Linux 감지", detectPlatform({userAgent:"Mozilla Linux",platform:"Linux x86_64"}) === "linux");
      check("Edge 우선 감지", detectBrowser("Mozilla Chrome/120 Edg/120") === "edge");
      check("Chrome 감지", detectBrowser("Mozilla Chrome/120 Safari/537") === "chrome");
      check("Safari 감지", detectBrowser("Mozilla Version/17 Safari/605") === "safari");
      check("Firefox 감지", detectBrowser("Mozilla Firefox/130") === "firefox");
      check("공식 설치 URL", WIREGUARD_INSTALL_URL === "https://www.wireguard.com/install/");
      check("모든 플랫폼 PWA 안내", Object.values(PLATFORM_PROFILES).every(p => p.pwa && p.installLabel));
      check("모든 플랫폼 WireGuard 안내", Object.values(PLATFORM_PROFILES).every(p => p.wireguard.includes("WireGuard")));
      const blocked = getPlatformReadiness({platformId:"windows",serverReady:false,authenticated:true});
      check("서버 없으면 구성 비활성", blocked.vpnConfig === "server_required" && !blocked.canIssueConfig);
      const login = getPlatformReadiness({platformId:"android",serverReady:true,authenticated:false});
      check("로그인 없으면 구성 비활성", login.vpnConfig === "login_required" && !login.canIssueConfig);
      const ready = getPlatformReadiness({platformId:"ios",serverReady:true,authenticated:true});
      check("서버·로그인 후 구성 가능", ready.vpnConfig === "available" && ready.canIssueConfig);
      check("설치형 PWA 상태", getPlatformReadiness({platformId:"macos",standalone:true}).webApp === "installed");
      check("웹앱과 터널 역할 분리", ready.truth.includes("웹앱") && ready.truth.includes("WireGuard"));
      check("Firefox PC 웹 fallback", getInstallGuidance("windows","firefox").mode === "web_fallback");
      check("Safari Mac Dock 안내", getInstallGuidance("macos","safari").copy.includes("Dock"));
      check("iOS 공유 메뉴 안내", getInstallGuidance("ios","chrome").copy.includes("공유 메뉴"));
      check("프로필 동결", Object.isFrozen(PLATFORM_PROFILES) && Object.values(PLATFORM_PROFILES).every(Object.isFrozen));
      return out;
    }""", f"{base}/20_SRC/app/platform_support.js")
    browser.close()

failed = [name for name, ok in checks if not ok]
for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed: raise SystemExit(f"플랫폼 지원 검사 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
