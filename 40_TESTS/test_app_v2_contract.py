#!/usr/bin/env python3
"""v2 R3·R4와 선행 R5 UI 계약을 실제 생성 산출물에서 검사한다."""
from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import build_app_v2  # noqa: E402


STATES = ("setup_needed", "checking", "protected", "limited", "disconnected")
MOMENTS = ("public-wifi", "travel", "region-web", "connection-help")
BUCKETS = ("free", "earned", "paid")
FAKE_RUNTIME = ("일본 · 도쿄", "대한민국 · 서울", "예상 42ms", "198.51.100.24", "연결됨 · 00:01")


def r3_contract(html: str) -> bool:
    return (
        'data-server-count="0"' in html
        and "현재 가동 서버가 없습니다" in html
        and all(f'data-state="{state}"' in html for state in STATES)
        and all(f"{state}:" in html for state in STATES)
        and not any(token in html for token in FAKE_RUNTIME)
        and "실제 터널과 외부 확인이 모두 성공한 경우만 표시합니다" in html
    )


def r4_contract(html: str) -> bool:
    return (
        all(f'data-moment="{moment}"' in html for moment in MOMENTS)
        and len(re.findall(r'data-moment="[^"]+"', html)) == 4
        and "data-direct-check" in html
        and "저장하거나 전송하지 않습니다" in html
    )


def r5_ui_contract(html: str) -> bool:
    return (
        all(f'data-wallet-bucket="{bucket}"' in html for bucket in BUCKETS)
        and all(f'data-wallet-view="{bucket}"' in html for bucket in BUCKETS)
        and 'id="morePack"' in html
        and 'id="showMorePack"' in html
        and "100GB·300GB는" in html
        and 'data-gb="100"' not in html
        and 'data-gb="300"' not in html
    )


def main() -> None:
    before = build_app_v2.build().read_bytes()
    after = build_app_v2.build().read_bytes()
    html = after.decode("utf-8")
    checks = [
        ("생성 결정론", before == after),
        ("v2.6 고객용 서비스 홈·4메뉴", all(value in html for value in ('data-service-shell', 'data-svc-view="home"', 'data-svc-view="locations"', 'data-svc-view="usage"', 'data-svc-view="account"', "무료 1GB로 시작", "상태를 꾸미지 않습니다"))),
        ("내부 검토 14화면 계약", set(re.findall(r'<section[^>]+data-screen="([^"]+)"', html)) == {"welcome", "consent", "setup", "home", "moments", "platforms", "protection", "locations", "wallet", "topup", "referral", "devices", "usage", "account"} and "화면 14개" in html and "INTERNAL REVIEW" in html and "query.get('review')==='1'" in html),
        ("R3 진실한 상태·빈 카탈로그", r3_contract(html)),
        ("R4 순간 4종·직접 경로", r4_contract(html)),
        ("R5 세 지갑 UI 선행", r5_ui_contract(html)),
        ("R7 추천 진행 UI", 'data-referral-rail' in html and "양쪽에 500MB" in html and "누적 100MB" in html),
        ("Moment 30 국가·목적·요금 추천 UI", all(value in html for value in ('data-screen="moments"', 'id="currentCountrySelect"', 'id="destinationCountrySelect"', 'data-tier-filter="free"', 'data-tier-filter="paid"', 'data-tier-filter="premium_planned"', '30개 사용 순간'))),
        ("모든 기기 역할 분리 UI", all(value in html for value in ('data-screen="platforms"', 'data-platform="windows"', 'data-platform="macos"', 'data-platform="linux"', 'data-platform="android"', 'data-platform="ios"', 'freeflexRequestInstall', '공식 WireGuard'))),
        ("PC 앱 모드·설치 시작점", all(value in html for value in ('id="appModeToggle"', "ffvpn-app-mode", "get('view')==='app'", "dataset.appLayoutSafe", "width:min(100%,760px)"))),
        ("API 미설정 기본값·모듈 진입점", '<meta name="freeflex-api-base" content="">' in html and 'src="./pwa_runtime.js"' in html and 'id="createProfileButton"' in html),
        ("claim referrer 차단", '<meta name="referrer" content="no-referrer">' in html),
        ("API READY 표시·R8 오표기 금지", "API READY" in html and "R8 API READY" not in html),
        ("연결 검사는 실제 보호 성공을 만들지 않음", "setConnectionState('protected')" not in html),
        ("영속 목적 저장 미사용", "ffvpn-moment" not in html and "localStorage.setItem('moment" not in html),
        ("오클루전 검사가 순간 4개와 빠른 메뉴 2개를 함께 소비", ".moment-card[data-moment], [data-screen=\"home\"] .quick[data-go]" in html and "targets.length===6" in html),
        ("음성 대조 R3: 가짜 위치 주입 거부", not r3_contract(html + "일본 · 도쿄")),
        ("음성 대조 R4: 순간 하나 제거 거부", not r4_contract(html.replace('data-moment="travel"', 'data-removed="travel"', 1))),
        ("음성 대조 R5: 보상 지갑 제거 거부", not r5_ui_contract(html.replace('data-wallet-bucket="earned"', 'data-removed="earned"', 1))),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"v2 앱 계약 {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
