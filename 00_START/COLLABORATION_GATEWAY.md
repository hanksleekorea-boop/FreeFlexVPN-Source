# FreeFlexVPN 비밀번호 공동개발 시작 안내

## 현재 상태

게이트웨이 코드와 localhost 종단간 검사는 준비됐지만 인터넷 운영 주소에는 아직 배포하지 않았다. 현재 공개 앱은 정적 Google Cloud Storage이므로 비밀번호 검증·Git 작업공간·배포 중계를 안전하게 실행할 서버가 아니다.

## 참여자가 최종적으로 하게 될 흐름

1. 프로젝트 전용 HTTPS 주소에서 공동개발 비밀번호로 로그인한다.
2. 15분 동안 허용된 소스·검사·시작 문서만 읽고 수정한다.
3. 자동저장 영수증, diff, 허용 검사 결과를 확인한다.
4. `ai-session/...` 갈래에 저장 기록을 만들고 `shared-development` 통합 요청을 제출한다.
5. 보호된 운영 배포는 검증된 운영 기준 SHA와 서명 결과물만 서버 중계를 통해 실행한다.

## 참여자가 할 수 없는 일

- 기본·통합 갈래 직접쓰기, force push, 보호 갈래 삭제
- 임의 shell·임의 경로·워크플로·비밀·소유자/관리 API
- 호스팅 관리자 권한, 배포 토큰 열람, 임의 SHA·환경·수동 롤백
- `.project-continuity/`, `.github/`, 배포 결과물·보관 이력 직접 수정

## 서버 운영 전 필수 조건

- 기존 승인 HTTPS 호스팅에서 Python 서비스·내구성 SQLite 또는 동등 저장소·비밀 저장 지원
- `FFVPN_COLLAB_PASSWORD`, 정확한 `FFVPN_COLLAB_ORIGIN`, 서버 전용 Git/호스팅 중계 자격증명
- AI별 분리 worktree, GitHub 통합 요청 중계, 공급자 배포 idempotency·readback·실제 운영판 식별
- Drive outbox·readback·서명 영수증과 필수 `drive-update-gate`
- 새 브라우저 비밀번호→읽기→수정→diff→commit→검사→통합 요청 실제 E2E

비밀번호·토큰·개인키를 이 문서, 채팅, Git, Drive에 붙여 넣지 않는다. 실제 설정은 검증된 호스팅 비밀 저장소에서만 수행한다.
