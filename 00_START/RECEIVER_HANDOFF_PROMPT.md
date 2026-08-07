# FreeFlexVPN 인수 AI용 단일 프롬프트 — v6.2

당신은 FreeFlexVPN의 인수 AI입니다. 이 프롬프트는 반드시 **사용자 PC의 로컬 작업 환경**(Git·PowerShell·Python 실행 및 비공개 GitHub 인증이 이미 가능한 Claude Cowork 또는 Codex)에서 실행하세요. 웹 채팅처럼 파일을 읽기만 하는 환경에서는 `accepted: true`를 선언할 수 없습니다. 개발을 시작하기 전에 아래 인계 검증을 끝내고, 비밀값·개인 정보·실제 IP를 어떤 기록에도 넣지 마세요.

1. 비공개 소스 보관소 `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source.git`를 복제하고 `handoff/v6-2-20260807` 작업 갈래를 받으세요.
2. 반드시 저장 기록 `dfea156ef2c3ba314adce06bb5092e9a153fd614`를 checkout하세요. 그 저장 기록이 `refs/heads/handoff/v6-2-20260807`에서 도달 가능한지 확인하세요.
3. 시작 전 `git status --porcelain=v1` 결과가 비어 있는지 확인하고, `AGENTS.md`, `.project-continuity/STATE.md`, `.project-continuity/TEST_EVIDENCE.md`, `00_START/DEVELOPMENT_DASHBOARD.md`를 읽으세요.
4. 새 가상환경에서 `python -m pip install -r requirements-dev.txt`, `python -m playwright install chromium`을 실행하세요. 이어서 아래 필수 검사를 모두 통과시켜야 합니다.

```powershell
python -X utf8 70_TOOLS/make_manifest.py --check
python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120
```

성공 기준은 목록표 통과 및 전체 재검사 61/61 파일·628/628 항목·실패 0입니다. 검사 뒤 추적 파일 변경이 0인지 확인하세요. 목록표 SHA-256은 `a5f77f930922ea209822ff6178d10fc683e17836c1871ccba785004addd5c63e`입니다.

필수 검사가 통과하면 비공개 Issue #2에 아래 형식으로 한 번만 댓글을 남기세요.

```text
AI_HANDOFF_V6_2 RECEIVED
handoff_id: e2297f1a-e215-40ab-96cd-3bee05cee55d
expected_sha: dfea156ef2c3ba314adce06bb5092e9a153fd614
manifest: matched
required_checks: passed 61/61 files, 628/628 checks
tracked_changes_after_tests: 0
accepted: true
```

하나라도 실패하면 `accepted: false`와 실패 이유·첫 해결 행동 하나만 남기고 개발 완료 선언을 하지 마세요. 자동 채팅 알림은 검증되지 않았으므로, 댓글 뒤 사용자가 인계 AI에게 “RECEIVED 완료”라고 전달해야 합니다. 인계 AI가 CONFIRMED를 기록하기 전에는 인계 완료라고 말하지 마세요.

CONFIRMED 뒤의 첫 개발 행동은 F1-3 망 전환·차단 모드 안내입니다. 실제 VPN 터널·iPhone·운영 자료 API는 아직 미확인이므로 완료로 바꾸지 마세요.
