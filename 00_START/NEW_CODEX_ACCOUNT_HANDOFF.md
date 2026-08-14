# FreeFlexVPN — 이 PC의 새 Codex 계정 인계

이 문서는 **같은 Windows 사용자·같은 PC**에서 Codex를 로그아웃한 뒤 다른 ChatGPT 계정으로 로그인해 개발을 이어가기 위한 정본이다.

OpenAI 공식 안내 기준으로 ChatGPT 웹의 계정 전환은 지원되지만 Codex 데스크톱 앱 안의 계정 전환은 지원되지 않는다. 따라서 Codex에서는 현재 계정을 로그아웃하고 다른 계정으로 로그인해야 한다. 계정을 바꿔도 채팅·메모리·설정·결제·워크스페이스는 합쳐지지 않는다. 반면 이 PC의 로컬 프로젝트 파일과 Git 작업 폴더는 계정 소유물이 아니므로, 새 계정이 아래의 **같은 폴더를 직접 열면** 그대로 읽을 수 있다.

- OpenAI 계정 전환 안내: <https://help.openai.com/en/articles/20001068-use-multiple-accounts-with-account-switching>
- Codex의 로컬 폴더 작업 안내: <https://help.openai.com/en/articles/20001275/>

## 열어야 할 폴더

```text
C:\Users\x13\Desktop\챗지피티프로젝트들\프리플렉스vpn\owner-gateway-v38
```

다른 `FreeFlexVPN` 복사본이나 과거 `handoff-check-*` 폴더를 열지 않는다.

## 새 계정의 첫 메시지

아래 내용을 새 Codex 작업의 첫 메시지로 붙여넣는다.

```text
FreeFlexVPN 개발을 같은 PC에서 인수합니다.

프로젝트 폴더는 다음 하나입니다.
C:\Users\x13\Desktop\챗지피티프로젝트들\프리플렉스vpn\owner-gateway-v38

대화 기억이나 이전 계정의 인증 상태를 정본으로 간주하지 마세요. 먼저 AGENTS.md를 읽고 `.project-continuity/runtime/continuity-v520.py bootstrap --project-path . --compact`를 실행하세요. 출력 JCS 한 줄과 `.project-continuity/CONTEXT.md`만 읽고 현재 사용자 요청을 계속하세요. 원래 v5.2 원샷 프롬프트는 다시 요구하거나 읽지 마세요.

GitHub·Google Cloud·Google Drive 권한은 새 계정에 자동 승계되지 않습니다. 각 서비스의 현재 로그인 주체로 최소 readback을 한 뒤 provider_permission_parity를 갱신하세요. 미확인 권한을 있다고 가정하거나 토큰·이메일·실제 IP·VPN 개인 설정을 출력하지 마세요.

기존 Android ffvpn 프로필을 삭제·덮어쓰지 마세요. git reset, checkout, clean, stash, 강제 push로 다른 작업자의 변경을 숨기지 말고, 협업 LOCK*.json도 만들지 마세요.
```

## 새 AI가 실행할 HOT 시작 절차

PowerShell에서 다음을 실행한다. 현재 설치된 Codex 번들 Python의 위치를 사용하며, 비밀값이나 계정 식별값은 출력하지 않는다.

```powershell
$project = 'C:\Users\x13\Desktop\챗지피티프로젝트들\프리플렉스vpn\owner-gateway-v38'
$python = 'C:\Users\x13\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
Set-Location -LiteralPath $project
& $python -X utf8 .project-continuity\runtime\continuity-v520.py bootstrap --project-path . --compact
```

출력의 `g`가 `READY`이면 현재 OS 사용자 범위 GitHub principal이 최초 기준선 이상의 권한을 가진다. GitHub 외부 작업 직전에는 다음을 다시 실행한다.

```powershell
& $python -X utf8 .project-continuity\runtime\continuity-v520.py github-verify --project-path .
```

HOT 결과와 `CONTEXT.md`를 우선 읽는다.

1. `AGENTS.md`
2. `.project-continuity/CONTEXT.md`
3. 현재 사용자 요청이 없을 때만 `CONTEXT.md`의 `next`

전체 `HISTORY.md`와 `POLICY-v5.2.md`는 매번 읽지 않는다. 설치 영수증·runtime·schema 불일치, 복구·충돌·보안·고위험·정식 다른-PC 인수 때만 필요한 COLD 자료를 선택해 읽는다. v4.14 호환 감사가 필요할 때만 `70_TOOLS/verify_account_continuation.py --json`을 추가 실행한다.

## 준비 완료 판정

로컬 개발은 다음을 모두 만족하면 이어갈 준비가 완료된 것이다.

- runtime이 정확히 70,672 bytes이고 SHA-256이 `7c08ebf5fed65e46a3bd99473fb33a48f7981d612f294da04e10d23b438537ba`이다. 이 값은 Windows Git worktree 독립 복원과 Drive 호출 제한 보정이 적용된 프로젝트 고정판이다.
- 반복 HOT 결과의 쓰기 수 `w`가 `0`, 출력이 1,024 bytes 이하, `CONTEXT.md`가 4,096 bytes 이하이다.
- `.project-continuity/LOCK*.json`이 0개다.
- Git 작업 폴더가 깨끗하고 원격이 `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source.git`이다.
- 목록표와 전체 회귀가 통과한 통합 기준선이 기록되어 있다.

외부 사이트를 포함한 **모든 개발 권한**은 별도 판정이다. 새 ChatGPT 계정, Codex 로그인, GitHub CLI, 브라우저의 GitHub·Google Cloud·Google Drive 로그인은 서로 같은 인증이라는 보장이 없다. GitHub는 `github-verify`, Drive는 암호화 A/B의 독립 재다운로드·해시·복원, 사이트는 `SITE-CAPABILITIES.json` 18개 capability의 유효한 `pass`가 필요하다. 셋 중 하나라도 빠지면 `full_site_development: ready`라고 표기하지 않는다. 권한 미확인 상태에서도 로컬 수정·검사·기능 갈래 커밋 준비는 계속할 수 있지만 push·PR·배포·Drive 쓰기는 해당 서비스 readback 뒤에만 한다.

현재 확인된 통합 기준선은 다음과 같다.

- `shared-development`: `1989aa89bdb5a3648201c26a9d4537543c94f5aa`
- GitHub Actions 최종 통합 검사: `31713961554` 성공
- 외부 권한 기준선: GitHub 개발 capability 7개 통과, Cloud 대상 접근 실패로 전체 18개 중 pass 7·fail 4·unknown 7
- 기존 Android `ffvpn`: DNS·경로 실패 이력 보존, 별도 검증 프로필의 과거 성공과 분리

## 다른 PC에서 받을 때

다른 PC는 이 문서의 로컬 경로를 사용할 수 없다. 공개 Release <https://github.com/hanksleekorea-boop/FreeFlexVPN-Source/releases/tag/handoff-20260812T095152Z-4f7ec30>의 TXT와 ZIP을 새 안전 폴더에서 검증한다. 이 Release는 2026-08-12 기준선이므로, 검증 뒤 `shared-development`의 최신 통합 상태를 읽기 전용으로 대조해야 한다.
