# FreeFlexVPN 기여 안내

## 누구나 가능한 작업

GitHub 로그인 사용자는 저장소 복제·포크, 기능 브랜치 개발, Issue 작성, Pull Request 제출이 가능합니다. 프로젝트 협업 잠금은 사용하지 않습니다.

1. 저장소를 포크하거나 쓰기 권한이 있으면 기능 브랜치를 만듭니다.
2. `git status`, `.project-continuity/STATE.md`, `HISTORY.md`로 다른 변경과 겹치는 경로를 먼저 확인합니다.
3. 코드와 관련 검사·문서·목록표를 함께 갱신합니다.
4. 아래 검사를 통과한 뒤 Pull Request를 제출합니다.

```powershell
python -X utf8 70_TOOLS/make_manifest.py --check
python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120
```

## 원본 push와 사이트 편집

- 원본 직접 push는 GitHub 저장소 협업자로 승인된 사용자만 가능합니다. 불특정 로그인 사용자 전체에 직접 push 권한을 주는 GitHub 권한은 없습니다.
- 협업자는 기능 브랜치에 push하고 기본 갈래에는 Pull Request로 병합합니다.
- 운영 사이트 버킷 편집은 정확한 Google IAM 주체에 버킷 한정 역할을 부여한 경우만 가능합니다.
- `70_TOOLS/grant_contributor_access.ps1`은 기본적으로 계획만 출력하며 명시적 `-Execute`에서만 식별된 주체에 권한을 요청합니다.

## 보안·개인정보

토큰·개인키·실제 IP·VPN 설정·계정정보·개인정보를 커밋하거나 Issue에 게시하지 마세요. 보안 문제는 GitHub Security 탭의 비공개 신고 기능을 사용하세요.
