# FreeFlexVPN 출구 노드 cloud-init v1

이 후보는 **새 Ubuntu 전용 서버 1대**를 WireGuard IPv4 출구 노드로 만드는 1회 입력용 설정이다.
공개 관리 패널은 열지 않으며, 관리자 SSH는 생성 시 지정한 공인 IPv4 한 개(`/32`)에서만 받는다.

## 실서버 후보 생성

먼저 현재 관리자 공인 IPv4를 확인한 뒤 아래 명령의 예시 주소를 바꾼다.

```powershell
python 70_TOOLS/build_exit_node_cloud_init.py --admin-ssh-cidr 198.51.100.25/32 --node-id tokyo-01
```

`198.51.100.25`도 문서용 주소이므로 그대로 쓰면 안 된다. 생성된 YAML을 공급자의 **cloud-init/user-data**
칸에 붙여 넣는다. 기존 서버에 쓰면 `flush ruleset`으로 기존 방화벽 규칙을 바꾸므로 **새 전용 서버에서만** 쓴다.
관리자 IP를 잘못 넣으면 SSH가 차단될 수 있으므로 공급자 웹 콘솔 복구 경로를 먼저 확인한다.

## 첫 부팅 뒤 콘솔 검증

공급자 콘솔에서 아래 항목을 먼저 확인한다. 이것을 통과하기 전에는 VPN 연결 성공으로 판정하지 않는다.

```bash
sudo cloud-init status --wait --long
sudo cloud-init schema --system
sudo cat /var/lib/freeflexvpn/health/latest.json
sudo systemctl --no-pager --full status wg-quick@wg0 nftables fail2ban
sudo wg show wg0
sudo cat /etc/wireguard/wg0.pub
```

`latest.json`의 `status`가 `ok`여야 한다. 개인키 `/etc/wireguard/wg0.key`는 서버 안에서 생성되고
권한은 `0600`이며, 저장소·cloud-init·로그로 복사하지 않는다. 공개키만 다음 피어 발급 단계에 쓴다.

## 월 1GB·무기한 충전 쿼터

cloud-init에는 WireGuard의 수신+송신 누적 바이트를 1분마다 읽는 쿼터 에이전트가 포함된다.
피어를 WireGuard에 추가하기 **전에** 등록하고, 결제 확정 뒤에만 충전 명령을 호출한다.

```bash
sudo python3 /opt/freeflexvpn/quota_agent.py enroll --account-id '64자리-HMAC-가명계정ID' --peer-key '피어공개키' --allowed-ip 10.66.0.2/32
sudo python3 /opt/freeflexvpn/quota_agent.py topup --peer-key '피어공개키' --bytes 3000000000
sudo python3 /opt/freeflexvpn/quota_agent.py status
```

- 무료분은 UTC 달력월마다 정확히 `1,000,000,000`바이트로 초기화한다.
- 충전분은 월이 바뀌어도 보존하고 무료분을 먼저 차감한다.
- 미등록 피어와 AllowedIPs가 바뀐 피어는 nftables에서 기본 차단한다.
- 상태 파일은 원자 저장하며 손상되면 원본을 덮어쓰거나 방화벽을 임의 변경하지 않고 실패를 알린다.
- 1분 폴링이므로 한도 도달과 차단 사이에 최대 한 주기만큼 초과 사용이 생길 수 있다. 실서버에서
  실제 속도로 상한을 계측하기 전에는 “정확히 1GB에서 즉시 차단”이라고 주장하지 않는다.

## 남용 방지 기준선

- VPN 클라이언트가 외부로 전달하는 TCP 25번(SMTP)은 기본 차단한다.
- 대표 BitTorrent 포트 `6881-6999`, `51413`의 TCP·UDP를 차단한다. 이는 포트 기반 휴리스틱일 뿐
  임의 포트·암호화·중계 방식을 쓰는 모든 P2P의 완전 차단 증거가 아니다.
- SSH는 fail2ban으로 10분 안의 5회 실패를 감지해 1시간 차단하고 건강검사에 서비스 상태를 포함한다.
- 가입 계층이 만든 64자리 HMAC 가명 계정 ID마다 활성 WireGuard 공개키를 최대 2개 허용한다.
  같은 개인키를 여러 물리 기기에 복사하면 WireGuard가 그 기기들을 구분할 수 없으므로 키 재사용은 금지한다.
- 구 스키마 원장은 자동 추정 변환하지 않는다. 실제 서버가 생기면 스키마 2 원장으로 시작하고,
  향후 운영 데이터가 생긴 뒤의 마이그레이션은 원본 보존·별도 검증 절차로 수행한다.

## 클라이언트 피어·QR 발급과 폐기

발급기는 검증된 X25519 구현을 사용하고, 개인키 묶음을 프로젝트·Git 저장소 안에는 만들지 않는다.
실서버 공개키와 주소가 생긴 뒤 아래처럼 **프로젝트 밖의 새 폴더**를 지정한다.

```powershell
python -m pip install -r 20_SRC/infra/requirements-peer.txt
python 70_TOOLS/issue_peer_bundle.py `
  --name light-01 `
  --server-public-key '<server-public-key>' `
  --endpoint '198.51.100.20:51820' `
  --client-ip '10.66.0.2/32' `
  --output-dir 'C:\Users\User\Downloads\FreeFlexVPN-light-01'
```

endpoint의 `198.51.100.20`은 문서용 TEST-NET 주소라 그대로 쓰면 안 된다. 결과 폴더의 `.conf`와
QR PNG에는 동일한 클라이언트 개인키가 있으므로 공유·Git 업로드를 금지한다. `SERVER_COMMANDS.txt`에는
공개키 기반 등록·폐기 명령만 있고 개인키는 없다. 등록된 피어는 쿼터 원장에서 재부팅 뒤 자동 복원되며,
폐기한 피어는 WireGuard 런타임에서 제거되고 다시 복원되지 않는다.

### PWA 키 생성 경로

`20_SRC/app/client_keygen.js`는 지원되는 Chromium 계열 브라우저의 Web Crypto X25519로 기기 안에서
개인키를 만들고, 제어 API에는 공개키만 보낸다. 개인키는 브라우저 저장소에 쓰거나 로그로 남기지 않고
WireGuard 구성 텍스트를 만드는 데만 사용한다. X25519를 지원하지 않는 브라우저에서는 성공을 가장하지
않고 공식 WireGuard 앱에서 키를 만든 뒤 공개키만 등록하도록 안내한다.

### 제어 API와 실서버 연결

`20_SRC/app/ssh_node_adapter.py`는 각 노드의 전용 SSH identity와 사전 고정된 `known_hosts` 파일을 사용한다.
`StrictHostKeyChecking=yes`, 비대화형 sudo, 20초 제한을 기본으로 하며 원격 stderr나 공개키 외 비밀값을
API 응답에 복사하지 않는다. 서버에는 `exit_admin.py`가 설치되어 피어 생성·폐기 뒤 실제 WireGuard
readback이 일치할 때만 성공을 반환한다. 서버 공개키·node ID가 설정과 다르면 해당 서버는 카탈로그에서
숨겨진다.

실서버를 연결할 때는 저장소에 비밀값을 넣지 말고 런타임 설정에서 다음 값만 `SSHNodeSpec`으로 주입한다.

- 서버 ID·node ID·국가/도시·공급자 참조
- 공인 exit IP·WireGuard endpoint·서버 공개키·DNS 주소
- SSH host/user/port와 프로젝트 밖 identity/known_hosts 절대 경로
- 공급자 콘솔에서 확인한 exit 검증 시각과 현재 용량률

대한민국 exit, 사설 exit IP, 없는 identity/known_hosts, 잘못된 공개키는 시작 단계에서 거부된다.

제어 서비스는 외부 JSON 설정 경로를 다음처럼 받는다. JSON 자체에도 개인키·비밀번호·토큰은 넣을 수
없으며, SSH 개인키는 `identity_file`이 가리키는 프로젝트 밖 파일에만 둔다.

```powershell
$env:FFVPN_DB_PATH='C:\ProgramData\FreeFlexVPN\control.sqlite3'
$env:FFVPN_NODE_CONFIG='C:\ProgramData\FreeFlexVPN\nodes.json'
python -m app.control_http --host 127.0.0.1 --port 8787
```

`nodes.json`은 `SSHNodeSpec`의 공개 메타데이터와 외부 파일 절대 경로만 담는다. 시작 시 health와 카운터를
한 번 읽고 이후 30~300초 범위의 설정 주기로 갱신한다. 카운터 SSH가 일시 실패해도 HTTP 서비스와 health
폴링은 멈추지 않으며, 누락 구간을 성공처럼 기록하지 않고 다음 누적 카운터에서 다시 정산한다.

### R6 실서버 사전점검

서버 2대 설정을 넣은 뒤 제어 서비스를 공개하기 전에 아래 도구를 실행한다. 서로 다른 공급자 2곳,
서로 다른 출구 IP·endpoint·노드 ID·WireGuard 공개키, 최신 health, 카운터 readback, 공개 카탈로그 일치를
모두 통과해야 `PASS`다. health 시각이 없거나 120초보다 오래됐거나 30초보다 미래이면 서버를 숨긴다.

먼저 SSH 연결을 만들지 않는 설정 전용 검사를 실행한다. 이 결과가 `CONFIGURATION READY`여도 실제 서버
통과는 아니며, 네트워크 요청 수는 0이다.

```powershell
python 70_TOOLS/run_r6_server_preflight.py `
  --config 'C:\ProgramData\FreeFlexVPN\nodes.json' `
  --candidate-id 'R6-candidate-20260802-01' `
  --output 'C:\ProgramData\FreeFlexVPN\evidence\R6_CONFIG_PREFLIGHT_20260802_01.json' `
  --config-only
```

그 다음 같은 후보 ID·설정과 방금 만든 설정검사 증거로 아래 실서버 검사를 실행한다. CLI는 후보 ID와
설정 파일 SHA-256이 증거와 정확히 같고, 설정검사가 네트워크 요청 0건으로 준비 완료됐을 때만 SSH를 시도한다.

```powershell
python 70_TOOLS/run_r6_server_preflight.py `
  --config 'C:\ProgramData\FreeFlexVPN\nodes.json' `
  --candidate-id 'R6-candidate-20260802-01' `
  --config-evidence 'C:\ProgramData\FreeFlexVPN\evidence\R6_CONFIG_PREFLIGHT_20260802_01.json'
```

결과는 기본적으로 `60_OUTPUTS/checks/R6_SERVER_PREFLIGHT_<UTC시각>.json` 새 파일에 원자 저장한다. 기존
증거는 덮어쓰지 않으며, 증거 JSON에는 SSH host·identity 경로·endpoint·IP·공개키·공급자명이 들어가지
않는다. 이 PASS는 **실서버 readback**일 뿐 iOS·Android·Windows 실기기 증거 또는 사용자 성공 증거가 아니다.

## GCP 첫 실제 노드 경로

GCP는 첫 실제 노드 admission까지만 담당한다. 성공해도 `R6 READY=false`이며, 다른 공급자 한 곳을 추가해야
최종 R6을 실행할 수 있다. 먼저 비밀값 없는 예시 계획을 생성해 구조를 확인한다.

```powershell
python 70_TOOLS/build_gcp_node_plan.py --example
```

실제 후보는 GCP project ID와 현재 관리자 공인 IPv4 `/32`를 넣어 프로젝트 안에 새 배포 계획과 cloud-init을
생성한다. 생성된 `commands`는 무료 등급·예산 알림·외부 IPv4·송신 비용을 콘솔에서 확인한 뒤 실행한다.

VM 생성 후 공급자 콘솔에서 공인 exit IP·WireGuard 공개키·SSH host fingerprint를 확인한다. 인증되지 않은
`ssh-keyscan` 결과만으로 known_hosts를 신뢰하지 않는다. 확인된 값으로 프로젝트 밖 runtime config를 만든 뒤
설정검사와 admission을 같은 candidate ID·같은 설정 해시로 실행한다.

```powershell
python 70_TOOLS/run_gcp_node_admission.py `
  --config 'C:\ProgramData\FreeFlexVPN\gcp-node.json' `
  --candidate-id 'GCP-candidate-YYYYMMDD-01' `
  --output 'C:\ProgramData\FreeFlexVPN\evidence\GCP_NODE_CONFIG_YYYYMMDD_01.json' `
  --config-only

python 70_TOOLS/run_gcp_node_admission.py `
  --config 'C:\ProgramData\FreeFlexVPN\gcp-node.json' `
  --candidate-id 'GCP-candidate-YYYYMMDD-01' `
  --config-evidence 'C:\ProgramData\FreeFlexVPN\evidence\GCP_NODE_CONFIG_YYYYMMDD_01.json'
```

예산 알림은 지출 차단 장치가 아니다. 계정의 무료 등급·크레딧 종료일과 외부 IPv4·송신 비용을 별도로 확인하고,
예상 밖 과금 시 VM·주소를 중지/삭제하는 운영 절차를 함께 둔다.

### Cloud Shell 실행 묶음

로컬 `gcloud`가 시작되지 않아도 검증된 GCP plan과 cloud-init에서 Cloud Shell용 묶음을 생성할 수 있다.
예시 묶음은 구조 확인용이며 스크립트가 모든 `gcloud` 호출 전에 `EXAMPLE_ONLY`로 종료한다.

```powershell
python 70_TOOLS/build_gcp_cloud_shell_bundle.py `
  --plan 60_OUTPUTS/infra/FreeFlexVPN_gcp_node_plan_v1_EXAMPLE.json `
  --cloud-init 60_OUTPUTS/infra/FreeFlexVPN_gcp_node_cloud_init_v1_EXAMPLE.yaml `
  --output-dir 60_OUTPUTS/infra/FreeFlexVPN_gcp_cloud_shell_bundle_v2_EXAMPLE `
  --example
```

실제 후보는 `DEPLOY_CANDIDATE` plan으로 새 프로젝트 밖 전송 폴더를 생성한다. Cloud Shell에서는 README 순서대로
읽기 전용 preflight를 먼저 실행하고, 무료 등급·크레딧 만료·예산 알림·외부 IPv4·송신 비용을 직접 확인한다.
배포는 `FREEFLEX_COST_REVIEWED=YES`, 정확한 `FREEFLEX_PROJECT_CONFIRM`, `FREEFLEX_APPLY=YES`가 모두 필요하다.
provider readback v2는 공급자 API JSON을 `verify_provider_readback.py`로 검사한다. VM 실행 상태·machine type·
IP forwarding·무서비스계정, Shielded VM 3종, 단일 10GB pd-standard 부팅 디스크, 예약 공인 IPv4와 VM NAT IP,
cloud-init SHA-256, 기본 네트워크와 정확한 SSH/WireGuard 방화벽이 모두 계획과 일치해야 통과한다. 통과해도
WireGuard admission이나 R6 증거는 아니다. 이상 시 rollback은 이 묶음이 만든 VM·예약 IP·SSH/WireGuard
방화벽만 삭제하며 프로젝트와 Compute API는 보존한다.

## 현재 증거 한계

- 구현·로컬: cloud-init·쿼터·피어 구성·QR 왕복·폐기/재부팅 복원 계약까지 검증 가능
- 대상 서버: 아직 0대이므로 cloud-init 실제 부팅, `cloud-init schema --system`, nft 쿼터 차단 미검증
- VPN 연결: 피어가 아직 없으므로 터널·출구 IP·DNS 누수 검증 미실시

공식 근거: cloud-init은 배포 대상에서 `cloud-init schema`로 최종 검사하고, Ubuntu WireGuard 출구
게이트웨이는 IPv4 forwarding과 masquerade가 필요하다.
