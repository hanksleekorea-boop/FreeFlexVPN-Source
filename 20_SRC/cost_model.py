#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FreeFlexVPN — 원가·수익 모델 단일 정본 (single source of truth).

이 파일이 계산의 유일한 출처다. 문서·HTML·검사에 나오는 모든 수치는
여기서 파생되어야 하며, 손으로 옮겨 적은 값이 있으면 40_TESTS/test_contracts.py 가 잡는다.

    python3 20_SRC/cost_model.py            # 사람이 읽는 요약
    python3 20_SRC/cost_model.py --json     # CONTRACTS.json 내용 출력
"""
import datetime, json, math, re, sys
from urllib.parse import urlsplit

# ── 실측 단가 (2026-07-30 공급자 공개 가격표에서 확인) ────────────────────
FX = {"usd": 1470.0, "eur": 1720.0, "chf": 1830.0}   # 원/통화

PROVIDER_GRADES = ("안전", "공격", "미확인")
TRAFFIC_MODELS = ("included_tb", "unmetered", "bandwidth_blocks")
VPN_RESALE_STATUSES = ("allowed", "unknown", "forbidden")


def _positive_number(value, field, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field}는 유한한 숫자여야 합니다")
    number = float(value)
    if number < 0 or (number == 0 and not allow_zero):
        raise ValueError(f"{field}는 {'0 이상' if allow_zero else '0 초과'}이어야 합니다")
    return number


def _currency(value, field):
    if value not in FX:
        raise ValueError(f"{field} 통화는 {sorted(FX)} 중 하나여야 합니다")
    return value


def _pricing_component(value, index):
    if not isinstance(value, dict):
        raise ValueError(f"pricing.components[{index}]는 객체여야 합니다")
    label = value.get("label")
    if not isinstance(label, str) or not label.strip() or len(label) > 80:
        raise ValueError(f"pricing.components[{index}].label이 비어 있거나 너무 깁니다")
    cur = _currency(value.get("currency"), f"pricing.components[{index}]")
    amount = _positive_number(value.get("amount"), f"pricing.components[{index}].amount", allow_zero=True)
    if value.get("cadence") != "monthly":
        raise ValueError("공급자 비교 입력은 월 환산된 구성요소만 받습니다")
    return {"label": label.strip(), "currency": cur, "amount": amount,
            "krw": round(krw(cur, amount), 4)}


def validate_provider_input(spec):
    """신규 공급자 입력을 정규화한다. 기존 원가표에 자동 편입하지 않는다.

    혼합 통화는 구성요소별 원화 환산 뒤 합산하고, 무제한·속도블록 상품은
    fair-use·속도캡·추가 블록 가격이 빠지면 실패한다.
    """
    if not isinstance(spec, dict):
        raise ValueError("공급자 입력은 객체여야 합니다")
    provider_id = spec.get("provider_id")
    plan_id = spec.get("plan_id")
    for value, field in ((provider_id, "provider_id"), (plan_id, "plan_id")):
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", value):
            raise ValueError(f"{field} 형식이 올바르지 않습니다")
    countries = spec.get("countries")
    if (not isinstance(countries, list) or not countries
            or any(not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code) for code in countries)):
        raise ValueError("countries는 중복 없는 ISO 3166-1 alpha-2 목록이어야 합니다")
    if len(set(countries)) != len(countries):
        raise ValueError("countries에 중복이 있습니다")
    checked_on = spec.get("checked_on")
    try:
        parsed_date = datetime.date.fromisoformat(checked_on)
    except (TypeError, ValueError) as exc:
        raise ValueError("checked_on은 YYYY-MM-DD여야 합니다") from exc
    if parsed_date > datetime.date.today():
        raise ValueError("checked_on은 미래일 수 없습니다")
    source_url = spec.get("source_url")
    parsed_url = urlsplit(source_url) if isinstance(source_url, str) else None
    if (parsed_url is None or parsed_url.scheme != "https" or not parsed_url.netloc
            or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment):
        raise ValueError("source_url은 자격증명·query·fragment가 없는 HTTPS 가격/약관 URL이어야 합니다")
    grade = spec.get("grade")
    if grade not in PROVIDER_GRADES:
        raise ValueError(f"grade는 {PROVIDER_GRADES} 중 하나여야 합니다")
    port_mbps = _positive_number(spec.get("port_mbps"), "port_mbps")
    resale = spec.get("vpn_resale_status")
    if resale not in VPN_RESALE_STATUSES:
        raise ValueError(f"vpn_resale_status는 {VPN_RESALE_STATUSES} 중 하나여야 합니다")
    if resale == "forbidden":
        raise ValueError("VPN 재판매가 금지된 상품은 후보에 넣을 수 없습니다")
    if resale == "unknown" and grade == "안전":
        raise ValueError("VPN 재판매 약관이 미확인이면 안전 등급을 줄 수 없습니다")

    pricing = spec.get("pricing")
    if not isinstance(pricing, dict):
        raise ValueError("pricing 객체가 필요합니다")
    raw_components = pricing.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise ValueError("pricing.components가 필요합니다")
    components = [_pricing_component(item, index) for index, item in enumerate(raw_components)]
    traffic = pricing.get("traffic")
    if not isinstance(traffic, dict) or traffic.get("model") not in TRAFFIC_MODELS:
        raise ValueError(f"pricing.traffic.model은 {TRAFFIC_MODELS} 중 하나여야 합니다")
    model = traffic["model"]
    normalized_traffic = {"model": model}
    if model == "included_tb":
        normalized_traffic["included_tb"] = _positive_number(traffic.get("included_tb"), "included_tb")
        overage = traffic.get("overage")
        if not isinstance(overage, dict):
            raise ValueError("included_tb 상품에는 overage가 필요합니다")
        cur = _currency(overage.get("currency"), "overage")
        amount = _positive_number(overage.get("amount_per_tb"), "overage.amount_per_tb", allow_zero=True)
        normalized_traffic["overage"] = {
            "currency": cur, "amount_per_tb": amount,
            "krw_per_tb": round(krw(cur, amount), 4),
        }
    elif model == "unmetered":
        status = traffic.get("fair_use_status")
        if status not in ("published", "unknown"):
            raise ValueError("unmetered 상품은 fair_use_status를 명시해야 합니다")
        if status == "unknown" and grade == "안전":
            raise ValueError("fair-use가 미확인이면 안전 등급을 줄 수 없습니다")
        normalized_traffic["fair_use_status"] = status
        normalized_traffic["speed_cap_mbps"] = _positive_number(
            traffic.get("speed_cap_mbps", port_mbps), "speed_cap_mbps"
        )
    else:
        normalized_traffic["base_mbps"] = _positive_number(traffic.get("base_mbps"), "base_mbps")
        normalized_traffic["block_mbps"] = _positive_number(traffic.get("block_mbps"), "block_mbps")
        block = traffic.get("block_price")
        if not isinstance(block, dict):
            raise ValueError("bandwidth_blocks 상품에는 block_price가 필요합니다")
        cur = _currency(block.get("currency"), "block_price")
        amount = _positive_number(block.get("amount"), "block_price.amount")
        normalized_traffic["block_price"] = {
            "currency": cur, "amount": amount, "krw": round(krw(cur, amount), 4),
        }

    commitment_months = spec.get("commitment_months", 1)
    if not isinstance(commitment_months, int) or isinstance(commitment_months, bool) or commitment_months < 1:
        raise ValueError("commitment_months는 1 이상의 정수여야 합니다")
    return {
        "provider_id": provider_id,
        "plan_id": plan_id,
        "countries": list(countries),
        "checked_on": checked_on,
        "source_url": source_url,
        "grade": grade,
        "vpn_resale_status": resale,
        "port_mbps": port_mbps,
        "commitment_months": commitment_months,
        "price_components": components,
        "mixed_currency": len({item["currency"] for item in components}) > 1,
        "monthly_base_krw": round(sum(item["krw"] for item in components), 4),
        "traffic": normalized_traffic,
        "admission": "validated_input_only_not_added_to_country_options",
    }

RATES = {
    # 이름                     통화    월단가   포트Mbps  포함TB  초과$/TB
    "contabo_vps10":          ("eur",   6.85,     200,   None,   None),   # 도쿄 등, 트래픽 무제한(fair use)
    "contabo_de":             ("eur",   4.50,     200,   None,   None),
    "hetzner_cx23":           ("eur",   5.99,     300,     20,   1.17),   # 5.49 + IPv4 0.50
    "ovh_vps1":               ("usd",   4.54,     500,   None,   None),   # 무제한 명시
    "ovh_eco":                ("usd",  11.10,     500,   None,   None),
    "infomaniak_lite":        ("chf",   2.70,     500,   None,   None),
    "akamai_nanode":          ("usd",   5.00,    1000,      1,   5.00),
    "akamai_saopaulo":        ("usd",   7.00,    1000,      1,   7.00),
    "akamai_jakarta":         ("usd",   6.00,    1000,      1,  15.00),
    "vultr_1gb":              ("usd",   5.00,    1000,      1,  10.00),
    "blastvps_1g_unmetered":  ("usd",  89.99,    1000,   None,   None),
    "onegservers_10g":        ("usd", 199.97,   10000,   None,   None),
    "ish_medium_eu":          ("usd",  21.24,     222,   None,   None),   # + 10Mbps당 $2
    "ish_premium_asia":       ("usd",  31.99,     222,   None,   None),   # + 10Mbps당 $15
    "ultahost_business":      ("usd",   4.80,     100,   None,   None),   # 24개월 약정가
    "zappie":                 ("usd",   4.50,    1000,    0.2,   None),
}
ISH_BLOCK = {"eu": 2.0, "asia": 15.0}   # 추가 대역폭 10Mbps당 USD

DOMAIN_YEAR   = 16000.0    # 원 — .com 원가
SMS_PER_MSG   = 20.0       # 원/건 — 국내 SMS 인증
PG_RATE       = 0.034 * 1.1  # 국내 PG 카드 3.4% + 수수료 VAT
SPARE         = 0.15       # 예비율(남용·차단 대응)
PEAK_FACTOR   = 3.0        # 월평균 대비 피크 배수
PRODUCT_NAME  = "FreeFlexVPN"
TARGET_SEGMENT = "light"
CAP_GB_FREE   = 1.0        # 무료 요금제 1인 월 상한
TOPUP_EXPIRES = False      # 충전 잔액은 무기한
BOOKKEEPING   = 100000.0
CLOSING_YEAR  = 300000.0
TELESALE_YEAR = 40500.0
PGFEE_YEAR    = 110000.0

def krw(cur, v): return v * FX[cur]
def tb_to_mbps(tb): return tb * 1e6 * 8 / (30 * 24 * 3600)   # 월 TB → 평균 Mbps
def peak_mbps(tb):  return tb_to_mbps(tb) * PEAK_FACTOR

# ── 1. 무료 요금제 성장 곡선 (1인 1GB 상한, 매월 +1,000명) ────────────────
def free_month(users, new_users=1000, cap=CAP_GB_FREE):
    tb   = users * cap / 1000.0
    peak = peak_mbps(tb)
    cur, unit, port, _, _ = RATES["contabo_vps10"]
    n_exit = max(1, math.ceil(peak / port))
    panel  = krw(*RATES["hetzner_cx23"][:2])
    server = n_exit * krw(cur, unit) + panel
    sms    = new_users * SMS_PER_MSG
    cost   = (server + DOMAIN_YEAR / 12) * (1 + SPARE) + sms
    return {"users": users, "tb": tb, "peak_mbps": peak, "nodes": n_exit + 1,
            "server": server, "sms": sms, "cost": cost}

def free_curve(months=36):
    return [free_month(1000 * m) for m in range(1, months + 1)]

# ── 2. 목적지 20개국 분산 (회원 1만명 × 20GB = 월 200TB) ─────────────────
SHARE = [("미국",39.78),("독일",10.15),("프랑스",7.89),("영국",6.87),("캐나다",4.58),
         ("네덜란드",4.32),("스위스",3.43),("호주",2.78),("오스트리아",2.62),("스웨덴",2.30),
         ("벨기에",2.15),("스페인",2.01),("일본",1.95),("덴마크",1.52),("아일랜드",1.46),
         ("이탈리아",1.44),("폴란드",1.38),("루마니아",1.25),("뉴질랜드",1.07),("싱가포르",1.04)]
TOTAL_TB_20 = 200.0

def _opt(name, cur, base, port, inc, ov, grade, note):
    return dict(name=name, cur=cur, base=base, port=port, inc=inc, ov=ov, grade=grade, note=note)

def _ish(region):
    """is*hosting: 무제한이나 속도캡. 필요 Mbps 만큼 10Mbps 블록을 추가 구매한다.
    블록 수는 그 국가가 실제로 담당할 대역폭에서 계산되므로 base 만 고정하고
    _cost() 에서 동적으로 더한다."""
    key = "ish_medium_eu" if region == "eu" else "ish_premium_asia"
    cur, base, port, _, _ = RATES[key]
    o = _opt(f"is*hosting({region}) + 대역폭", cur, base, port, None, None,
             "공격", "무제한이나 속도캡 → 10Mbps 블록 추가 구매")
    o["block_usd"] = ISH_BLOCK[region]
    return o

def _contabo(name, surcharge_usd):
    """Contabo 기본요금은 EUR, 지역 추가요금(도쿄·시드니 등)은 USD 로 고시된다.
    통화를 섞어 더하면 국가당 240~290원이 어긋나므로 원화로 환산해 고정한다."""
    o = _opt(name, "krw", 0.0, RATES["contabo_de"][2], None, None, "안전", "무제한(fair use)")
    o["krw_base"] = krw("eur", RATES["contabo_de"][1]) + krw("usd", surcharge_usd)
    return o

def _r(key, name, grade, note):
    cur, base, port, inc, ov = RATES[key]
    return _opt(name, cur, base, port, inc, ov, grade, note)

COUNTRY_OPTIONS = {
    "미국":     [_r("blastvps_1g_unmetered","BlastVPS 1Gbps unmetered","안전","진성 unmetered"),
                 _r("onegservers_10g","1GServers 10Gbps unmetered","안전","대규모 여유")],
    "독일":     [_r("ovh_vps1","OVHcloud VPS-1","안전","무제한 명시")],
    "프랑스":   [_r("ovh_vps1","OVHcloud VPS-1","안전","무제한 명시")],
    "영국":     [_r("ovh_vps1","OVHcloud VPS-1","안전","무제한 명시")],
    "캐나다":   [_r("ovh_vps1","OVHcloud VPS-1","안전","무제한 명시")],
    "폴란드":   [_r("ovh_vps1","OVHcloud VPS-1 바르샤바","안전","무제한 명시")],
    "스위스":   [_r("infomaniak_lite","Infomaniak VPS Lite","안전","무제한 500Mbps")],
    "이탈리아": [_r("ovh_eco","OVHcloud Eco 밀라노","안전","무제한 명시"),
                 _r("akamai_nanode","Akamai Milan","안전","1TB+초과 $5/TB")],
    "네덜란드": [_r("akamai_nanode","Akamai Amsterdam","안전","1TB+초과 $5/TB")],
    "스페인":   [_r("akamai_nanode","Akamai Madrid","안전","1TB+초과 $5/TB")],
    "스웨덴":   [_r("akamai_nanode","Akamai Stockholm","안전","1TB+초과 $5/TB")],
    "브라질":   [_r("akamai_saopaulo","Akamai São Paulo","안전","1TB+초과 $7/TB")],
    "일본":     [_contabo("Contabo VPS10 도쿄", 1.16),
                 _r("akamai_nanode","Akamai Tokyo","안전","1TB+초과 $5/TB")],
    "싱가포르": [_contabo("Contabo VPS10 싱가포르", 1.16),
                 _r("akamai_nanode","Akamai Singapore","안전","1TB+초과 $5/TB")],
    "호주":     [_contabo("Contabo VPS10 시드니", 0.96),
                 _r("ovh_eco","OVHcloud Eco 시드니","안전","무제한 명시"),
                 _r("akamai_nanode","Akamai Sydney","안전","1TB+초과 $5/TB")],
    "오스트리아":[_opt("OneProvider 유럽 평균가","usd",12.67,1000,None,None,"미확인","해당국 로케이션 미확인")],
    "뉴질랜드": [_opt("Zappie Host NZ(상위 플랜)","usd",30.00,1000,None,None,"미확인","상위 플랜 단가 미공개")],
    "포르투갈": [_r("ultahost_business","UltaHost Business","안전","상위요금제부터 무제한·24개월 약정가")],
}
for c in ("벨기에","덴마크","아일랜드","루마니아"):
    COUNTRY_OPTIONS[c] = [_ish("eu")]
for c in ("터키","태국","홍콩","말레이시아","페루","콜롬비아","아르헨티나"):
    COUNTRY_OPTIONS[c] = [_ish("asia")]
COUNTRY_OPTIONS["오스트리아"].append(_ish("eu"))
COUNTRY_OPTIONS["뉴질랜드"].append(_ish("asia"))
for c in ("네덜란드","스페인","스웨덴","이탈리아","브라질"):
    COUNTRY_OPTIONS[c].append(_ish("eu"))
COUNTRY_OPTIONS["미국"].insert(0, _opt("OneProvider LA (fair-use unmetered)","usd",12.00,1000,None,None,"공격","fair-use 정의 비공개"))
COUNTRY_OPTIONS["네덜란드"].insert(0, _opt("OneProvider Amsterdam","usd",12.66,1000,None,None,"공격","fair-use"))
COUNTRY_OPTIONS["스웨덴"].insert(0, _opt("OneProvider Stockholm","usd",12.72,1000,None,None,"공격","fair-use"))
COUNTRY_OPTIONS["스페인"].insert(0, _opt("OneProvider Madrid","usd",12.73,1000,None,None,"공격","fair-use"))

def _cost(o, tb, mb):
    n = max(1, math.ceil(mb / o["port"]))
    if o.get("krw_base"):
        return o["krw_base"] * n, n
    if o.get("block_usd"):
        blocks = math.ceil(mb / 10.0)
        return krw(o["cur"], o["base"]) + krw("usd", blocks * o["block_usd"]), 1
    if o["inc"] is None:
        return krw(o["cur"], o["base"]) * n, n
    extra = max(0.0, tb - o["inc"] * n)
    if extra > 0 and o["ov"] is None:
        return None, n
    return krw(o["cur"], o["base"]) * n + krw("usd", extra * (o["ov"] or 0)), n

PANEL_SPARE = 2   # 패널 + 예비 노드

def dist20(mode="safe"):
    """mode: 'low'(fair-use 라인 허용) | 'safe'(계약 명시 용량만)"""
    rows, total = [], 0.0
    for c, sh in SHARE:
        tb = TOTAL_TB_20 * sh / 100.0
        mb = peak_mbps(tb)
        cands = [o for o in COUNTRY_OPTIONS[c] if mode == "low" or o["grade"] != "공격"] or COUNTRY_OPTIONS[c]
        best = None
        for o in cands:
            v, n = _cost(o, tb, mb)
            if v is None: continue
            if best is None or v < best[0]: best = (v, n, o)
        v, n, o = best
        total += v
        rows.append(dict(country=c, share=sh, tb=round(tb,1), mbps=round(mb),
                         provider=o["name"], nodes=n, krw=round(v), grade=o["grade"]))
    panel = krw(*RATES["hetzner_cx23"][:2]) * PANEL_SPARE
    total += panel
    return dict(rows=rows, panel=round(panel), total=round(total),
                per_user=round(total / 10000, 1), nodes=sum(r["nodes"] for r in rows) + PANEL_SPARE)

FOCUS8 = ["미국","독일","프랑스","영국","캐나다","네덜란드","스위스","호주"]
ABSORB = {"오스트리아":"독일","벨기에":"네덜란드","스웨덴":"독일","스페인":"프랑스","일본":"미국",
          "덴마크":"독일","아일랜드":"영국","이탈리아":"프랑스","폴란드":"독일","루마니아":"독일",
          "뉴질랜드":"호주","싱가포르":"미국"}

def dist_focus():
    sh = dict(SHARE)
    for k, v in ABSORB.items():
        sh[v] += sh.pop(k)
    rows, total = [], 0.0
    for c in FOCUS8:
        tb = TOTAL_TB_20 * sh[c] / 100.0
        mb = peak_mbps(tb)
        best = None
        for o in COUNTRY_OPTIONS[c]:
            if o["grade"] == "공격": continue
            v, n = _cost(o, tb, mb)
            if v is None: continue
            if best is None or v < best[0]: best = (v, n, o)
        v, n, o = best
        total += v
        rows.append(dict(country=c, share=round(sh[c],2), tb=round(tb,1), mbps=round(mb),
                         provider=o["name"], nodes=n, krw=round(v)))
    panel = krw(*RATES["hetzner_cx23"][:2]) * PANEL_SPARE
    total += panel
    return dict(rows=rows, panel=round(panel), total=round(total),
                per_user=round(total / 10000, 1), nodes=sum(r["nodes"] for r in rows) + PANEL_SPARE)

# ── 3. 종량제 충전팩 ─────────────────────────────────────────────────────
PACKS = [("맛보기",3,1500),("라이트",10,3900),("스탠다드",30,8900),("빅",100,19900),("벌크",300,39900)]

def cost_per_gb():
    return dist20("safe")["total"] / (TOTAL_TB_20 * 1000)

def pack_table():
    cpg = cost_per_gb()
    out = []
    for name, gb, price in PACKS:
        c = gb * cpg; fee = price * PG_RATE; m = price - c - fee
        out.append(dict(name=name, gb=gb, price=price, per_gb=round(price / gb),
                        cost=round(c), fee=round(fee), margin=round(m),
                        margin_rate=round(m / price * 100, 1)))
    return out

def volume_discount_ratio():
    t = pack_table()
    return round((t[0]["price"] / t[0]["gb"]) / (t[-1]["price"] / t[-1]["gb"]), 1)

# ── 4. 계약값 원장 ───────────────────────────────────────────────────────
def contracts():
    curve = free_curve(36)
    y = [round(sum(m["cost"] for m in curve[i*12:(i+1)*12])) for i in range(3)]
    lo, sf, fc = dist20("low"), dist20("safe"), dist_focus()
    return {
        "meta": {"generated_from": "20_SRC/cost_model.py",
                 "product_name": PRODUCT_NAME, "target_segment": TARGET_SEGMENT,
                 "topup_expires": TOPUP_EXPIRES,
                 "fx": FX, "peak_factor": PEAK_FACTOR, "spare": SPARE,
                 "cap_gb_free": CAP_GB_FREE, "pg_rate": round(PG_RATE, 4)},
        "free_tier": {
            "month_01_krw": round(curve[0]["cost"]),
            "month_11_krw": round(curve[10]["cost"]),
            "month_12_krw": round(curve[11]["cost"]),
            "month_24_krw": round(curve[23]["cost"]),
            "month_36_krw": round(curve[35]["cost"]),
            "year1_krw": y[0], "year2_krw": y[1], "year3_krw": y[2],
            "year_total_krw": sum(y),
            "node_step_months": [i+1 for i in range(36)
                                 if i == 0 or curve[i]["nodes"] != curve[i-1]["nodes"]],
        },
        "dist20": {"total_tb": TOTAL_TB_20,
                   "low_krw": lo["total"], "safe_krw": sf["total"], "focus_krw": fc["total"],
                   "low_nodes": lo["nodes"], "safe_nodes": sf["nodes"], "focus_nodes": fc["nodes"],
                   "safe_per_user_krw": sf["per_user"], "focus_per_user_krw": fc["per_user"]},
        "unit": {"cost_per_gb_krw": round(cost_per_gb(), 2)},
        "packs": pack_table(),
        "volume_discount_ratio": volume_discount_ratio(),
    }

if __name__ == "__main__":
    c = contracts()
    if "--json" in sys.argv:
        print(json.dumps(c, ensure_ascii=False, indent=2)); sys.exit(0)
    f, d, u = c["free_tier"], c["dist20"], c["unit"]
    print(f"── {PRODUCT_NAME} 무료 요금제 (1인 {CAP_GB_FREE:g}GB · 매월 +1,000명) ──")
    for k in ("month_01_krw","month_12_krw","month_24_krw","month_36_krw"):
        print(f"  {k:<16} {f[k]:>10,}원")
    print(f"  연차 합계        {f['year1_krw']:,} / {f['year2_krw']:,} / {f['year3_krw']:,}원"
          f"  (3년 {f['year_total_krw']:,}원)")
    print(f"  노드 증설 시점   {f['node_step_months']}개월차")
    print("── 20개국 분산 (1만명 × 20GB = 200TB) ──")
    print(f"  최저가 {d['low_krw']:>9,}원 / 안전 {d['safe_krw']:>9,}원 / 집중8 {d['focus_krw']:>9,}원")
    print(f"── 단위 원가 {u['cost_per_gb_krw']}원/GB · 볼륨 할인 {c['volume_discount_ratio']}배 ──")
    for p in c["packs"]:
        print(f"  {p['name']:<6}{p['gb']:>4}GB {p['price']:>7,}원  {p['per_gb']:>4}원/GB  마진 {p['margin_rate']}%")
