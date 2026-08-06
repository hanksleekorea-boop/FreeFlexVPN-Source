# 새 PC·새 계정에서 이어서 개발하기

이 프로젝트의 원격 정본은 비공개 보관소 `hanksleekorea-boop/FreeFlexVPN-Source`다. 기본 갈래는 `feature/source-bootstrap`이며, `main`에는 직접 저장 기록이나 원격 올리기를 하지 않는다.

## 같은 GitHub 계정으로 새 PC에서 시작

1. Git과 GitHub CLI를 설치한다.
2. PowerShell에서 `gh auth login`을 실행해 **hanksleekorea-boop** 계정으로 로그인한다.
3. 원하는 작업 폴더에서 다음을 실행한다.

```powershell
gh repo clone hanksleekorea-boop/FreeFlexVPN-Source
Set-Location FreeFlexVPN-Source
powershell -ExecutionPolicy Bypass -File .\70_TOOLS\bootstrap_dev.ps1 -Verify
```

4. `.project-continuity/STATE.md`를 읽고, 새 기능 갈래를 만든 뒤 작업한다.

## 다른 GitHub 계정으로 시작

보관소가 비공개이므로 관리자가 대상 사용자 이름을 협업자로 초대해야 한다. 초대 전에는 복제할 수 없다. 초대 뒤에는 위와 같은 절차를 쓴다.

```powershell
gh api -X PUT repos/hanksleekorea-boop/FreeFlexVPN-Source/collaborators/대상사용자이름 -f permission=push
```

초대할 계정의 정확한 사용자 이름을 확인한 경우에만 이 명령을 사용한다. 비밀키·토큰·개인 파일을 보관소에 올리지 않는다.

## 복제 완료 확인

```powershell
git status --short --branch
python -X utf8 70_TOOLS/make_manifest.py --check
```

둘 다 성공하면 코드·기획·연속성 기록의 파일 지문값이 원격 정본과 같다.
