# 새 PC·새 계정에서 이어서 개발하기

이 프로젝트의 원격 정본은 공개 협업 보관소 `hanksleekorea-boop/FreeFlexVPN-Source`다. 기본 갈래는 최신 검증 후보이며 기본 갈래에는 직접 저장 기록이나 원격 올리기를 하지 않고 기능 갈래와 Pull Request를 사용한다.

가장 빠른 인계 경로는 최신 공개 Release의 TXT→ZIP 순서다: `https://github.com/hanksleekorea-boop/FreeFlexVPN-Source/releases/tag/handoff-20260812T095152Z-4f7ec30`. GitHub 로그인 없이도 받을 수 있다. ZIP SHA-256은 `22a10e20260929edec0cf02e3f9680c58ee5dedc1cb7385b76d58b2a83b0873b`이며, 기준 소스 HEAD는 `4f7ec30f1c8fac0b7d8594b40ccf48e46cd45357`이다.

## 같은 GitHub 계정으로 새 PC에서 시작

1. Git과 GitHub CLI를 설치한다.
2. PowerShell에서 `gh auth login`을 실행해 **hanksleekorea-boop** 계정으로 로그인한다.
3. 원하는 작업 폴더에서 다음을 실행한다.

```powershell
gh repo clone hanksleekorea-boop/FreeFlexVPN-Source
Set-Location FreeFlexVPN-Source
powershell -ExecutionPolicy Bypass -File .\70_TOOLS\bootstrap_dev.ps1 -Verify
```

4. `.project-continuity/STATE.md`를 읽고, 새 기능 갈래를 만든 뒤 작업한다. 협업 잠금 파일은 만들지 않고 `git status`와 STATE·HISTORY 변경 경로로 충돌을 피한다.

## 다른 GitHub 계정으로 시작

로그인한 누구나 공개 저장소를 복제·포크하고 잠금 없이 개발해 Pull Request를 제출할 수 있다. 원본 기능 갈래에 직접 push해야 하는 참여자만 관리자가 정확한 사용자 이름으로 협업자 초대를 보낸다.

```powershell
gh api -X PUT repos/hanksleekorea-boop/FreeFlexVPN-Source/collaborators/대상사용자이름 -f permission=push
```

초대할 계정의 정확한 사용자 이름을 확인한 경우에만 이 명령을 사용한다. 비밀키·토큰·개인 파일을 보관소에 올리지 않는다.

## 다른 AI·다른 PC에 코드와 사이트 편집 권한 열기

AI 자체에는 GitHub나 Google Cloud 권한을 부여할 수 없다. AI가 사용하는 **정확한 GitHub 사용자명**과 사이트 배포에 사용할 **Google IAM 주체**(`user:...`, `group:...`, `serviceAccount:...`)에 권한을 준다. 익명 공개 쓰기와 공유 토큰은 사용하지 않는다.

먼저 실행 계획만 확인한다.

```powershell
.\70_TOOLS\grant_contributor_access.ps1 -GitHubUsername 대상사용자이름 -GooglePrincipal 'user:대상계정'
```

두 주체가 정확하면 관리자가 `-Execute`를 붙여 실행한다. GitHub에는 `push`, 공개 사이트에는 해당 버킷만 `roles/storage.objectAdmin`을 부여한다.

```powershell
.\70_TOOLS\grant_contributor_access.ps1 -GitHubUsername 대상사용자이름 -GooglePrincipal 'user:대상계정' -Execute
```

GitHub 대상자는 초대 수락 후 복제·push를 확인해야 한다. Google IAM 주체는 `gs://freeflexvpn-live-20260810-a31d7f` 버킷 읽기·업로드를 별도로 확인해야 한다. 소유 계정이나 프로젝트 전체 관리자 권한은 공유하지 않는다.

## 복제 완료 확인

```powershell
git status --short --branch
python -X utf8 70_TOOLS/make_manifest.py --check
```

둘 다 성공하면 코드·기획·연속성 기록의 파일 지문값이 원격 정본과 같다.
