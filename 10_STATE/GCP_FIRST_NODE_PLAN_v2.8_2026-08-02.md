# FreeFlexVPN v2.8 GCP 첫 실제 노드 실행계획

> 상태: `VERIFIED_IMPLEMENTED_LOCAL`  
> 날짜: 2026-08-02  
> 사용자 결정: GCP를 첫 실제 노드로 사용  
> 이전 롤백: v2.7 R6 증거 사슬

## 쉬운 요약

GCP 계정만 준비되면 작은 Ubuntu VM을 안전한 기본값으로 만들고, 첫 실제 VPN 노드인지 검증할 수 있는 도구를 완성했다.
GCP 한 곳만 통과해도 최종 R6 완료로 표시하지 않으며, 두 번째 공급자를 추가해야 한다.

## 생성된 도구

1. `build_gcp_node_plan.py`: GCP 명령과 기존 cloud-init을 새 파일로 생성한다.
2. `build_gcp_runtime_config.py`: 콘솔에서 확인한 공인 IP·공개키·SSH 경로를 프로젝트 밖 무비밀 설정으로 만든다.
3. `run_gcp_node_admission.py`: 설정검사 증거와 같은 후보·설정일 때만 실제 SSH admission을 실행한다.
4. `gcp_node_admission.py`: 단일 GCP health·카운터·카탈로그를 판정하되 `R6 READY=false`를 고정한다.

## 비용·보안 기본값

- VM: `e2-micro`, 10GB 표준 영구 디스크, 미국 후보 리전.
- 네트워크: 관리자 SSH는 현재 공인 IPv4 `/32`, WireGuard UDP만 전체 클라이언트에 공개.
- 권한: VM 서비스 계정·API scope 없음, IP forwarding과 Shielded VM 활성화.
- 비용: 무료 등급 여부, 크레딧 만료, 외부 IPv4와 송신 비용을 생성 전 콘솔에서 재확인.
- 예산 알림은 실제 지출을 자동으로 막는 상한이 아님을 계획에 고정.

현재 Google 공식 안내는 신규 무료 체험과 월별 무료 등급을 제공하지만 계정·리전·사용량 제한이 있다.
정본 확인: https://cloud.google.com/free/docs/free-cloud-features

## 로컬 검증

- GCP 신규 기능: 16/16 통과.
- 기존 cloud-init·SSH·카탈로그·R6·증거 연결까지 확장한 안전 회귀: 87/87 통과.
- 예시 GCP 계획·cloud-init을 생성했으며 비밀값 0, `R6 READY=false`를 확인.
- 현재 PC: Ubuntu WSL2 있음. 공식 Google Cloud CLI 578.0.0 ZIP(84,629,589 bytes, SHA-256 `7AB6AC62A5AEEF41F40CD517E1B397F7901F9DF630CA71CF6D225614C7D7367E`)과 필수 추출 파일은 `C:\tmp`에 준비됨.
- 단, `gcloud version`은 검증된 Python 3.12.13을 지정해도 120초 안에 응답하지 않아 실행 가능·인증 완료로 주장하지 않음. Cloud Shell을 대체 실행 경로로 사용할 수 있음.

## 증거 경계

- I/L: GCP 계획·설정·admission 구현과 로컬 검사 있음.
- B/P: 새 공개 앱 변경 없음. 공개 정본은 v2.3.
- 서버: 실제 GCP VM 0대, SSH readback 0건.
- D/U: 실제 기기·독립 사용자 증거 0건.
- 전체 기준선: 7/12 = 58.3% 유지.

## 실제 실행 순서

1. GCP 계정·프로젝트·결제/무료 크레딧 상태 확인.
2. 휴대용 Google Cloud CLI 시작 지연을 해결해 로그인하거나, 브라우저 Cloud Shell에서 로그인된 프로젝트를 사용.
3. 실제 project ID와 관리자 공인 IP로 GCP 계획 생성.
4. 계획의 비용 경고를 확인한 뒤 명령을 실행해 VM 생성.
5. 공급자 콘솔에서 IP·국가·host fingerprint·WireGuard 공개키 확인.
6. 프로젝트 밖 runtime config 생성.
7. CONFIG READY 증거 생성 후 같은 증거로 live admission 실행.
8. 다른 공급자 한 곳을 추가해 v2.7 R6 2공급자 검사를 실행.

## 롤백

GCP v2.8 파일과 도구만 제외하면 v2.7 상태로 돌아간다. v2.7 증거·공개 v2.3 앱은 수정하지 않는다.
