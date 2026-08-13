# GitHub v6.2 인계 감사 — 최신 공유본

## 2026-08-13 공개·무잠금 협업 전환

- 현재 판정: `PUBLIC_LOCK_FREE_CONTRIBUTION_READY`.
- 저장소: PUBLIC, 기본 갈래 `feature/pc-commercial-readiness-90`, fork·Issues 활성.
- 익명 검증: GitHub 자격 증명 도우미를 비운 새 임시 폴더 clone 성공, HEAD `cb8df1b367c6696875e6d5a4b4fa0f3c89f136ad`, 변경 0개.
- 참여 경로: 누구나 clone·Release 다운로드, 로그인 사용자는 fork·Issue·Pull Request. 프로젝트 협업 잠금 파일은 만들지 않는다.
- 기본 갈래 규칙: 삭제·강제 갱신 차단, Pull Request 필수, 승인 요구 0명, 모든 일반 병합 방식 허용.
- 보안: secret scanning·push protection·Dependabot 보안 갱신·비공개 취약점 신고 활성. validity checks는 GitHub 재조회에서 disabled로 남아 활성 완료로 주장하지 않는다.
- 경계: GitHub는 불특정 로그인 사용자 전원에게 원본 직접 push 권한을 주는 모델을 제공하지 않는다. 직접 push는 정확히 식별된 협업자만 가능하며 공유 토큰·익명 쓰기는 사용하지 않는다. 사이트 배포 IAM은 별도다.
- 아래 2026-08-12 및 이전의 `비공개` 표기는 당시 상태를 보존한 역사 기록이다.

## 2026-08-12 최신 인계 감사

- 판정: `GITHUB_RELEASE_READY_WITH_RECEIVER_RECHECK`
- 인계 기준 저장 기록: `4f7ec30f1c8fac0b7d8594b40ccf48e46cd45357`
- 인계 작업 갈래: `handoff/v6-2-20260807`, 생성 시 원격 ahead/behind 0/0.
- 비공개 Release: `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source/releases/tag/handoff-20260812T095152Z-4f7ec30`
- 자산: ZIP·TXT 두 개만 존재하며 Release 재다운로드 SHA-256 일치.
- 검사: 최종 전체 회귀 69/69 파일·720/720 항목, 목록표 416개, 인계 계약 6/6 통과.
- 제한: 새 PC 독립 재실행과 받는 AI 수락, iPhone·Windows 실제 VPN, 기존 Android `ffvpn` DNS·경로 문제는 별도 확인이 필요하다.

## 판정

- 판정: `GITHUB_READY_WITH_LIMITATIONS`
- 인계 기준 저장 기록: `dfea156ef2c3ba314adce06bb5092e9a153fd614`
- 인계 작업 갈래: `handoff/v6-2-20260807`
- 확인 시각: 2026-08-07 UTC

## 확인한 상태

| 항목 | 결과 | 근거 |
|---|---|---|
| 원격 보관소 | 비공개 · 읽기/쓰기 가능 | GitHub CLI 재조회 |
| 기본 작업 갈래 | `feature/source-bootstrap` | GitHub CLI 재조회 |
| 인계 작업 갈래 | 정확한 저장 기록이 원격에 존재 | `git ls-remote` |
| 새 복제본 | 시작 전 깨끗함 · 목록표 통과 | 새 임시 복제본 실측 |
| 필수 검사 | 61/61 파일 · 628/628 항목 통과 | 새 복제본 전체 재검사 |
| 원격 자동 검사 | 성공 | GitHub Actions 실행 31162903252 |
| Actions 기본 권한 | 읽기 전용 | GitHub REST 재조회 |
| Dependabot 보안 갱신 | 활성 | GitHub REST 설정 후 재조회 |
| 기본 갈래 보호 | 삭제·강제 변경 차단, Pull Request 요구, 필수 검토 0명 | GitHub ruleset `20545111` 재조회 |
| 인계 우편함 | 비공개 Issue #2 | GitHub private Issue 생성 |

## 이번에 추가한 안전 장치

- `.github/dependabot.yml`: 실제 Python 의존성 두 위치만 주 1회 점검, 열린 요청은 각 3개 이하.
- `.github/CODEOWNERS`, 보안 신고·기여 안내, Issue·Pull Request 양식.
- `.project-continuity/local/`은 기기별 증거 원장으로만 쓰며 Git에서 제외.
- 목록표 도구는 이 제외 위치를 목록표 대상에서도 뺀다. 그래서 다른 PC의 복제본이 기기별 파일 때문에 실패하지 않는다.

## 제한과 정직한 경계

- GitHub Actions 실행 31162903252는 인계 기준 저장 기록에서 성공했다. 이 실행은 병합 없이 닫은 시험 Pull Request에서 확인했다.
- 자동 인계 알림은 검증되지 않았다. 인수 AI는 Issue #2에 영수증을 남기고, 사용자가 이 대화에 “RECEIVED 완료”라고 알려 주는 사용자 전달 방식이다.
- 첫 인수 시도는 GitHub 인증·GitHub CLI·터미널이 없는 웹 채팅 환경에서 실행되어 검증을 시작하지 못했다. 해결 경로는 이 PC의 로컬 Claude Cowork 또는 Codex에서 동일 프롬프트를 실행하는 A 경로로 확정했다.
- 실제 WireGuard 터널, iPhone 실기기, 실제 운영 자료 API는 아직 검증되지 않았다. 이 인계는 소스·검사·GitHub 연결의 검증이지 VPN 서비스 완성 선언이 아니다.
- GitHub 비밀값 자동 탐지는 현재 비공개 보관소의 별도 유료 보안 상품에 의존할 수 있어 활성 완료로 주장하지 않는다. 로컬 고위험 지문 검사는 0건이었다.

## 되돌리기

- 이 인계 작업 갈래와 Pull Request는 기본 갈래에 병합하지 않았다.
- Dependabot 보안 갱신은 저장소 Security 설정에서 끌 수 있다.
- 기본 갈래 규칙 묶음은 GitHub Settings → Rules에서 `20545111`을 비활성화하거나 수정할 수 있다. 삭제·강제 변경은 자동으로 실행하지 않는다.
