#!/usr/bin/env python3
"""Chromium이 Moment 30 ES 모듈을 실제 소비해 계약과 음성 대조를 검증한다."""
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
    page.goto(f"{base}/20_SRC/app/moment_catalog.js")
    checks = page.evaluate("""async (moduleUrl) => {
      const { MOMENTS, COUNTRY_PROFILES, recommendMoments } = await import(moduleUrl);
      const checks = [];
      const check = (name, condition) => checks.push([name, Boolean(condition)]);
      check("정확히 30개", MOMENTS.length === 30);
      check("순위 1~30", MOMENTS.every((m, i) => m.rank === i + 1));
      check("ID 고유", new Set(MOMENTS.map(m => m.id)).size === 30);
      check("무료 존재", MOMENTS.some(m => m.tier === "free"));
      check("유료 존재", MOMENTS.some(m => m.tier === "paid"));
      check("프리미엄 예정 존재", MOMENTS.some(m => m.tier === "premium_planned"));
      check("비지원 존재", MOMENTS.some(m => m.tier === "none"));
      check("중국 제한 프로필", COUNTRY_PROFILES.CN.policy === "specialized_required");
      check("인도 제공자 규정 프로필", COUNTRY_PROFILES.IN.policy === "provider_compliance");
      check("UAE 합법 목적 프로필", COUNTRY_PROFILES.AE.policy === "legal_use_only");

      const live = recommendMoments({ destinationCountry: "SG", availableCountryCodes: ["SG"], catalogKnown: true });
      const wifi = live.recommendations.find(m => m.id === "cafe-wifi");
      const research = live.recommendations.find(m => m.id === "local-search-qa");
      check("가까운 서버 추천 활성", wifi.actionable && wifi.destination === "AUTO_NEAREST");
      check("실제 목적국 서버 추천 활성", research.actionable && research.destination === "SG");

      const missing = recommendMoments({ destinationCountry: "JP", availableCountryCodes: ["SG"], catalogKnown: true });
      check("없는 목적국 서버 비활성", !missing.recommendations.find(m => m.id === "local-search-qa").actionable);
      const unknown = recommendMoments({ destinationCountry: "SG", availableCountryCodes: ["SG"], catalogKnown: false });
      check("서버 목록 미확인 비활성", !unknown.recommendations.find(m => m.id === "local-search-qa").actionable);

      const blocked = recommendMoments({ destinationCountry: "IN", availableCountryCodes: ["IN", "AR"], catalogKnown: true });
      const arbitrage = blocked.recommendations.find(m => m.id === "subscription-arbitrage");
      const iplayer = blocked.recommendations.find(m => m.id === "iplayer-outside-uk");
      check("구독료 우회 목적 비지원", arbitrage.support === "not_supported" && !arbitrage.actionable && arbitrage.destination === null);
      check("BBC 국외 우회 비지원", iplayer.support === "not_supported" && !iplayer.actionable);

      const china = recommendMoments({ currentCountry: "CN", destinationCountry: "SG", availableCountryCodes: ["SG"], catalogKnown: true });
      check("중국에서 일반 연결 성공 미보장", china.countryPolicy.policy === "specialized_required" && china.recommendations.every(m => !m.actionable));
      check("제한 국가 순간은 전문 서비스", china.recommendations.find(m => m.id === "restricted-network").support === "specialized_required");
      const paidOnly = recommendMoments({ tier: "paid" });
      check("요금 필터", paidOnly.total > 0 && paidOnly.recommendations.every(m => m.tier === "paid"));
      const search = recommendMoments({ query: "와이파이" });
      check("목적 검색", search.total >= 3 && search.recommendations.every(m => `${m.title} ${m.why}`.includes("와이파이")));
      check("카탈로그 동결", Object.isFrozen(MOMENTS) && MOMENTS.every(Object.isFrozen));
      return checks;
    }""", f"{base}/20_SRC/app/moment_catalog.js")
    browser.close()

failed = [name for name, passed in checks if not passed]
for name, passed in checks:
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
if failed:
    raise SystemExit(f"Moment 30 검사 실패: {', '.join(failed)}")
print(f"RESULT: {len(checks)}/{len(checks)} passed")
