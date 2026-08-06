# FreeFlexVPN v2.13 GCP 비용 확인 도우미

> 상태: `VERIFIED_BUILD_LOCAL_BROWSER_BLOCKED`  
> 날짜: 2026-08-03  
> 이전 롤백: v2.12 GCP 비용 검토 계산 후보

## 쉬운 요약

S-1의 “Google Cloud에 로그인해서 비용을 확인한다”를 한 화면의 6개 체크와 비용 계산으로 줄였다. 이 도우미는 계정에 접속하거나 VM을 만들지 않으며, 비밀번호·결제수단·Billing Account ID·토큰 입력란도 없다.

## 산출물

- 소스: `20_SRC/html_templates/gcp_billing_review_v2_13.html`
- 빌더: `70_TOOLS/build_gcp_billing_review.py`
- 검사: `40_TESTS/test_gcp_billing_review.py`
- 단일 HTML: `60_OUTPUTS/FreeFlexVPN_GCP_비용확인도우미_v2.13_2026-08-03.html`

HTML은 공식 가격 스냅샷을 `gcp_cost_review.py`에서 가져와 외부 IPv4와 목적지별 송신 비용을 계산한다. GCP 프로젝트 ID·통화·크레딧 상태와 생성 전 확인 6개를 기록하지만, “준비” 판정도 배포 승인으로 취급하지 않는다.

## 데이터 지속성

- 브라우저 저장 성공: 이 기기의 localStorage에 자동 저장.
- 저장 실패: 현재 DOM·인메모리 상태를 유지하고 계산·체크·JSON 내보내기를 계속 제공.
- 정직 고지: 저장 실패 모드에서 “현재 화면 메모리에서만 유지 중”과 닫기 전 JSON 내보내기를 표시.
- 복구: JSON 가져오기 실패 시 가져오기 전 스냅샷을 다시 적용해 기존 입력을 보존.
- 수동 검증 훅: `?storage=fail`에서 저장 실패를 강제할 수 있으나 이번 세션 브라우저 창 연결이 실패해 실제 화면 판정은 미완료.

## PWA·전달 경계

192px·512px PNG 아이콘과 base64 매니페스트를 HTML에 내장했다. Android 설치 이벤트, iOS 홈 화면 추가 안내, standalone 억제, 설치 배너 24시간 억제를 포함한다. HTTPS/localhost가 아니면 설치를 보장하지 않는다고 화면에 명시한다.

관리용 로컬 도우미이며 공개 URL이 없으므로 QR은 발행하지 않았다. 공개 앱 v2.3과 v2.12 비용 계산 후보는 수정하지 않았다.

## 검증

- 계약 검사: 7/7 PASS.
- 인라인 JavaScript 구문: 1/1 PASS.
- localhost 제공: HTTP 200.
- 브라우저: webview attach 2회 시간 초과 — 데스크톱·모바일·저장 실패 실제 상호작용은 미검증.
- 실제 GCP·결제·VM·서버·기기·사용자 증거: 0.
- 비마일스톤 S-1 보조물이므로 제품 전체 진척은 7/12 = 58.3% 유지.

## 롤백

v2.13 계획·템플릿·빌더·검사·HTML·증거만 제외하면 v2.12로 돌아간다. v2.12 계산기와 기존 공개 앱은 수정하지 않는다.
