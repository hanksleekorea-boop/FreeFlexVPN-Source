#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공개 FreeFlexVPN 앱 셸의 UI·PWA·정직 고지 계약을 검사한다."""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def png_size(path: pathlib.Path) -> tuple[int, int] | None:
    raw = path.read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) < 24:
        return None
    return struct.unpack(">II", raw[16:24])


def app_contract(html: str) -> bool:
    return all(token in html for token in ('<section class="svc-shell" data-service-shell', 'data-svc-view="home"', 'data-svc-view="locations"', 'data-svc-view="usage"', 'data-svc-view="account"', "무료 1GB로 시작", "상태를 꾸미지 않습니다"))


def main() -> None:
    app = (ROOT / "app.html").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    qr_evidence = json.loads((ROOT / "app-qr-evidence.json").read_text(encoding="utf-8"))
    qr_raw = (ROOT / "app-qr.png").read_bytes()
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    check("v2.6 서비스 UI 표식", app_contract(app))
    declared = re.search(r"화면\s*(\d+)개", app)
    screens = re.findall(r'<section[^>]+data-screen="([^"]+)"', app)
    check("화면 수 자기 일치", bool(declared) and int(declared.group(1)) == len(screens))
    check("내부 검토 14화면 보존", len(screens) == 14 and {"moments", "platforms", "protection", "wallet", "referral"}.issubset(screens) and "INTERNAL REVIEW" in app)
    check("화면 이름 중복 없음", len(screens) == len(set(screens)))
    check("고객 기본화면과 내부 검토 분리", "review-mode" in app and "query.get('review')==='1'" in app)
    check("R3 실제 서버 0대", 'data-server-count="0"' in app and "현재 가동 서버가 없습니다" in app)
    check("R3 보호 상태 5종", all(f'data-state="{state}"' in app for state in ("setup_needed", "checking", "protected", "limited", "disconnected")))
    check("R3 가짜 위치·지연시간 제거", not any(token in app for token in ("일본 · 도쿄", "대한민국 · 서울", "예상 42ms", "198.51.100.24")))
    check("R4 순간 카드 4종", len(re.findall(r'data-moment="[^"]+"', app)) == 4)
    check("R4 직접 경로·목적 비저장", "data-direct-check" in app and "저장하거나 전송하지 않습니다" in app)
    check("R5 세 지갑 UI", all(f'data-wallet-bucket="{bucket}"' in app for bucket in ("free", "earned", "paid")))
    check("R5 지갑 화면·라이트 팩", all(f'data-wallet-view="{bucket}"' in app for bucket in ("free", "earned", "paid")) and 'data-gb="100"' not in app and 'data-gb="300"' not in app)
    check("R7 양쪽 보상 화면", 'data-screen="referral"' in app and "양쪽에 500MB" in app and "누적 100MB" in app)
    check("Moment 30 국가·목적·단계", all(token in app for token in ('data-screen="moments"', 'id="currentCountrySelect"', 'id="destinationCountrySelect"', 'data-tier-filter="premium_planned"', 'subscription-arbitrage')))
    check("PC·모바일·PWA 역할 분리", all(token in app for token in ('data-screen="platforms"', 'data-platform="windows"', 'data-platform="macos"', 'data-platform="linux"', 'data-platform="android"', 'data-platform="ios"', '공식 WireGuard')))
    check("PC 앱 모드·설치 시작점", all(token in app for token in ('id="appModeToggle"', "ffvpn-app-mode", "dataset.appLayoutSafe", "get('view')==='app'")))
    check("가격 지불의사 미검증 고지", "지불의사 미검증" in app)
    check("랜딩 서비스 진입 링크", 'href="app.html"' in index and "무료 1GB로 시작" in index)
    check("랜딩 알파·체험 문구 제거", "개발 진행 중" not in index and "앱 화면 체험하기" not in index)
    check("QR 공개 대상 일치", qr_evidence.get("target_url") == qr_evidence.get("decoded_payload") == "https://storage.googleapis.com/freeflexvpn-public-oceanic-abacus-477201-f3/app.html")
    check("QR 해시 일치", qr_evidence.get("sha256") == hashlib.sha256(qr_raw).hexdigest())
    check("브라우저 오클루전 음성 판정 가능", "dataset.layoutSafe=safe?'pass':'fail'" in app and "elementFromPoint" in app)

    manifest_match = re.search(
        r'<link rel="manifest" href="data:application/manifest\+json;base64,([^"]+)"', app
    )
    manifest = {}
    if manifest_match:
        try:
            manifest = json.loads(base64.b64decode(manifest_match.group(1)).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            manifest = {}
    check("단일 base64 매니페스트", bool(manifest) and manifest.get("start_url") == "./app.html?view=app" and manifest.get("id") == "./app.html" and manifest.get("scope") == "./")
    check("PNG 아이콘 192", png_size(ROOT / "icon-192.png") == (192, 192))
    check("PNG 아이콘 512", png_size(ROOT / "icon-512.png") == (512, 512))
    check("매니페스트 아이콘 계약", {icon.get("sizes") for icon in manifest.get("icons", [])} == {"192x192", "512x512"})
    check("Android 설치 흐름", "beforeinstallprompt" in app and "appinstalled" in app)
    check("iOS 설치 안내", "홈 화면에 추가" in app and "iphone|ipad|ipod" in app)
    check("standalone 억제", "display-mode: standalone" in app and "navigator.standalone" in app)
    check("24시간 닫기와 저장 실패 안전", "86400000" in app and "localStorage.setItem" in app and "catch{}" in app)
    check("서비스워커 앱 셸", all(token in worker for token in ("app.html", "moment_catalog.js", "platform_support.js", "icon-192.png", "icon-512.png", "CACHE_NAME")))
    check("음성 대조: 서비스 표식 변조 거부", not app_contract(app.replace('<section class="svc-shell" data-service-shell', '<section class="svc-shell" data-removed-shell', 1)))

    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"공개 앱 셸 검사 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
