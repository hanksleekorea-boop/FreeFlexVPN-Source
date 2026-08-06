# 00_START/README — 먼저 읽으십시오

## 현재 GitHub 연결 (2026-08-06)

- 개발 원본: 비공개 `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source`의 `feature/source-bootstrap` 기능 갈래.
- 공개 사이트: 별도 공개 보관소 `https://github.com/hanksleekorea-boop/FreeFlexVPN`와 GitHub Pages 주소를 사용한다. 이 보관소의 미공개 변경은 개발 원본과 독립적으로 보존한다.
- 새 작업은 개발 원본에서 기능 갈래를 만들고 검사한 뒤 원격에 올린다. `main`에는 직접 저장 기록이나 보관소 올리기를 하지 않는다.

## 2026-08-03 이관 사본 안내

이 폴더는 원본을 수정하지 않고 만든 `v2.15-r2-handoff` 스테이징 사본이다. 새 담당자는
`HANDOFF_PROMPT.md`를 먼저 읽고, 그 문서 §9의 첫 턴 검증을 마치기 전에는 파일을 수정하지 않는다.

### 이번 이관에서 뺀 것과 되살리는 방법

| 뺀 것 | 이유 | 되살리는 방법 |
|---|---|---|
| `.pytest_cache/`, 모든 `__pycache__/`, `*.pyc` | 실행 캐시 | 검사 실행 시 자동 재생성 |
| `90_TMP/` | 일회성 공개 읽기·중간 파일 | 필요한 실측을 다시 실행해 새 임시 경로에 생성 |
| `60_OUTPUTS/qa/` | 약 37.4MB의 Chrome 프로필 캐시·재생성 가능한 화면 | 계약 검사는 `python -X utf8 70_TOOLS/run_all_tests.py`; 구형 렌더 기준은 `python -X utf8 40_TESTS/render_check.py` |
| `60_OUTPUTS/checks/` | 검사·빌더가 재생성하는 중간 JSON | 해당 테스트·빌더를 다시 실행 |
| 기존 `MANIFEST.md` | 제외 전 457파일 기준이라 현행 이관 사본과 불일치 | `python -X utf8 70_TOOLS/make_manifest.py`로 이 사본에서 재생성 |
| 형제 저장소 `FreeFlexVPN-Pages/.git`와 작업 트리 | 공개 미러이며 원본 프로젝트와 별도, 미커밋 변경 보존 필요 | 공개 URL과 `10_STATE/PUBLIC_EVIDENCE*`를 기준으로 별도 저장소에서 계속 관리 |

뺀 항목은 정본·현행 소스·검사 픽스처가 아니다. 정리 전후 전체 회귀와
`FKV_LIST_CHECKS=1` 라벨 원장을 대조해 조용한 검사 감소가 없는지 별도로 확인한다.

## 2026-08-01 v2.0 정본 안내

앱서비스 범위가 안전 기본기·순간 중심 UX·3잔액 데이터 지갑·양쪽 추천 보상으로 확장됐다.
새 작업은 아래 순서로 읽는다.

1. `00_START/HANDOFF_V2_2026-08-01.md`
2. `10_STATE/APP_SERVICE_PLAN_v2.0_2026-08-01.md`
3. `10_STATE/PLAN_v2_2026-08-01.md`
4. `10_STATE/PRIORITIES_v2_2026-08-01.md`

아래 본문과 기존 `HANDOFF_PROMPT.md`는 v1 기준선의 롤백·역사 자료로 보존한다.

## 이 묶음이 무엇인가

**FreeFlexVPN** 프로젝트의 전체 이관 묶음입니다. 라이트 사용자를 위한 VPN 서비스(1인 월 1GB 무료 + 무기한 충전)를
만들기 위한 **조사·원가 모델·기획서·실행계획서·검사 하네스**가 들어 있습니다.

**중요: 공개된 것은 UI 프로토타입이며 실제 VPN 터널 서비스는 아직 없습니다.** 로컬에는
쿼터·피어·Telegram·exit-node 후보 코드가 있으나 실제 서버·결제·실기기·파일럿 증거는 없다.

## 인수인계 순서

1. `00_START/HANDOFF_PROMPT.md` 를 새 AI 대화에 붙여넣습니다 (이 zip과 함께).
2. 새 담당자가 §9 첫 턴 보고를 수행합니다.
3. 그 보고의 5번(계약값 설명)이 얼버무려져 있으면 이관이 안 된 것입니다.

## 폴더 이름 규칙 — 해석과 되돌리는 법

숫자 접두사(`10_`, `20_` …)는 **읽는 순서**를 뜻하며 실행 순서가 아닙니다.
경로는 코드에 흩어 두지 않고 `70_TOOLS/fkvpaths.py` 한 곳에서만 해석합니다.
**폴더 이름을 바꾸려면 `fkvpaths.py` 의 `MARKERS` 만 고치면 되돌릴 수 있습니다.**
소스나 문서에 경로를 직접 적지 마십시오 — 이름 변경 비용이 릴리스 하나가 됩니다.

## 뺀 것과 되살리는 방법

| 뺀 것 | 이유 | 되살리는 방법 |
|---|---|---|
| 렌더 스크린샷 28장 (약 9.2MB) | 검사 실행 시 재생성 | `python3 40_TESTS/render_check.py` 실행 후 필요 시 `page.screenshot()` 추가 |
| PDF 변환본 2개 | docx에서 재생성 | `soffice --headless --convert-to pdf 60_OUTPUTS/*.docx` |
| 중간 계산 스크립트 12개 (model.py·free.py·opt.py 등) | `20_SRC/cost_model.py` 로 통합됨 | 통합본이 동일 수치를 재현함이 검사로 확인됨 (`40_TESTS/test_contracts.py` A1) |
| 일회성 검증 스크립트 (verify*.js, v4~v8.js) | `40_TESTS/render_check.py` 로 대체 | 대체본이 더 많은 관문을 확인함 |
| `node_modules`·`__pycache__` | 재생성 가능 | `npm i docx playwright` / 자동 생성 |

**뺐다고 검사가 줄지 않았습니다.** 정리 전에는 명명된 검사 하네스가 아예 없었고(0건),
정리 후 계약 30 + 실렌더 60 + 음성대조 8 = **98건이 신설**되었습니다.

## 필요한 실행 환경

Python 3.11+ · Playwright + Chromium · (문서 재생성 시) Node.js + `docx` 패키지.
Playwright가 없으면 실렌더 검사 60건이 **건너뛰어지지 않고 실패**합니다 — 의도된 동작입니다.
