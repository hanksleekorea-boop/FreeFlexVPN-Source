# FreeFlexVPN — 받는 AI 인계 프롬프트

아래 공개 Release에서 TXT와 ZIP 두 파일만 받으세요. GitHub 로그인 없이도 받을 수 있습니다.

`https://github.com/hanksleekorea-boop/FreeFlexVPN-Source/releases/tag/handoff-20260812T095152Z-4f7ec30`

```text
FreeFlexVPN 프로젝트를 인수하세요.

1. `freeflexvpn-next-ai-prompt.txt`를 먼저 읽고 ZIP 이름과 SHA-256을 확인하세요.
2. ZIP `freeflexvpn-ai-handoff-20260812T095152Z-4f7ec30.zip`의 SHA-256은 `22a10e20260929edec0cf02e3f9680c58ee5dedc1cb7385b76d58b2a83b0873b`입니다.
3. 새 안전 폴더에 압축을 풀고 `00_MANIFEST/README-FIRST.md`, `manifest.tsv`, `SHA256SUMS`를 검증하세요.
4. Git 원격 `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source.git`, 갈래 `handoff/v6-2-20260807`, 기준 HEAD `4f7ec30f1c8fac0b7d8594b40ccf48e46cd45357`을 읽기 전용으로 대조하세요.
5. `git reset`, `checkout`, `clean`, `stash`, 강제 push, 기존 Android `ffvpn` 프로필 삭제·덮어쓰기를 하지 마세요.
6. `python -X utf8 70_TOOLS/make_manifest.py --check`와 `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`을 실행하세요.
7. 기존 Android `ffvpn`의 DNS·경로 실패와 별도 검증 프로필의 과거 성공을 분리하세요. 다음 첫 행동은 기존 프로필을 보존한 피어·재발급 경로 비교입니다.
8. 실제 실행 결과와 새 환경의 한계를 STATE·HISTORY·TEST_EVIDENCE에 기록하세요.
```

성공 기준: ZIP·TXT 다운로드 SHA-256 일치, 내부 SHA256SUMS 일치, 목록표 일치, 전체 회귀 통과, 원격 기준 HEAD 확인. 실제 Android·iPhone·Windows VPN과 외부 계정 접근은 새 환경에서 별도 검증해야 합니다.
