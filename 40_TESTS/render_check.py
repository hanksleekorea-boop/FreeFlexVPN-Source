#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실렌더 검사 — 산출물을 '소비자와 같은 방식'으로 읽는다.

브라우저로 열고(=화면), PWA 매니페스트는 base64 디코드 후 JSON 파싱,
아이콘은 PNG 매직넘버 + IHDR 실제 크기, 수치는 렌더된 텍스트에서 확인한다.
정적 문자열 검색으로는 JS 계산 결과를 볼 수 없으므로 반드시 렌더한다.

    python3 40_TESTS/render_check.py
"""
import base64, json, os, re, struct, sys, asyncio, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "70_TOOLS"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "20_SRC"))
import fkvpaths, cost_model

try:
    from playwright.async_api import async_playwright
except ImportError:
    raise SystemExit("SKIP-불가: playwright 미설치 — 이 검사는 건너뛸 수 없다. 설치 후 재실행하라.")

ROOT = fkvpaths.root()
LIVE = cost_model.contracts()
def money(v): return f"{int(round(v)):,}"

# 파일별로 렌더된 화면에 반드시 보여야 하는 수치 (계약 원장에서 파생)
EXPECT = {
    "FreeFlexVPN_비용계산서.html": [
        money(LIVE["free_tier"]["month_01_krw"]), money(LIVE["free_tier"]["month_12_krw"]),
        money(LIVE["free_tier"]["year1_krw"]), money(LIVE["free_tier"]["year3_krw"])],
    "VPN_20개국_분산_비용최적화.html": [
        money(LIVE["dist20"]["low_krw"]), money(LIVE["dist20"]["safe_krw"]),
        money(LIVE["dist20"]["focus_krw"])],
    "종량제_VPN_가격패키지_설계.html": [money(p["price"]) for p in LIVE["packs"]],
}

def png_dims(raw: bytes):
    if raw[:8] != b"\x89PNG\r\n\x1a\n": return None
    if raw[12:16] != b"IHDR": return None
    w, h = struct.unpack(">II", raw[16:24])
    return w, h

CHECKS, FAILS = [], []
def rec(label, ok, detail=""):
    CHECKS.append(label)
    if not ok: FAILS.append((label, detail))

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for f in fkvpaths.deliverables():
            page = await browser.new_page(viewport={"width": 1200, "height": 1400})
            errs = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(f"PAGEERROR {e}"))
            await page.goto(f.as_uri())
            await page.wait_for_timeout(500)
            name = f.name

            rec(f"R:{name} 렌더 콘솔 에러 0", len(errs) == 0, "; ".join(errs[:3]))
            title = await page.title()
            rec(f"R:{name} 제목 존재", bool(title.strip()), title)
            body = await page.inner_text("body")
            rec(f"R:{name} 본문 200자 이상 렌더", len(body) > 200, f"{len(body)}자")
            rec(f"R:{name} 구 브랜드 미노출", "Free Korea VPN" not in body, "")

            # PWA 매니페스트 — 소비자(브라우저)와 같은 방식: base64 디코드 → JSON 파싱
            href = await page.get_attribute("link[rel=manifest]", "href")
            ok_m, mf = False, {}
            if href and "base64," in href:
                try:
                    mf = json.loads(base64.b64decode(href.split("base64,", 1)[1]).decode("utf-8"))
                    ok_m = True
                except Exception as e:
                    mf = {"_err": str(e)}
            rec(f"M:{name} 매니페스트 base64 디코드 후 JSON 파싱", ok_m, str(mf)[:80])
            if ok_m:
                rec(f"M:{name} 필수 필드(name·start_url·display·icons)",
                    all(k in mf for k in ("name", "start_url", "display", "icons")), str(sorted(mf))[:80])
                rec(f"M:{name} FreeFlexVPN 브랜드",
                    str(mf.get("name", "")).startswith(LIVE["meta"]["product_name"]),
                    str(mf.get("name", "")))
                sizes = {}
                for ic in mf.get("icons", []):
                    src = ic.get("src", "")
                    if "base64," not in src: continue
                    raw = base64.b64decode(src.split("base64,", 1)[1])
                    d = png_dims(raw)
                    if d: sizes[d] = sizes.get(d, 0) + 1
                rec(f"I:{name} 아이콘 PNG 매직넘버·IHDR 192px 존재", (192, 192) in sizes, str(sizes))
                rec(f"I:{name} 아이콘 PNG IHDR 512px 존재", (512, 512) in sizes, str(sizes))
                rec(f"I:{name} SVG 아이콘 미사용(Android 설치 실패 방지)",
                    not any("svg" in (ic.get("src", "") + ic.get("type", "")).lower()
                            for ic in mf.get("icons", [])), "")
            for needle in EXPECT.get(name, []):
                rec(f"V:{name} 렌더 텍스트에 {needle} 존재", needle in body, "")
            await page.close()
        await browser.close()

asyncio.run(run())
n = len(CHECKS)
if FAILS:
    for label, detail in FAILS: print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"실렌더 검사 {n-len(FAILS)}/{n} 통과 · 실패 {len(FAILS)}")
print(f"실렌더 검사 {n}/{n} 통과")
