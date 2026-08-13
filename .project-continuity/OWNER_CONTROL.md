# FreeFlexVPN 소유자 통제 정본

## 현재 판정

- 안내 계약: `OWNER-AI COMPACT OPS v4.0`
- 참여 프로필: `PASSWORD_GATEWAY` · 작업 방식 `SAFE_FANOUT`
- 개발 준비도: `PASSWORD_GATEWAY_LOCAL_E2E` — localhost 계약 통과, 실제 인터넷 게이트웨이 미배포
- 참여자 배포: `PARTICIPANT_DEPLOY_POLICY_ONLY` — 정책·모의 중계 검사 통과, 실제 호스팅 중계 미연결
- Drive: `CONNECTED` · `DRIVE_UPDATE_GATE_PENDING` · 소유자 전용 · 참여자 0명 · 공개 링크 OFF
- 복구: `UNVERIFIED` — 원격 Git은 있으나 독립 암호화 백업 복원 검사는 없음

## 프로젝트 대상 카드

- 프로젝트: FreeFlexVPN (`freeflexvpn`)
- 저장소: 공개 `hanksleekorea-boop/FreeFlexVPN-Source`
- 운영 기준 갈래: `feature/pc-commercial-readiness-90`
- 통합 갈래: `shared-development`
- 운영 환경: 기존 Google Cloud Storage 정적 채널
- 대상 지문: `158c7b892a1cecc2d8dc414a884794b9de5d100cdc90277136db751ed8751f07`
- Git 권한: 현재 인증 주체의 read/write/admin 실제 확인
- 호스팅·DNS·결제·백업 복호화 권한: 이 작업에서 미확인

## 소유자에게만 남긴 통제

- 저장소·호스팅·Drive 관리자, 비밀 저장소, 병합, 보호 규칙 변경, 참여자 추가·철회, 배포 정책, 임의 복구
- 참여자 세션은 owner/admin/secret/workflow/연속성 기록/임의 shell/기본·통합 갈래 직접쓰기를 사용할 수 없다.
- 비밀번호·세션·CSRF는 평문 저장하지 않는다. 호스팅 비밀은 코드·Git·브라우저·Drive에 넣지 않는다.

## 보호 상태

- 운영 기준과 `shared-development`: PR 필수, `verify` 필수, 대화 해결, 삭제·강제 push 차단, 필수 승인 0명.
- 참여자 수정 허용: `20_SRC/`, `40_TESTS/`, `00_START/`의 안전한 텍스트 파일.
- 참여자 수정 차단: `.github/`, `.project-continuity/`, `70_TOOLS/`, `30_DEPLOY/`, `90_ARCHIVE/`, 비밀 패턴, 프로젝트 밖 경로.
- 세션: 프로젝트 하나, 15분, CSRF·same-origin·secure/httpOnly/sameSite 쿠키, 로그인 속도 제한, 대상 지문, 중복 작업 영수증.

## Drive 상태

- 소유자 권한과 비공개 상태를 재조회한 기존 FreeFlexVPN 인계 폴더 아래에 `FreeFlexVPN - 공동개발 상황`을 생성했다.
- 표준 하위 폴더 9개와 `01_CURRENT_STATUS/FreeFlexVPN 공동개발 현재 상태` 문서를 생성·재조회했다.
- 참여자 Google 계정 명부가 없으므로 공유 0건이다. 이메일·계정 ID 원문은 이 정본에 기록하지 않는다.
- 서버 outbox→Drive readback→서명 영수증이 없으므로 통합·병합·배포 강제 게이트는 ACTIVE로 주장하지 않는다.

## 철회·복구

- `RevokeAll`은 소유자 재인증, 대상 지문, `REVOKE ALL freeflexvpn` 확인문구 뒤 세션·정책 세대·배포 권한만 폐기한다.
- 저장소·문서·소유자 계정·로컬 clone은 삭제하지 않는다. 신원 공유 방식이 아니므로 개별 철회는 보장하지 않는다.
- 다음 복구 검사는 별도 승인된 암호화 백업을 임시 위치에 복원하고 전체 회귀·소유자 접근을 확인하는 것이다.

## 다음 첫 행동

서버 실행과 비밀 저장을 지원하는 **기존 승인 호스팅 대상**을 소유자 권한으로 확인한 뒤, 새 비용·새 채널 없이 가능한 경우에만 비밀번호 비밀을 공급자 저장소에 설정하고 새 브라우저 종단간 시험을 한다.
