# FreeFlexVPN — 새 Codex 계정 인계 프롬프트

아래 내용 전체를 이 PC에서 새로 로그인한 Codex 대화의 첫 메시지로 붙여넣으세요.

```text
당신은 FreeFlexVPN의 새 담당 Codex입니다. 대화 기억은 정본이 아닙니다. 이 PC의 프로젝트 파일, Git 상태, 검사 증거, 공개 URL만 정본으로 사용하세요.

프로젝트 경로:
C:\Users\x13\Desktop\챗지피티프로젝트들\프리플렉스vpn\handoff-check-cp949\FreeFlexVPN

즉시 다음 순서로 시작하세요.
1. 프로젝트의 AGENTS.md, %USERPROFILE%\.codex\GLOBAL_CONTINUITY_POLICY.md, %USERPROFILE%\.ai-global-rules\GLOBAL_RULES.md를 읽으세요.
2. .project-continuity\STATE.md, HISTORY.md, TEST_EVIDENCE.md, 00_START\DEVELOPMENT_DASHBOARD.md, 00_START\시작하세요.md, 이 파일을 읽으세요.
3. 수정 전에 git status --porcelain=v1, git branch --show-current, git rev-parse HEAD, git rev-list --left-right --count @{upstream}...HEAD를 실행해 실제 상태를 확인하세요.
4. 인계 패키지는 생성 시점에 미저장 변경이 없고 원격 작업 갈래와 ahead/behind 0/0인 소스만 허용합니다. 실제 상태가 다르면 git reset, git checkout, git clean, stash, 강제 push로 숨기지 말고 변경 소유와 범위를 먼저 분류하세요.
5. 원격 기준선은 인계 ZIP의 `20_GIT/git_context.txt`와 Release 자산의 SHA-256을 대조하세요. GitHub 인증·원격 읽기는 새 환경에서 다시 확인하되, 계정·토큰·이메일·실제 IP·개인 VPN 설정 내용은 출력하거나 기록하지 마세요.

현재 핵심 사실:
- 공개 반응형 앱: https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html
- PC 화면: 위 주소의 ?view=app
- 실제 A56에서 새 검증 터널 ffvpn-a56v는 일반 웹·DNS/도달성·서버 최근 악수까지 통과했다. 이 저장 터널은 현재 꺼져 있다.
- 기존 ffvpn 터널의 이전 웹 실패는 미해결이며, 최신 자동 재현은 Android UI 자동화가 스위치를 실제로 켜지 못해 미확인이다. 두 터널·항상 연결·차단 모드는 현재 꺼져 있다.
- 기존 ffvpn을 삭제·덮어쓰지 않는다. 실제 기기·비용·외부 공개·비밀값·삭제는 현재 대화의 명시 승인을 먼저 확인한다.

첫 개발 행동:
STATE.md의 다음 첫 행동을 따르되, 기존 ffvpn의 사람 직접 스위치 조작 가능 여부 또는 안전한 재발급/교체 계획을 읽기 전용으로 먼저 검토하세요. 새 검증 터널을 기존 사용자용 프로필로 임의 승격하지 마세요.

종료 전:
- 실제 실행·검사 결과를 STATE.md, HISTORY.md, TEST_EVIDENCE.md에 기록하세요.
- 다음 작업자가 할 행동 하나를 남기고, 다른 작업자 잠금이 있으면 덮어쓰지 마세요.
- 모든 보고는 R1~R8과 [보고 무결성 R1–R8: 8/8]로 끝내세요.
```

## 인계 판정

- 같은 PC·같은 프로젝트 폴더: 위 프롬프트와 프로젝트 기록만으로 안전하게 이어갈 수 있다.
- 다른 PC: 최신 공개 GitHub Release `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source/releases/tag/handoff-20260812T095152Z-4f7ec30`의 ZIP·TXT SHA-256과 `20_GIT/git_context.txt`의 HEAD를 확인한 뒤 새 안전 폴더에 풀면 같은 소스를 재현할 수 있다. ZIP SHA-256은 `22a10e20260929edec0cf02e3f9680c58ee5dedc1cb7385b76d58b2a83b0873b`이다. 전체 회귀와 외부 접근은 새 PC에서 다시 확인해야 한다.
- GitHub 확인: 원격은 공개이며 로그인 없는 clone도 가능하다. 인계 생성기는 깨끗한 작업 폴더·현재 작업 갈래와 원격 ahead/behind 0/0이 아니면 중단한다.
