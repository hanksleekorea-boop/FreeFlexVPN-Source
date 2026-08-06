# FreeFlexVPN GCP Cloud Shell bundle v1

이 묶음은 EXAMPLE_ONLY라 모든 셸 스크립트가 cloud 명령 전에 종료합니다.

## 순서

1. Google Cloud Console에서 프로젝트 `freeflex-example-123456`와 무료 크레딧 만료·예산 알림·외부 IPv4·송신 비용을 직접 확인합니다.
2. Cloud Shell에 이 폴더를 업로드하고 `bash 01_preflight.sh`를 실행합니다. 이 단계는 읽기 전용입니다.
3. 실제 후보에서만 아래 확인값을 입력한 뒤 배포합니다.

```bash
export FREEFLEX_COST_REVIEWED=YES
export FREEFLEX_PROJECT_CONFIRM=freeflex-example-123456
export FREEFLEX_APPLY=YES
bash 02_deploy.sh
bash 03_provider_readback.sh
```

4. provider readback은 VM 설정 확인일 뿐 VPN admission이 아닙니다. 공급자 콘솔에서 cloud-init·WireGuard 공개키·SSH fingerprint를 별도 확인합니다.
5. 예상 밖 비용·설정 오류가 있으면 아래처럼 이 묶음이 만든 정확한 네 리소스만 제거합니다.

```bash
export FREEFLEX_PROJECT_CONFIRM=freeflex-example-123456
export FREEFLEX_ROLLBACK=YES
bash 04_rollback.sh
```

`provider-readback.json`은 공인 IP를 포함하므로 프로젝트/Git에 복사하지 않습니다. 이 묶음에는 토큰·비밀번호·개인키가 없습니다.
