# FreeFlexVPN v2.18 GCP S-1·S-2 실행 기록

> 상태: `S1_COMPLETE_S2_DEPLOYED_PROVIDER_VERIFIED_RUNTIME_BOOTSTRAP_VERIFIED`  
> 날짜: 2026-08-04  
> 프로젝트: `oceanic-abacus-477201-f3`  
> 제품 진척: 7/12 = 58.3% 유지 — V2-M8은 서로 다른 공급자 2곳이 필요하다.

## S-1 비용 안전장치

- Google Cloud 무료 체험판이 활성 상태이며 확인 시점 잔여 크레딧은 ฿10,066.05, 잔여 기간은 90일이었다.
- 선택 프로젝트에 결제가 연결되어 있고 확인 시점 표시 비용은 ฿0.00이었다.
- 월 ฿300 예산 `FreeFlexVPN 월 예산 300바트`와 50%·90%·100% 알림을 생성했다.
- 예산 알림은 지출을 자동 차단하지 않는다. 일반 유료 계정 `활성화`는 누르지 않았다.

## S-2 실제 배포값

| 항목 | 실측값 |
|---|---|
| 노드 | `gcp-usw1-01` |
| 리전/존 | `us-west1` / `us-west1-b` |
| VM | 비선점형 `e2-micro`, RUNNING |
| 부팅 디스크 | 10GB `pd-standard` |
| 관리 접속 | Google IAP TCP 전달망 `35.235.240.0/20`만 SSH 허용 |
| VPN | UDP 51820 공개 |
| 외부 주소 | 예약 IPv4 `gcp-usw1-01-ip` |
| 서비스 계정 | 없음, API scope 없음 |
| 보호 | Shielded VM, IP forwarding |

## 실행·검증 결과

- 읽기 전용 사전검사 PASS 뒤 Compute Engine API를 활성화했다.
- SSH 방화벽, WireGuard 방화벽, 예약 주소, VM을 생성했다.
- 공급자 재조회는 계획과 실제 프로젝트·존·VM·디스크·방화벽·주소·cloud-init의 결속을 PASS로 확인했다.
- 최초 cloud-init은 UFW systemd 서비스가 `active (exited)`인 것을 실제 방화벽 활성으로 잘못 판단해 `scripts_user` 오류로 멈췄다.
- 서버의 실제 `ufw status`는 `inactive`였다. 검사 규칙을 실제 UFW 상태 기준으로 수정하고 같은 서버에서 bootstrap을 다시 실행했다.
- 재실행 결과 `wg-quick@wg0`, `nftables`, `fail2ban`, `freeflexvpn-health.timer`가 모두 `active`였다.
- 서버 건강 파일은 `status=ok`, 실패 목록 없음으로 확인됐다.
- bootstrap 완료 표식과 런타임 서비스는 확인했지만 실제 사용자 피어·VPN 터널·실기기 연결은 아직 만들지 않았다.

## 로컬 정본과 배포 해시

- 최초 배포 metadata의 cloud-init SHA-256은 `CE2077A14520C610B10A328197D318CC858C0112CC03A883E18C8B3BA848B818`이며 공급자 재조회가 이 값을 확인했다.
- UFW 오판 수정 뒤 로컬 정본 cloud-init SHA-256은 `54F022377F02F610DFED6F4F3CC1F3C1204F7FD3756925C78E8DA5506FDDF389`이다.
- 실행 중 서버에는 UFW 검사 한 줄만 동일하게 보정해 bootstrap을 재실행했다. 최초 cloud-init 실패 이력은 숨기지 않으며, 다음 노드는 수정된 로컬 정본으로 새로 배포해야 한다.

## 증거 경계

- S-1 완료, 첫 GCP 노드의 공급자 설정·부팅·WireGuard 런타임 건강 확인까지 완료했다.
- R6 또는 V2-M8 완료로 승격하지 않는다. V2-M8은 서로 다른 공급자의 두 번째 서버와 두 런타임 확인이 필요하다.
- V2-M9에는 iOS·Android·Windows의 실제 터널·누수·재연결 증거가 별도로 필요하다.
- 결제수단, 계정 이메일, Billing Account ID, 외부 IP, SSH 키·지문, WireGuard 키, 토큰, 브라우저 저장소는 이 기록에 저장하지 않았다.

## 다음 재개점

1. 서로 다른 두 번째 공급자의 후보를 비용·권한 검토한다.
2. 첫 실제 시험기기에 일회용 피어 구성을 발급해 터널·DNS/IPv6·재연결 증거를 수집한다.
3. 두 공급자와 실기기 증거가 모두 갖춰진 뒤에만 R6/V2-M8 admission을 평가한다.
