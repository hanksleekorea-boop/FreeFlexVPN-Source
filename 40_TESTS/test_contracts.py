#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약 검사 — 모델 왕복 · 문서 수치 일치 · 하네스 자기검사.

    python3 40_TESTS/test_contracts.py
    CONDOLINK_LIST_CHECKS=1 python3 40_TESTS/test_contracts.py   # 라벨만 출력
규율: 버전·개수·수치를 이 파일에 하드코딩하지 않는다. 전부 산출물에서 읽어 계산한다.
"""
import json, os, re, sys, zipfile, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "70_TOOLS"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "20_SRC"))
import fkvpaths, cost_model

ROOT = fkvpaths.root()
CHECKS, FAILS = [], []

def check(label, fn):
    CHECKS.append(label)
    if os.environ.get("CONDOLINK_LIST_CHECKS") or os.environ.get("FKV_LIST_CHECKS"):
        return
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    if not ok:
        FAILS.append((label, detail))

def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)

def money(v): return f"{int(round(v)):,}"

# ── A. 모델 왕복: CONTRACTS.json 이 cost_model.py 에서 재생성되는가 ──────
LEDGER = json.loads((ROOT / "10_STATE" / "CONTRACTS.json").read_text(encoding="utf-8"))
LIVE   = cost_model.contracts()

def _walk(a, b, path=""):
    if isinstance(a, dict):
        if set(a) != set(b): return False, f"{path} 키 불일치"
        for k in a:
            ok, d = _walk(a[k], b[k], f"{path}.{k}")
            if not ok: return ok, d
        return True, ""
    if isinstance(a, list):
        if len(a) != len(b): return False, f"{path} 길이 {len(a)}≠{len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            ok, d = _walk(x, y, f"{path}[{i}]")
            if not ok: return ok, d
        return True, ""
    return (a == b), (f"{path} {a!r}≠{b!r}" if a != b else "")

check("A1 계약 원장 왕복 — CONTRACTS.json == cost_model 재계산",
      lambda: _walk(LEDGER, LIVE))
check("A2 단위 원가 = 안전구성 총액 ÷ 200TB",
      lambda: (abs(LIVE["unit"]["cost_per_gb_krw"]
                   - LIVE["dist20"]["safe_krw"] / (LIVE["dist20"]["total_tb"] * 1000)) < 0.01, ""))
check("A3 구성 비용 순서 — 집중8 < 최저가 < 안전",
      lambda: (LIVE["dist20"]["focus_krw"] < LIVE["dist20"]["low_krw"] < LIVE["dist20"]["safe_krw"], ""))
check("A4 무료 연차 합계 = 월별 합",
      lambda: (LIVE["free_tier"]["year_total_krw"]
               == sum(LIVE["free_tier"][k] for k in ("year1_krw","year2_krw","year3_krw")), ""))
check("A5 볼륨 할인 배수가 업계 표준 3~4배 구간",
      lambda: (3.0 <= LIVE["volume_discount_ratio"] <= 4.0, str(LIVE["volume_discount_ratio"])))
check("A6 모든 충전팩 마진율 90% 이상",
      lambda: (all(p["margin_rate"] >= 90 for p in LIVE["packs"]), ""))
check("A7 충전팩 GB당 단가 단조 감소(용량↑ → 단가↓)",
      lambda: (all(a["per_gb"] > b["per_gb"] for a, b in zip(LIVE["packs"], LIVE["packs"][1:])), ""))
DECISIONS = (ROOT / "10_STATE" / "DECISIONS.md").read_text(encoding="utf-8")
CAP_IN_DECISION = re.search(r"1인 월\s*([0-9.]+)GB", DECISIONS)
check("A8 사용자 확정 무료 한도 = 모델 무료 한도",
      lambda: (CAP_IN_DECISION is not None and
               float(CAP_IN_DECISION.group(1)) == LIVE["meta"]["cap_gb_free"],
               "DECISIONS와 cost_model 불일치"))
check("A9 사용자 확정 브랜드 = 모델 브랜드",
      lambda: (LIVE["meta"]["product_name"] in DECISIONS, LIVE["meta"]["product_name"]))
check("A10 충전 잔액 무기한 계약",
      lambda: (not LIVE["meta"]["topup_expires"] and "충전 잔액은 무기한" in DECISIONS, ""))

# ── B. 문서 수치 일치: 손으로 옮겨 적은 값이 남아 있지 않은가 ───────────
DOC_KEYS = [
    ("free_tier", "month_01_krw"), ("free_tier", "month_12_krw"),
    ("free_tier", "month_24_krw"), ("free_tier", "month_36_krw"),
    ("free_tier", "year1_krw"), ("free_tier", "year2_krw"), ("free_tier", "year3_krw"),
    ("dist20", "low_krw"), ("dist20", "safe_krw"), ("dist20", "focus_krw"),
]
DOCS = {p.name: docx_text(p) for p in fkvpaths.documents()}
ALLDOC = "\n".join(DOCS.values())
for grp, key in DOC_KEYS:
    val = LIVE[grp][key]
    check(f"B:{grp}.{key} = {money(val)}원 이 문서에 존재",
          (lambda v=val: (money(v) in ALLDOC, f"{money(v)} 미발견")))
check("B:cost_per_gb 문서 표기 일치",
      lambda: (f"{LIVE['unit']['cost_per_gb_krw']:.2f}" in ALLDOC, ""))
for p in LIVE["packs"]:
    check(f"B:pack {p['name']} {p['gb']}GB {money(p['price'])}원 문서 일치",
          (lambda q=p: (money(q["price"]) in ALLDOC and money(q["per_gb"]) in ALLDOC, "")))

# ── C. 하네스 자기검사 — 하드코딩 금지 ────────────────────────────────
SELF = pathlib.Path(__file__).read_text(encoding="utf-8")
BODY = SELF.split("# ── C.")[0]
check("N1 검사 소스에 원화 수치 하드코딩 없음",
      lambda: (not re.search(r"\b\d{1,3}(,\d{3})+\b", BODY), "쉼표 수치 발견"))
# 바늘 문자열을 조립해서 만든다 — 리터럴로 쓰면 이 파일 자신이 걸린다(자기참조 함정)
_NEEDLES = ["/" + str(n) for n in (179, 350, 130)] + ["\ucd1d " + str(30)]
check("N2 검사 소스에 검사 총계 하드코딩 없음",
      lambda: (not any(x in BODY for x in _NEEDLES), ""))
check("N3 검사 소스에 버전 문자열 하드코딩 없음",
      lambda: (not re.search(r"v\d+\.\d+\.\d+", BODY), ""))
check("N4 계약 원장이 모델에서 생성됨을 자기 기술",
      lambda: (LIVE["meta"]["generated_from"].endswith("cost_model.py"), ""))

# ── D. 구조 ────────────────────────────────────────────────────────────
check("D1 배포 미러 HTML 1개 이상",
      lambda: (len(fkvpaths.deliverables()) > 0, ""))
check("D2 문서 산출물 1개 이상",
      lambda: (len(fkvpaths.documents()) > 0, ""))
check("D3 모든 배포 HTML 이 단일 파일(외부 상대참조 없음)",
      lambda: (all("src=\"./" not in p.read_text(encoding="utf-8", errors="ignore")
                   and "href=\"./" not in p.read_text(encoding="utf-8", errors="ignore")
                   for p in fkvpaths.deliverables()), ""))
check("D4 배포 HTML 에 구 브랜드 미노출",
      lambda: (all("Free Korea VPN" not in p.read_text(encoding="utf-8", errors="ignore")
                   for p in fkvpaths.deliverables()), ""))
check("D5 비용 계산서가 FreeFlexVPN 이름으로 존재",
      lambda: (any(p.name.startswith(LIVE["meta"]["product_name"])
                   and "비용계산서" in p.name for p in fkvpaths.deliverables()), ""))

if os.environ.get("CONDOLINK_LIST_CHECKS") or os.environ.get("FKV_LIST_CHECKS"):
    for c in CHECKS: print(c)
    sys.exit(0)
n = len(CHECKS)
if FAILS:
    for label, detail in FAILS: print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"계약 검사 {n-len(FAILS)}/{n} 통과 · 실패 {len(FAILS)}")
print(f"계약 검사 {n}/{n} 통과")
