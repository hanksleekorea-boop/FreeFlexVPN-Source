# FreeFlexVPN Telegram 온보딩 v1

이 흐름은 Telegram을 가입·동의·상태 확인 창구로만 사용한다. 봇 대화는 종단간 암호화가 아니므로
WireGuard 개인키·클라이언트 `.conf`·QR 이미지는 Telegram 메시지로 보내지 않는다.

## 사용자 흐름

1. `/start` — 월 1GB 무료·충전분 무기한 정책과 동의 버튼 표시. 아직 아무것도 저장하지 않는다.
2. `동의하고 시작` — Telegram 숫자 ID를 HMAC-SHA256으로 가명화한 값과 정책 버전만 저장한다.
3. `/claim` — 10분·1회용 HTTPS 수령 주소를 반환한다. 원문 토큰은 반환 후 저장하지 않고 SHA-256만 저장한다.
4. 수령 페이지 — 클라이언트에서 키를 만든 뒤 공개키와 `10.66.0.x/32`만 서버 등록 계층에 전달한다.
5. `/status` — 동의·피어 상태만 알리고 개인키나 원문 Telegram ID를 노출하지 않는다.
6. `/revoke` — 먼저 `revoke_pending`, 서버 WireGuard 폐기 성공 뒤에만 `revoked`로 확정한다.

## 저장하는 것 / 저장하지 않는 것

- 저장: HMAC 가명 ID, 동의 정책 버전·시각, 수령권 SHA-256·만료·사용 여부, 피어 공개키·할당 IP·상태
- 미저장: 원문 Telegram ID, username, 전화번호, 메시지 본문, 수령권 원문, WireGuard 개인키·QR
- 저장 실패·손상: 원본을 보존하고 신규 수령권·폐기 확정을 fail-closed로 중단하며 사용자에게 오류를 반환한다.

## 현재 권한 경계

- BotFather 계정 생성·봇 토큰 등록: 사용자 승인·비밀값 필요, 미실행
- 공개 HTTPS claim endpoint·webhook: 실제 서버와 도메인 필요, 미구현
- 현재 설정 산출물은 `ADAPTER_OR_DEMO`이며 실제 봇 또는 VPN 연결 성공 증거가 아니다.

