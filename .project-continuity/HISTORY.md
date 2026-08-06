# 작업 인계 기록

## 2026-08-05 — 제품·UX 우선순위 100 v3.0 산출

- 작성: `APP_SERVICE_PLAN_v3.0_2026-08-05.md`, `DEV_EXECUTION_PLAN_v3.0_2026-08-05.md`, `PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md`
- 핵심: P0-01부터 P4-100까지 각 요구사항의 완료 판정과 T0~T5 개발 열차를 고정함.
- 정직성: 일반 인터넷/DNS 확인과 VPN 터널 보호 확인을 분리했으며, iPhone 실기기와 실제 운영 자료는 미검증으로 기록함.
- 검사: `40_TESTS/test_priority_100_planning_v3.py` 5건 통과.
- 승인: 문서 작성만 수행. 코드 변경, Git 커밋/push, 배포, 비용 발생, 실기기 설정 변경은 수행하지 않음.
- 다음: T0 보호 상태의 실제 검사 입력 유무를 먼저 확인.

## 2026-08-06 — 신규기능 100 최우선 기획·상세 실행계획 v4.0

- 작업자/도구: codex / Codex Desktop.
- 대상: `APP_SERVICE_PLAN_v4.0_2026-08-06.md`, `DEV_EXECUTION_PLAN_v4.0_2026-08-06.md`, `FEATURE_FIRST_ROADMAP_100_v4.0_2026-08-06.md`, 문서 계약 검사와 연속성 기록.
- 목적: P0-01~P4-100을 기존 대기 기능보다 앞선 F0~F6·20개 작업 묶음으로 승격.
- 우선순위: 보안·개인정보·전면 장애·신규기능 필수 기반 외 기존 작업은 `PARKED_AFTER_F6`.
- 정직성: 다섯 엔진 상태 유지, `unverified`는 UI 표현, A56 터널·iPhone·실제 운영 자료 미검증 유지.
- 검사: `40_TESTS/test_priority_100_planning_v4.py` 7/7 통과.
- 미수행: 앱 코드, Git, push, 배포, 비용, 실기기 설정 변경.
- 다음: F0-1 기준선 회귀와 UI 보호 상태 입력 경로 추적.
- 하드링크: 기록 5개가 Windows 임시 업로드 경로와 연결된 것을 확인해 작업 원본 쪽 링크를 안전하게 분리함. 분리 후 각 파일 `links=1` 확인.
- 자기검사: STATE갱신 O · 다음행동 O · 잠금해제 O · 대안소진 O · 스킬탐색 O · 완결판정 O · 규칙점검 O · 정본확인 O.

## 2026-08-06 — F0-1 보호 상태 UI·음성 대조

- 작성: `20_SRC/build_app_v2.py`, `20_SRC/html_templates/service_shell.html`, `20_SRC/html_templates/service_shell.css`, `40_TESTS/test_protection_status_ui.py`.
- 결과: 엔진의 다섯 상태는 유지하고, `limited`·`setup_needed`를 고객 화면에서 `unverified`(보호 상태 확인 불가)로 표시함. 시작 화면도 실제 터널·외부 IP·DNS 근거 전에는 확인 불가로 표시함.
- 안전성: `protected`를 UI 클릭으로 설정하는 코드는 없고, 음성 대조로 limited→checking 변조·확인 불가 스타일 제거를 각각 거부함.
- 검사: F0-1 전용 5/5, 보호 상태 엔진 8/8, v2 앱 계약 19/19 통과. 전체 회귀는 45/57 파일·430/430 검사 통과; 12개 브라우저 의존 파일은 Playwright Chromium 실행 파일 미설치로 미실행.
- 미수행: Git, push, 배포, 비용, 실기기 설정 변경. 내장 브라우저는 로컬 `file:` 미리보기 URL 정책상 열지 못해 시각 검사는 정적 생성 산출물·계약 검사로 한정함.
- 다음: F0-2 근거 항목별 보호 확인표와 재시도 경로.

## 2026-08-06 — 전역 규칙 v9 적용 확인

- 정본: `C:\Users\x13\.ai-global-rules\GLOBAL_RULES.md`가 사용자 첨부 v9와 SHA-256 파일 지문값까지 동일함을 확인.
- 보관: 이전 v8.1은 `shared-continuity\rules-archive\GLOBAL_RULES_v8.1_2026-08-06_140419.md`에 유지됨.
- 현재 프로젝트: `AGENTS.md`에 v9 포인터와 R1~R8·무결성 라인 규칙을 추가.
- 미수행: 앱 코드, Git, 인터넷 공개, 비용, 실기기 설정 변경 없음.

## 2026-08-06 — F0-2 첫 사용·정직한 오류

- 작성: `20_SRC/html_templates/service_shell.html`, `service_shell.css`, `20_SRC/app/pwa_runtime.js`, `20_SRC/build_app_v2.py`, `40_TESTS/test_protection_evidence_ui.py`, `40_TESTS/test_first_use_recovery_ui.py`.
- 결과: 고객용 첫 화면에 터널·외부 IP·DNS·IPv6·차단 스위치 5개 근거표를 추가하고, 실제 IP 값은 화면 전달값에서 제외함. 설정 도움말에 QR 미인식·카메라 거부·만료·빈 파일·지원하지 않는 형식의 5개 복구 안내와 보호 범위를 추가함.
- 검사: F0-2 근거표 4/4, 첫 사용 복구 3/3, F0-1 상태 UI 5/5, 보호 엔진 8/8, 앱 계약 19/19 통과. 한 줄 전체 재검사 47/59 파일·437/437 검사 통과.
- 미완료: 12개 화면 검사는 Playwright Chromium 실행 파일이 없어 시작하지 못함. 실제 터널·iPhone·운영 자료 API도 아직 확인하지 못함.
- 미수행: Git, 인터넷 공개, 비용, 실기기 설정 변경 없음.
- 다음: F1-1의 실제 출처·갱신 시각이 있는 서버·사용량 빈 상태 구현.

[연속성 자기검사: STATE갱신 O · 다음행동기재 O · 잠금해제 O]

## 2026-08-06 — 원격 기능 갈래 push 확인

- 저장 기록: `b0e4e6e chore(source): bootstrap private GitHub source repository [codex]`.
- 원격: `origin/feature/source-bootstrap`에 올린 뒤 같은 파일 지문값을 `git ls-remote`로 읽어 확인함. 원격 보관소는 비공개, 이슈 기능 사용 가능, HTTPS 인증은 현재 PC의 안전한 자격 증명 보관소를 사용함.
- 검사: Chromium 설치 후 전체 재검사 57/59 파일·594/594 검사 통과, 제품 동작 실패 2개 파일은 STATE의 다음 행동으로 분리함.
- 공개 Pages 보관소·배포·비용·실기기 VPN 설정은 변경하지 않음.

[연속성 자기검사: STATE갱신 O · 다음행동기재 O · 잠금해제 O]

## 2026-08-06 — 개발 원본 GitHub 연결·대청소 1차

- 대청소: `10_PLAN/CURRENT_SERVICE_PLAN.md`, `10_PLAN/CURRENT_DEVELOPMENT_EXECUTION_PLAN.md` 통합 정본을 새로 만들고 원본 v2~v4는 그대로 보존함. 참조 없는 `debug.log`는 `_to_delete/debug_2026-08-05.log`로만 이동했으며 삭제는 하지 않음.
- 목록표: `70_TOOLS/make_manifest.py`가 로컬 가상환경·브라우저 임시 파일을 제외하고 파일별 경로·크기·용도·파일 지문값을 기록하도록 보강함. `MANIFEST.md` 왕복 대조 380개 통과.
- GitHub: Git 2.53.0, GitHub CLI 2.97.0, HTTPS 인증 계정 `hanksleekorea-boop` 확인. 원본 폴더를 정확한 신뢰 경로로 등록하고 `feature/source-bootstrap` 기능 갈래를 생성함.
- 원격: 비공개 `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source.git`를 `origin`으로 연결하고 읽기 확인함. 기존 공개 Pages 보관소는 미공개 변경이 있어 수정·push하지 않음.
- 검사: 고위험 비밀값·개인키 패턴 0건. Chromium 설치 뒤 전체 검사 57/59 파일·594/594 검사 통과. `test_keyboard.py` 2건과 `test_pc_home.py` 1건은 실제 화면 동작 실패로 재현됨.
- 다음: 두 화면 검사 실패를 수정·재검사한 뒤 F1-1로 진행. 원격에는 기능 갈래만 push하고 main에는 직접 커밋·push하지 않음.

[연속성 자기검사: STATE갱신 O · 다음행동기재 O · 잠금해제 O]
