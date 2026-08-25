# 공동개발 게이트웨이 운영 인계

상태: 서버 배포 후보. 로컬·CI 검증과 운영 패키징은 완료했지만 실제 HTTPS 주소는 아직 배포되지 않았다.

## 필수 운영 조건

- 기존 승인 호스트의 영구 디스크에 원본 Git 저장소, 세션 worktree, SQLite DB, Drive outbox를 둔다.
- 비밀번호와 Drive HMAC 서명키는 공급자 비밀 저장소에서 환경변수로만 주입한다. 로그·이미지·Git에 넣지 않는다.
- HTTPS 역방향 프록시 뒤에서만 공개하며 `FFVPN_COLLAB_ORIGIN`을 그 정확한 Origin으로 고정한다.
- 서버용 GitHub App 또는 최소 권한 fine-grained token은 이 저장소의 세션 갈래 push와 PR 생성만 허용한다. 운영 갈래 직접 push와 강제 push 권한은 주지 않는다.
- 프로세스와 세션 worktree는 전용 비관리자 OS 계정으로 실행한다.

## 환경변수

```text
FFVPN_COLLAB_PASSWORD=<secret manager injection>
FFVPN_COLLAB_DRIVE_SIGNING_KEY=<32+ byte secret manager injection>
FFVPN_COLLAB_ORIGIN=https://<approved-host>
FFVPN_COLLAB_DB=/var/lib/freeflexvpn/collaboration.sqlite3
FFVPN_COLLAB_SOURCE_REPO=/var/lib/freeflexvpn/source
FFVPN_COLLAB_SESSIONS_ROOT=/var/lib/freeflexvpn/sessions
FFVPN_COLLAB_DRIVE_OUTBOX=/var/lib/freeflexvpn/drive-outbox
FFVPN_COLLAB_GITHUB_ENABLED=1
FFVPN_COLLAB_GH=/usr/local/bin/gh
```

정적 단일 작업공간 변수 `FFVPN_COLLAB_WORKSPACE`·`FFVPN_COLLAB_SESSION_BRANCH`는 개발 검사 호환용이다. 실제 다중 참여 운영에서는 세션 작업공간 변수를 사용한다.

## 배포 전후 검사

1. 원본 저장소 origin과 `origin/shared-development`를 읽기 전용 확인한다.
2. `python -X utf8 70_TOOLS/make_manifest.py --check`와 전체 회귀를 통과시킨다.
3. `/healthz`에서 `session_worktrees=true`, `integration_broker=true`, `secrets_exposed=false`를 확인한다.
4. 새 브라우저에서 로그인→읽기→수정→커밋→PR을 수행한다. 생성된 PR base가 `shared-development`이고 force push가 아님을 확인한다.
5. Drive relay가 outbox를 반영한 뒤 서명된 readback 영수증을 반환하는지 확인한다. 영수증이 없으면 Drive 관문은 완료가 아니다.

## 복구

- 장애 시 새 로그인만 중지하고 원본 저장소·세션 worktree·SQLite·outbox를 보존한다.
- 세션 브랜치는 GitHub와 서버에 남기고 임의 삭제·reset·clean하지 않는다.
- 비밀 노출 의심 시 공급자에서 비밀번호·서명키·GitHub 자격만 교체하고, 기존 사용자 VPN 프로필과 운영 앱은 건드리지 않는다.
- 호스트 복구 후 health→로그인→기존 세션 브랜치 읽기→미처리 outbox 재전송 순서로 확인한다. 같은 operation_id는 중복 부작용 없이 재시도된다.
