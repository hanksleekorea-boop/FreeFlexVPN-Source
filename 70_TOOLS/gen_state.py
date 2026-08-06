#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STATE.md 와 HANDOFF_PROMPT.md 를 실물에서 생성한다.

문서의 수치를 손으로 옮겨 적지 않기 위한 스크립트다.
파일 수·바이트·검사 통과 수·계약값은 전부 여기서 실측·재계산해 주입한다.

    python3 70_TOOLS/gen_state.py
"""
import json, os, re, subprocess, sys, pathlib, datetime
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "20_SRC"))
import fkvpaths, cost_model

ROOT = fkvpaths.root()
C = cost_model.contracts()
(ROOT / "10_STATE" / "CONTRACTS.json").write_text(
    json.dumps(C, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
F, D, U = C["free_tier"], C["dist20"], C["unit"]
NAME = C["meta"]["product_name"]
CAP = f"{C['meta']['cap_gb_free']:g}"
PUB = json.loads((ROOT / "10_STATE" / "PUBLIC_EVIDENCE.json").read_text(encoding="utf-8"))
PUBLIC_URL = PUB["public_url"]
def w(v): return f"{int(round(v)):,}"

def run(*args):
    p = subprocess.run([sys.executable, *args], cwd=ROOT,
                       env=dict(os.environ, FKV_ROOT=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
                                PYTHONIOENCODING="utf-8"),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    return p.returncode, (p.stdout + p.stderr).strip()

def count(out, pat):
    m = re.search(pat, out)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

def run_required(label, script, pattern):
    rc, out = run(script)
    passed, total = count(out, pattern)
    if rc != 0 or total <= 0 or passed != total:
        print(f"필수 검사 FAIL — {label} rc={rc} · 집계 {passed}/{total}")
        if out:
            print(out[-4000:])
        raise SystemExit(1)
    return passed, total

print("검사 실행 중 …")
c_pass, c_tot = run_required("계약", "40_TESTS/test_contracts.py", r"계약 검사 (\d+)/(\d+)")
r_pass, r_tot = run_required("실렌더", "40_TESTS/render_check.py", r"실렌더 검사 (\d+)/(\d+)")
n_pass, n_tot = run_required("음성대조", "40_TESTS/negative_control.py", r"음성 대조 (\d+)/(\d+)")
q_pass, q_tot = run_required("쿼터", "40_TESTS/test_quota_ledger.py", r"쿼터 원장 검사 (\d+)/(\d+)")
g_pass, g_tot = run_required("GitHub Pages", "40_TESTS/test_github_pages.py", r"GitHub Pages 검사 (\d+)/(\d+)")
qr_pass, qr_tot = run_required("공개 QR", "40_TESTS/test_public_qr.py", r"공개 QR 검사 (\d+)/(\d+)")
infra_pass, infra_tot = run_required("cloud-init", "40_TESTS/test_cloud_init.py", r"cloud-init 검사 (\d+)/(\d+)")
agent_pass, agent_tot = run_required("쿼터 에이전트", "40_TESTS/test_quota_agent.py", r"쿼터 에이전트 검사 (\d+)/(\d+)")
peer_pass, peer_tot = run_required("피어 묶음", "40_TESTS/test_peer_bundle.py", r"피어 묶음 검사 (\d+)/(\d+)")
telegram_pass, telegram_tot = run_required("Telegram 온보딩", "40_TESTS/test_telegram_onboarding.py", r"Telegram 온보딩 검사 (\d+)/(\d+)")
abuse_pass, abuse_tot = run_required("남용 방지", "40_TESTS/test_abuse_controls.py", r"남용 방지 검사 (\d+)/(\d+)")
ui_pass, ui_tot = run_required("공식 UI·UX", "40_TESTS/test_ui_design_contract.py", r"UI·UX 채택 검사 (\d+)/(\d+)")
rc8, o8 = run("70_TOOLS/scan_secrets.py")
if rc8 != 0:
    print("필수 검사 FAIL — 비밀값·개인정보 스캔")
    print(o8[-4000:])
    raise SystemExit(1)
TOTAL_PASS = c_pass + r_pass + n_pass + q_pass + g_pass + qr_pass + infra_pass + agent_pass + peer_pass + telegram_pass + abuse_pass + ui_pass
TOTAL = c_tot + r_tot + n_tot + q_tot + g_tot + qr_tot + infra_tot + agent_tot + peer_tot + telegram_tot + abuse_tot + ui_tot
print(f"  계약 {c_pass}/{c_tot} · 실렌더 {r_pass}/{r_tot} · 음성대조 {n_pass}/{n_tot} · 쿼터 {q_pass}/{q_tot} · GitHub Pages {g_pass}/{g_tot} · QR {qr_pass}/{qr_tot} · cloud-init {infra_pass}/{infra_tot} · 쿼터 에이전트 {agent_pass}/{agent_tot} · 피어 묶음 {peer_pass}/{peer_tot} · Telegram {telegram_pass}/{telegram_tot} · 남용 방지 {abuse_pass}/{abuse_tot} · UI·UX {ui_pass}/{ui_tot} · 비밀값 rc={rc8}")

files = [p for p in sorted(ROOT.rglob("*"))
         if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".zip"]
nfiles = len(files); nbytes = sum(p.stat().st_size for p in files)
inv = {}
for p in files:
    inv.setdefault(p.relative_to(ROOT).parts[0] if len(p.relative_to(ROOT).parts) > 1 else "(루트)", []).append(p)
DELIV = "\n".join(f"- `30_DEPLOY/{p.name}` — {p.stat().st_size:,} B" for p in fkvpaths.deliverables())
DOCS  = "\n".join(f"- `60_OUTPUTS/{p.name}` — {p.stat().st_size:,} B" for p in fkvpaths.documents())
INV   = "\n".join(f"| `{k}/` | {len(v)} | {sum(x.stat().st_size for x in v):,} |"
                  for k, v in sorted(inv.items()))
TODAY = datetime.date.today().isoformat()

# ── STATE.md ────────────────────────────────────────────────────────────
STATE = f"""# STATE — 정본 상태 (생성물 · 직접 수정 금지)

> `python3 70_TOOLS/gen_state.py` 로 재생성한다. 손으로 고치면 다음 생성에서 사라진다.
> 생성일 {TODAY}

## 1. 한 줄

제품 목표 → [조사·원가모델·문서·검사 → UI·UX v1.1 공식 채택·PWA 공개 → exit-node·쿼터·피어 QR·Telegram·남용 방지 로컬 후보] → **▶현재 여기◀** →
[VPN 서버 확보 → cloud-init 실부팅 → 실제 피어 발급·터널 연결 → 실기기 검증] → 완성

## 2. 증거 계층

| 등급 | 현재 | 근거 |
|---|---|---|
| 구현 | **있음(제품 기반·문서·모델·exit-node 후보·검사)** | 파일 {nfiles}개 · {nbytes:,} B · 검사 {TOTAL}건 |
| 로컬 | **있음(산출물 한정)** | 계약 {c_pass}/{c_tot} · 실렌더 {r_pass}/{r_tot} · 음성대조 {n_pass}/{n_tot} · 쿼터 {q_pass}/{q_tot} · GitHub Pages {g_pass}/{g_tot} · QR {qr_pass}/{qr_tot} · cloud-init {infra_pass}/{infra_tot} · 쿼터 에이전트 {agent_pass}/{agent_tot} · 피어 묶음 {peer_pass}/{peer_tot} · Telegram {telegram_pass}/{telegram_tot} · 남용 방지 {abuse_pass}/{abuse_tot} · UI·UX {ui_pass}/{ui_tot} |
| 빌드 | 해당 없음 | 단일 HTML·docx 구조라 별도 빌드 산출물 없음 |
| 패키지 | **있음** | MANIFEST 전 파일 sha256 · 왕복 대조 |
| 공개 | **있음(R2-ui-v1.1)** | 익명 무캐시 HTTP 3회 동일 해시 · 원격 Chrome DOM·CTA 오클루전·QR PASS · `{PUBLIC_URL}` |
| 대상환경 | **없음** | 실기기 확인 0건 |
| 실사용자 | **없음** | 파일럿 0건 |

**VPN 서버 런타임은 아직 없다.** 위 "구현/로컬"에는 출구 노드 cloud-init의 정적·음성 검증이
포함되지만, 실제 Ubuntu 부팅·cloud-init schema·VPN 연결 성공을 뜻하지 않는다.

## 3. 계약값 (모델 재계산값 — `10_STATE/CONTRACTS.json`)

| 계약 | 값 |
|---|---|
| 제품 | **{NAME}** · 라이트 사용자 · 월 {CAP}GB 무료 · 충전 잔액 무기한 |
| 공식 UI·UX | **v1.1 채택·공개** · `10_STATE/UI_DESIGN_v1.1_2026-08-01.md` · 9개 화면 |
| 단위 원가 | **{U['cost_per_gb_krw']}원/GB** (안전 구성 {w(D['safe_krw'])}원 ÷ {int(D['total_tb'])}TB) |
| 20개국 분산 월비용 | 최저가 {w(D['low_krw'])} · 안전 {w(D['safe_krw'])} · 집중8 {w(D['focus_krw'])}원 |
| 무료 요금제 월비용 | 1개월 {w(F['month_01_krw'])} · 12개월 {w(F['month_12_krw'])} · 36개월 {w(F['month_36_krw'])}원 |
| 무료 연차 합계 | 1년 {w(F['year1_krw'])} · 2년 {w(F['year2_krw'])} · 3년 {w(F['year3_krw'])}원 |
| 노드 증설 시점 | {F['node_step_months']}개월차 |
| 볼륨 할인 배수 | {C['volume_discount_ratio']}배 |

## 4. 파일 원장

| 폴더 | 파일 수 | 바이트 |
|---|---|---|
{INV}
| **합계** | **{nfiles}** | **{nbytes:,}** |

### 공개 배포 후보 (30_DEPLOY)
{DELIV}

### 문서 산출물 (60_OUTPUTS)
{DOCS}

## 5. 지금 막혀 있는 것

1. **실제 VPN 서버 런타임 0개** — cloud-init은 로컬 후보일 뿐 실제 부팅·터널 서비스는 별개다.
2. **서버 0대** — 사용자 확인상 결제·계정 확보 예정. 확보 전까지는 권한 경계다.
3. **Telegram 실가동 0개** — BotFather 토큰·공개 claim endpoint·webhook은 권한/서버 경계다.
4. 실기기·파일럿 — 물리적 하한
"""
(ROOT / "10_STATE" / "STATE.md").write_text(STATE, encoding="utf-8")

# ── HANDOFF_PROMPT.md ───────────────────────────────────────────────────
PACKS = "\n".join(
    f"| {p['name']} | {p['gb']}GB | {w(p['price'])}원 | {w(p['per_gb'])}원 | {p['margin_rate']}% |"
    for p in C["packs"])

HANDOFF = f"""# {NAME} — 이관 프롬프트 (이 한 장만 붙여넣으세요)

> 첨부한 `freekoreavpn.zip` 하나와 이 프롬프트 하나면 인수인계가 끝납니다.
> 생성 {TODAY} · 이관 시점 상태: **UI·UX v1.1 공식 채택·PWA 공개 · 제품 기반 구현 시작 · GitHub Pages R2 공개 · 로컬 검사 {TOTAL_PASS}/{TOTAL} 통과**

너는 지금부터 {NAME}의 전담 담당자다. 첨부된 zip이 프로젝트 전체다.
압축을 풀고 **§9의 첫 턴 보고**를 하라. **그 전에는 아무것도 수정하지 마라.**
사용자 언어는 **한국어**다. 모든 절의 첫 문장은 비개발자가 읽는다고 가정하고 쓴다.

---

## 1. 제품 한 문단

가끔 VPN이 필요한 라이트 사용자를 위한 서비스다. 가입하면 **매달 {CAP}GB가 무료**이고,
더 필요한 사람은 약정·자동결제 없이 **필요한 만큼만 충전**해 쓴다. 접속은 공식 WireGuard
앱에 QR 한 장을 찍는 것으로 끝나며, 고객 응대 창구는 두지 않는다(봇 자동응답 + 문서).
브랜드는 **{NAME}**이며 **서버는 한국에 두지 않는다** — 같은 트래픽을 서울에서 처리하면
일본의 약 22배가 들기 때문이다. 시작·동의·설정·홈·국가·충전·기기·사용량·내 정보의
**9화면 UI·UX v1.1 PWA는 공개됐지만 아직 실제 VPN 서비스가 연결된 제품은 아니다.** 이 묶음에는
채택 UI 프로토타입, 53개국 서버 원가 실측, 소비자 VPN 27곳 요금 실측, 원가 모델,
사업기획서·개발실행계획서와 그 수치가 모델과 어긋나지 않는지 확인하는 검사 {TOTAL}건이 있다.

## 2. 지금 어디까지 왔는가 — 증거 계층

| 등급 | 뜻 | 현재 | 근거 |
|---|---|---|---|
| **구현** | 코드·산출물·검사가 있다 | **있음(제품 기반·문서·모델·exit-node 후보·검사)** | 파일 {nfiles}개 · {nbytes:,} B |
| **로컬** | 개발 환경에서 실제 실행해 확인했다 | **있음(산출물 한정)** | 계약 {c_pass}/{c_tot} · 실렌더 {r_pass}/{r_tot} · 음성대조 {n_pass}/{n_tot} · 쿼터 {q_pass}/{q_tot} · GitHub Pages {g_pass}/{g_tot} · QR {qr_pass}/{qr_tot} · cloud-init {infra_pass}/{infra_tot} · 쿼터 에이전트 {agent_pass}/{agent_tot} · 피어 묶음 {peer_pass}/{peer_tot} · Telegram {telegram_pass}/{telegram_tot} · 남용 방지 {abuse_pass}/{abuse_tot} · UI·UX {ui_pass}/{ui_tot} |
| **빌드** | 배포/제출 후보를 만들었다 | 해당 없음 | 단일 HTML·docx라 별도 빌드 산출물 없음 |
| **패키지** | 버전·구조·해시를 확인했다 | **있음** | MANIFEST 전 파일 sha256 왕복 대조 |
| **공개** | 실제 공개 대상에서 확인했다 | **있음(R2-ui-v1.1)** | `{PUBLIC_URL}` · 원격 무캐시 HTTP 3회 · Chrome DOM·CTA·QR · ANON_ACCESS PASS |
| **대상환경** | 명시된 실제 기기에서 확인했다 | **없음** | 실기기 0건 |
| **실사용자** | 동의된 독립 사용자가 과업을 완수했다 | **없음** | 파일럿 0건 |

**규율 한 줄: 증명한 것만 증명했다고 말한다. 계층을 건너뛰지 않는다.**

**금지 (하나라도 하면 이관 실패다):**
- 로컬 통과를 공개로 올리기 — 검사 {TOTAL}건 통과는 공개(P) 증거가 **아니다**
- 헤드리스 브라우저를 실기기(D)로 올리기
- 네가 만든 샘플·계산값을 실사용자(U) 증거로 올리기
- 문서를 추가했다고 진행률 올리기 — **새 증거가 없으면 숫자를 올리지 않는다**
- **실행해 보지 않은 명령을 "이렇게 하면 됩니다"라고 사용자에게 적기**
- 공개 진입점이 없는데 QR을 만들어 주기 — 없으면 `QR_STATUS=BLOCKED` 라고 적는다
- **"VPN이 연결된다"고 말하기 — 서버 런타임·대상환경 증거는 아직 0건이다**

## 3. 절대 어기면 안 되는 계약값

| 계약 | 값 | 어기면 |
|---|---|---|
| `cost_per_gb` | **{U['cost_per_gb_krw']}원/GB** = 안전구성 {w(D['safe_krw'])}원 ÷ {int(D['total_tb'])}TB | 종량제 가격표의 마진이 전부 틀어진다 |
| `dist20.safe` / `.low` / `.focus` | {w(D['safe_krw'])} / {w(D['low_krw'])} / {w(D['focus_krw'])}원 | 국가 확장 판단의 근거가 무너진다 |
| 무료 요금제 월비용 | 1개월 {w(F['month_01_krw'])} · 12개월 {w(F['month_12_krw'])} · 36개월 {w(F['month_36_krw'])}원 | 성장 시나리오가 틀린다 |
| 노드 증설 시점 | {F['node_step_months']}개월차 | 증설 예산 시점을 놓친다 |
| 통화 혼합 금지 | Contabo 기본요금 EUR + 지역 추가요금 USD → **원화 환산 후 합산** | 국가당 240~290원 어긋남 (LESSONS L2) |
| 피크 계수 / 예비율 | 3.0 / 15% | 노드 수 산정이 바뀐다 |
| 제품 계약 | **{NAME} · 1인 월 {CAP}GB · 충전 잔액 무기한** | 과금·원가·사용자 약속이 어긋난다 |
| 공식 UI·UX | **v1.1 · 9화면 · `10_STATE/UI_DESIGN_v1.1_2026-08-01.md`** | 공개 셸과 실제 VPN 런타임이 갈라진다 |
| 한국 exit 노드 | **두지 않는다** | 24TB 기준 서울 34.5만원 vs 일본 1.5만원 |
| 아이콘 | **PNG만** (192 + 512), SVG 금지 | Android `beforeinstallprompt` 가 조용히 실패해 설치가 안 된다 |
| 매니페스트 | JSON 전체를 **단일 base64 blob** 으로 인라인 | 필드별 퍼센트 인코딩으로 바꾸면 파싱이 깨진다 |
| 검사 하네스 | 수치·개수·버전 **하드코딩 0** | `test_contracts.py` 의 `N1~N4` 가 자기 소스를 검사해 강제한다 |
| 경로 해석 | `70_TOOLS/fkvpaths.py` **한 곳에서만** | 재배치 시 검사가 조용히 건너뛴다 |
| 비밀값 | 저장소·로그·문서에 **금지** | `70_TOOLS/scan_secrets.py` 가 확인 |

## 4. 너의 환경 한계를 먼저 확인하고 정직하게 선언하라

**첫 턴에 이 프로젝트의 검사를 실제로 돌려 보고, 안 되면 안 된다고 말하라.**

| 필요한 것 | 없으면 불가능해지는 것 |
|---|---|
| Python 3.11+ | 원가 모델·계약 검사 {c_tot}건·MANIFEST 대조 — **전부 불가** |
| Playwright + Chromium | 실렌더 검사 {r_tot}건, PWA 매니페스트·아이콘 실측 — **전부 불가** |
| Node.js + `docx` 패키지 | 문서 재생성 불가 (기존 docx 읽기는 가능) |
| 외부 네트워크 | 배포 여부 실측 불가 |
| 사용자 PC 파일 쓰기 | 배포 파일 전달 불가 |

**의존성 0으로 되는 것:** `python3 70_TOOLS/fkvpaths.py` (경로 자체 확인).

**첫 턴에 반드시 다음 중 하나를 포함하라:**

> "이 환경에서는 `<X>`를 실행할 수 없으므로, 제가 새로 만드는 것은 `<등급>`까지입니다.
> 넘겨받은 검사 증거 {TOTAL}건은 **이전 환경의 기록**이며 제가 재현한 것이 아닙니다."

전부 실행 가능하면:

> "이 환경에서 검사 {TOTAL}건을 **직접 재현했습니다.** 결과는 `<실측 숫자>` 입니다.
> 공개 제품 안내(P)는 원격에서 재현됐습니다. 실제 VPN 연결의 공개(P)·실기기(D)·실사용자(U) 증거는 여전히 0건입니다."

zip이 첨부되지 않았으면:

> "도구는 있으나 대상물(zip)이 없어 하나도 재현하지 못했습니다."

**이것을 얼버무리는 것이 가장 큰 위반이다.**

## 5. 지금 막혀 있는 것 / 지금 할 수 있는 것

### 🔴 최우선 (차단됨)

1. **실제 VPN 서버 런타임 0개** — 공개 안내 페이지는 완료됐지만 터널 연결 기능은 아직 없다.
2. **서버 0대** — 원인분류: 권한(결제는 사용자 전용, 사용자가 곧 확보 예정이라고 확인).
   **최소 행동: Contabo 도쿄 VPS10 + Hetzner CX23 결제(합 월 18,043원).**
   완료 판정: 2대 SSH 접속 성공.

### 🟡 사람만 할 수 있는 것

계정·결제·비밀값 등록 · 실기기 설치 · 실사용자 모집·동의 · 호스터 약관 서면 질의 발송 ·
통신판매업 신고 · 법률 자문 · 달력 시간.

### 🟢 사용자 개입 없이 지금 할 수 있는 것 (우선순위 순)

1. 랜딩페이지 + 3단계 사용법
2. 약관·개인정보처리방침·국외이전 고지문 초안
3. T1~T10 접속·누수·속도 테스트 체크리스트
4. 국가별 원가 자동 재계산 스크립트 확장

**공개 안내 게이트는 통과했다.** 위 항목은 이제 실제 VPN 연결 런타임의 선행 작업이며,
서버가 확보되기 전에는 로컬 구현 증거만 오르고 실제 연결 증거는 오르지 않는다.

**배포 경로를 다시 탐색하지 마라.** `10_STATE/PRIORITIES.md` §4에 전수 실측 결과가 있다.
단 **네 환경이 다르면 그 표를 다시 실측**하고, 하나라도 열리면 그것이 최우선 작업이 된다.

## 6. 이 프로젝트가 비싸게 배운 것 (전문은 `10_STATE/LESSONS.md`)

1. **한 공급자만 보고 "이 나라는 비싸다"라고 말했다.** 한국 원가를 국내 클라우드 종량제로만
   계산해 "일본 대비 74배"라고 보고했는데, 53개국 전수 조사에서 Vultr 서울이 있어 실제로는
   22배였다. → **규칙:** 국가별 원가는 그 나라 최저가 옵션으로 계산하고, 배수를 말할 때는
   분모·분자의 공급자를 함께 적는다.
2. **통화를 섞어 더해 20개국 합계가 820원 어긋났다.** Contabo 기본요금은 EUR, 지역 추가요금은
   USD인데 EUR로 더했다. → **규칙:** 통화가 다르면 원화로 환산한 뒤 더한다.
3. **검사가 자기 자신에 걸렸다.** "소스에 총계를 하드코딩하지 않았는가"를 확인하는 검사가
   리터럴을 써서 자기 자신이 FAIL했다. → **규칙:** 자기 소스를 검사하는 규칙은 바늘 문자열을
   조립해서 만든다.
4. **배포 채널이 0인데 산출물만 계속 쌓았다.** 7회 연속 "토큰 1개"를 요청하며 문서를 늘렸다.
   → **규칙:** 채널 0은 매 보고 상단의 [중요 병목]이다. 문서 추가는 진척이 아니다.
5. **자동 목차(TOC)가 뷰어에 따라 빈 페이지로 보였다.** → **규칙:** 정적 목차를 쓰고,
   문서는 PDF로 변환해 페이지를 눈으로 확인한다. 생성 성공은 렌더 성공이 아니다.
6. **"무제한"을 검증 없이 쓸 뻔했다.** is\\*hosting은 무제한이라면서 5~80Mbps 속도캡이 있고
   대역폭을 10Mbps당 $2(EU)/$15(아시아)로 판다. → **규칙:** 무제한 상품은 포트 속도와
   fair-use 조건을 함께 확인하고, 약관 리스크가 있으면 등급을 `공격`으로 분리한다.

## 7. 사용자와 일하는 방식

- **언어: 한국어.** 모든 절·표의 첫 문장은 비개발자가 읽는다고 가정한다. 약어는 첫 등장에 쉬운 뜻 병기.
- **보고에 반드시 넣을 것:** 진척 대시보드(분야별 게이지·일정 편차) · 최신 앱 링크와 **QR 이미지** ·
  다운로드 링크 · 개발 우선순위 30 · **사용자 없이 가능한 작업 30** · 병목(사용자가 해야 할 것은
  **굵게**, 작은 행동/큰 행동 구분) · 마지막에 사용자가 지금 결정할 질문 5개
- 최종 산출물은 **QR + 다운로드 링크를 항상 함께**. 앱은 로그인 없이 누구나 열려야 한다
- 작업 중간에 멈추지 않는다. 멈추고 싶을 때 한 번 더 밀어붙인다
- **새 증거가 없으면 진행률 숫자를 올리지 않는다**
- **연속 신호:** `ㅎ` `1` `ㅋ` `ㅇ` `0` `o` `j` → 최상위 비차단 자율 작업을 시작한다.
  `0` 은 "0-1부터 순서대로"를 뜻한다. **이 신호는 권한을 넓히지 않는다.**
- **상시 승인:** 검증을 통과한 공개 웹 배포는 매번 묻지 않고 진행한다
- **여전히 명시 승인이 필요한 것:** 결제 · 계정 생성 · 비밀값 등록 · 권한 변경 ·
  개인정보 수집 · 데이터 삭제 · 제3자 연락 · 실사용자 모집 · 실기기 조작

## 8. 폴더 지도

| 폴더 | 내용 |
|---|---|
| `00_START/` | 이 프롬프트 + `README.md`(뺀 것·되살리는 법·이름 변경 규칙) |
| ★ `10_STATE/` | **사실의 출처.** `STATE.md` 정본(생성물) · `CONTRACTS.json` 계약값 원장(생성물) · `DECISIONS.md` 확정 결정·조사 상수 · `LESSONS.md` 사고 이력 · `PRIORITIES.md` 다음 작업 + 배포 경로 전수 실측 |
| ★ `20_SRC/` | **현행 소스.** `cost_model.py` 원가·수익 모델 **단일 정본** · `html_templates/` 대시보드 원본 · `docgen/` 문서 생성기 · `icons.py` |
| ★ `30_DEPLOY/` | **공개 배포 후보** HTML {len(fkvpaths.deliverables())}종 (단일 파일 PWA) |
| `40_TESTS/` | 계약 {c_tot} · 실렌더 {r_tot} · 음성대조 {n_tot} · 쿼터 {q_tot} · GitHub Pages {g_tot} · QR {qr_tot} · cloud-init {infra_tot} · 쿼터 에이전트 {agent_tot} · 피어 묶음 {peer_tot} · Telegram {telegram_tot} · 남용 방지 {abuse_tot} |
| `60_OUTPUTS/` | 사업기획서·개발실행계획서 (docx) |
| `70_TOOLS/` | `fkvpaths.py` 경로 해석 · `make_manifest.py` · `scan_secrets.py` · `gen_state.py` 문서 생성 |
| `MANIFEST.md` | 전 파일 SHA-256 (생성물 — 직접 수정 금지) |

## 9. 첫 턴에 이것을 보고하라

1) **zip 파일 개수와 MANIFEST 해시 대조 결과**
   → `python3 70_TOOLS/make_manifest.py --check`
   기대: `MANIFEST 왕복 대조 PASS — 파일 N개 해시 전부 일치`
   (N은 `MANIFEST.md` 상단 표의 "파일 수"와 같아야 한다. 낡으므로 여기 숫자를 적지 않는다.)
   **검사를 먼저 돌린 뒤 `--check` 해도 PASS 여야 한다** — 재생성물은 제외 목록에 있다.

2) **이 환경에서 되는 것 / 안 되는 것 + §4의 선언 문구**

3) **`python3 20_SRC/cost_model.py`**
   기대: 단위 원가 **{U['cost_per_gb_krw']}원/GB** · 20개국 안전 구성 **{w(D['safe_krw'])}원** ·
   무료 1개월 **{w(F['month_01_krw'])}원**.
   **다르면 모델이 바뀐 것이므로 문서를 고치기 전에 먼저 보고하라.**

4) **`python3 40_TESTS/test_contracts.py`** → 기대 `계약 검사 {c_tot}/{c_tot} 통과`
   **`python3 40_TESTS/render_check.py`** → 기대 `실렌더 검사 {r_tot}/{r_tot} 통과`
   **`python3 40_TESTS/negative_control.py`** → 기대 `음성 대조 {n_tot}/{n_tot} 통과`
   **`python3 40_TESTS/test_quota_ledger.py`** → 기대 `쿼터 원장 검사 {q_tot}/{q_tot} 통과`
   **`python3 40_TESTS/test_github_pages.py`** → 기대 `GitHub Pages 검사 {g_tot}/{g_tot} 통과`
   **`python3 40_TESTS/test_public_qr.py`** → 기대 `공개 QR 검사 {qr_tot}/{qr_tot} 통과`
   **`python3 40_TESTS/test_cloud_init.py`** → 기대 `cloud-init 검사 {infra_tot}/{infra_tot} 통과`
   **`python3 40_TESTS/test_quota_agent.py`** → 기대 `쿼터 에이전트 검사 {agent_tot}/{agent_tot} 통과`
   **`python3 40_TESTS/test_peer_bundle.py`** → 기대 `피어 묶음 검사 {peer_tot}/{peer_tot} 통과`
   **`python3 40_TESTS/test_telegram_onboarding.py`** → 기대 `Telegram 온보딩 검사 {telegram_tot}/{telegram_tot} 통과`
   **`python3 40_TESTS/test_abuse_controls.py`** → 기대 `남용 방지 검사 {abuse_tot}/{abuse_tot} 통과`
   실패·예외가 있으면 **항목 이름과 원인**을 그대로 적어라.
   라벨 열거는 `FKV_LIST_CHECKS=1` 을 붙인다.

5) **계약값 `cost_per_gb` 의 값과 그 뜻을 한 문장으로.** ← 얼버무리면 인수인계 실패다
   (힌트: 무엇을 무엇으로 나눈 값이며, 이 값이 흔들리면 어떤 문서의 어느 표가 전부 틀리는가)

6) **`10_STATE/LESSONS.md` 에서 가장 중요하다고 판단한 교훈 3개와 그 이유**

7) **`python3 70_TOOLS/scan_secrets.py`** → 기대 `비밀값·개인정보 스캔 PASS — 허용 목록 외 항목 0건`

8) **사용자 개입 없이 지금 시작할 수 있는 1순위 작업과 선정 이유**
   (§5 🟢 목록이 전부 임계 경로가 아니라는 점을 함께 밝힐 것)

**"넘겨받았으니 상태가 좋을 것"이라고 가정하지 마라.** 문서가 아니라 실물을 확인하라.
특히 **공개 배포 여부는 기록이 아니라 응답 코드로 판정하라.** R2-ui-v1.1 공개 앱 셸은 통과했지만,
실제 VPN 연결 런타임 공개 여부는 별도 후보와 별도 응답·연결 증거로 다시 판정해야 한다.

---

## 부록 — 종량제 가격표 (설계안, 지불의사 미검증)

| 팩 | 용량 | 가격 | GB당 | 마진율 |
|---|---|---|---|---|
{PACKS}

볼륨 할인 배수 **{C['volume_discount_ratio']}배** — 프록시·eSIM 업계 표준 3~4배와 일치.
**이 가격은 설계안이며 실제 지불의사(WTP)는 검증되지 않았다.** 사전판매 100~200명으로
검증한 뒤 확정할 것.
"""
(ROOT / "00_START" / "HANDOFF_PROMPT.md").write_text(HANDOFF, encoding="utf-8")
print(f"STATE.md · HANDOFF_PROMPT.md 생성 완료 (검사 {TOTAL_PASS}/{TOTAL})")
