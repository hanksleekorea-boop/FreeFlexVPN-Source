# FreeFlexVPN v2.12 GCP 첫 노드 비용 검토

> 상태: `VERIFIED_IMPLEMENTED_LOCAL`  
> 날짜: 2026-08-03  
> 이전 롤백: v2.11 provider readback 강화 후보

## 쉬운 요약

GCP의 `e2-micro`가 무료 등급이어도 VPN 서버 전체가 무료인 것은 아니다. 외부 IPv4는 시간당 USD 0.005이고, 미국 노드에서 한국 사용자에게 보내는 트래픽은 무료 허용량을 넘으면 GiB당 USD 0.19가 적용되는 것으로 공식 공개 가격표에서 확인했다. 실제 계정의 무료 크레딧·통화·할인은 로그인된 결제 콘솔에서만 확정할 수 있으므로 VM 생성은 계속 차단한다.

## 재현 가능한 계산

`70_TOOLS/run_gcp_cost_review.py`가 공식 공개 가격 스냅샷과 사용량 입력에서 비용 하한 JSON을 생성한다. 기본 후보는 `us-west1`의 `e2-micro`, 10GiB 표준 디스크, Premium Tier, 월 730시간, 한국 목적지 1/10/100GiB다.

- 외부 IPv4만 월 USD 3.65(730 × 0.005).
- 10GiB 사용 예시는 무료 송신 1GiB를 가정하면 알려진 하한 USD 5.36.
- 100GiB 사용 예시는 같은 가정에서 알려진 하한 USD 22.46.
- 원화 표시는 프로젝트 기준 환율 1 USD = 1,470원의 설명용 값이며 실제 청구 환율이 아니다.
- 무료 등급이 보이지 않으면 VM·디스크 가격은 `UNKNOWN_VERIFY_CONSOLE`로 남기며 임의 추정하지 않는다.

## 생성 전 콘솔 확인 6개

1. 결제 계정 활성·프로젝트 연결
2. 선택 미국 리전의 e2-micro 무료 등급 표시
3. Welcome credit 잔액·만료일
4. 외부 IPv4 시간당 요금 포함
5. Premium Tier 목적지·예상 GiB 포함
6. 예산 알림 설정(강제 지출 상한이 아님을 확인)

## 공식 공개 근거

- 무료 등급: https://docs.cloud.google.com/free/docs/free-cloud-features
- VPC·IPv4·송신 가격: https://cloud.google.com/vpc/pricing
- VM 가격: https://cloud.google.com/products/compute/pricing

## 증거 경계와 다음 관문

- 구현/로컬: 계산기·CLI·자동 검사 있음.
- 공개 가격: 공식 페이지의 2026-08-03 읽기 결과 있음.
- 인증 결제/Cloud/서버/기기/사용자: 없음.
- 다음 관문: 사용자가 Google 로그인 후 결제 콘솔에서 위 6개를 확인해야 실제 후보를 생성할 수 있다.
- 전체 제품 진척은 비마일스톤 준비물이므로 7/12 = 58.3%를 유지한다.

## 롤백

이 v2.12 파일·계산기·CLI·검사·증거 JSON만 제외하면 v2.11 상태로 돌아간다. v2.11 provider readback 강화 산출물과 공개 v2.3 앱은 수정하지 않는다.
