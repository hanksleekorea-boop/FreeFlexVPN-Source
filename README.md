# FreeFlexVPN

FreeFlexVPN의 PC·모바일 웹앱, VPN 제어 API, 인프라 계약과 검증 도구를 함께 개발하는 저장소입니다.

## 공개·무잠금 협업

- GitHub에 로그인한 누구나 이 저장소를 복제하거나 포크하고, 자기 브랜치에서 잠금 없이 개발해 Pull Request를 제출할 수 있습니다.
- `.project-continuity/LOCK*.json` 협업 잠금은 만들지 않습니다. 시작 전에 `git status`, `.project-continuity/STATE.md`, `HISTORY.md`의 변경 경로를 대조합니다.
- GitHub는 불특정 로그인 사용자 전체에게 원본 직접 push 권한을 제공하지 않습니다. 원본 push가 필요한 참여자는 정확한 GitHub 사용자명으로 협업자 권한을 받습니다.
- 공개 사이트 배포권한은 소스 기여와 분리합니다. 익명 쓰기, 공유 관리자 토큰, 저장소에 비밀값 저장은 금지합니다.

## 시작

```powershell
gh repo clone hanksleekorea-boop/FreeFlexVPN-Source
Set-Location FreeFlexVPN-Source
powershell -ExecutionPolicy Bypass -File .\70_TOOLS\bootstrap_dev.ps1 -Verify
```

자세한 새 PC 절차는 [`00_START/NEW_PC_SETUP.md`](00_START/NEW_PC_SETUP.md), 기여 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 확인하세요.

현재 공개 앱: https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html

> 공개 저장소의 코드 후보와 실제 운영 VPN·결제·법무·실기기 검증은 별도입니다. 완료 근거가 없는 항목을 상용 완료로 표시하지 않습니다.
