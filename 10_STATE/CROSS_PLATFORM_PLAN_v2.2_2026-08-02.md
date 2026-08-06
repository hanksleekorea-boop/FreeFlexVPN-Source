# FreeFlexVPN 크로스플랫폼 서비스 기획 v2.2

기준일: 2026-08-02  
상태: `VERIFIED_IMPLEMENTED` (I/L), 실제 서버·대상 기기 연결은 미완료  
지원 모듈: `20_SRC/app/platform_support.js` (`2026-08-02.1`)

## 1. 제품 결론

FreeFlexVPN은 하나의 설치형 웹앱(PWA)으로 Windows PC·Mac·Linux PC·Android·iPhone/iPad에서 계정, 잔액, Moment 30 추천, 서버 선택, 기기 구성을 관리한다. 실제 VPN 터널은 각 운영체제의 공식 WireGuard 앱이 실행한다.

브라우저만으로 운영체제 VPN을 직접 켠다고 주장하지 않는다. PWA 설치가 지원되지 않는 브라우저에서도 일반 웹앱으로 동일 관리 기능을 사용할 수 있다.

## 2. 모든 기기 지원표

| 환경 | FreeFlexVPN 사용 형태 | 실제 VPN 연결 | 설치 안내 |
|---|---|---|---|
| Windows 10·11 PC | Chrome·Edge PWA 또는 웹 | 공식 WireGuard Windows 앱에 `.conf` 가져오기 | 주소창 설치 아이콘 |
| macOS | Safari Dock 앱·Chrome PWA 또는 웹 | 공식 WireGuard macOS 앱에 구성 가져오기 | Dock에 추가 또는 브라우저 설치 |
| Linux PC | Chromium 계열 PWA 또는 웹 | 배포판 WireGuard 패키지에 구성 적용 | 브라우저 설치 메뉴 |
| Android | 설치형 PWA 또는 웹 | 공식 WireGuard Android 앱에 구성 가져오기 | 앱 설치·홈 화면 추가 |
| iPhone·iPad | 홈 화면 PWA 또는 웹 | 공식 WireGuard iOS 앱에 구성 가져오기 | 공유 메뉴→홈 화면에 추가 |

공식 설치 정본: https://www.wireguard.com/install/

## 3. 사용자 흐름

1. 공개 HTTPS 주소를 브라우저에서 연다.
2. 앱이 운영체제를 기기 내에서 감지하고 사용자가 다른 기기를 직접 선택할 수도 있다.
3. FreeFlexVPN을 PWA로 설치하거나 웹에서 계속 사용한다.
4. 공식 WireGuard 설치 페이지에서 해당 OS 앱을 설치한다.
5. 실제 health 서버와 로그인이 모두 준비된 경우에만 이 기기 전용 구성을 발급한다.
6. 개인키가 포함된 `.conf`를 해당 기기에 저장해 WireGuard로 가져온다.
7. FreeFlexVPN 웹앱에서 실제 터널·출구 IP·DNS·IPv6·최근 확인 시각을 검증한다.

## 4. 역할과 데이터 경계

- FreeFlexVPN PWA: 가입 수령, 서버 추천, Moment 30, 잔액, 추천 보상, 기기·구성 관리, 보호 상태 표시.
- 공식 WireGuard: 운영체제 네트워크 인터페이스와 실제 터널 실행.
- 개인키: 브라우저가 지원하면 기기에서 생성하며 서버에는 공개키만 전송. `.conf`는 해당 기기에만 저장.
- 플랫폼 감지: `userAgent`, `platform`, touch point를 화면 메모리에서만 사용하고 API로 보내거나 저장하지 않음.
- 오프라인: 캐시된 앱 셸·안내는 열 수 있으나 로그인, 구성 발급, 서버 연결·검증에는 인터넷 필요.
- 다기기: 활성 기기 2대 계약을 유지하며 같은 개인키를 복사하지 않고 기기마다 별도 키를 발급.

## 5. 지원 상태 언어

| 상태 | 의미 |
|---|---|
| 웹앱 사용 가능 | 브라우저에서 관리 화면을 열 수 있음 |
| 설치 가능 | 브라우저·OS 조합이 PWA 설치를 지원함. 설치 확정은 사용자 동작 필요 |
| 실제 서버 필요 | 현재 공개 서버가 0대라 구성 발급 불가 |
| 로그인 필요 | 서버는 있으나 인증 세션이 없어 구성 발급 불가 |
| 구성 발급 가능 | 실제 서버·로그인·브라우저 키 생성 관문 통과 |
| 보호 확인됨 | 실기기 터널·출구 IP·DNS·IPv6·킬 스위치 조건 전건 통과 |

PWA 설치 성공은 VPN 연결 성공이 아니며, `.conf` 생성도 실기기 보호 성공이 아니다.

## 6. 구현·검증 관문

- I: 플랫폼 5종 프로필, Windows/macOS/Linux/Android/iOS 감지, PWA·WireGuard 역할 분리.
- L: 플랫폼 모듈 15/15, 앱 계약 17/17, 모의 실제 서버 PWA 왕복 23/23.
- B/K: v2.2 단일 HTML과 모듈 5종, 서비스워커 캐시 후보 생성·해시.
- P: GitHub Pages 무로그인 HTTP·Chrome 렌더·14화면·플랫폼 5종 검증.
- D: 동일 후보를 실제 Windows·macOS·Linux·Android·iOS에서 설치·구성·연결. 아직 미완료.
- U: 독립 사용자의 PC→모바일 또는 모바일→PC 다기기 과업. 아직 미완료.

## 7. 공식 근거

- WireGuard 공식 설치 페이지는 Windows, macOS, Ubuntu·Debian 등 Linux, Android, iOS 설치 경로를 제공한다: https://www.wireguard.com/install/
- MDN은 설치 가능한 PWA가 OS의 앱처럼 아이콘·독립 창으로 실행될 수 있으며, 설치 UI와 지원 범위는 브라우저·운영체제 조합에 따라 다르다고 설명한다: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable

## 8. 롤백

v2.2 플랫폼 화면·모듈·서비스워커 캐시를 제거하고 v2.1 Moment 30 공개 커밋 `33813cd`로 되돌린다. v2.1 공개 앱 SHA-256은 `d4cd682612af8813a75c94343958374700bb6493d436885ba1955a83f97b588e`다.
