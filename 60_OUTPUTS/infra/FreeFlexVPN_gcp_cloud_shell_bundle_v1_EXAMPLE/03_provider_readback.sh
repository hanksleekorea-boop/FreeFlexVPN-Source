#!/usr/bin/env bash
# Provider API readback only. This is not SSH/WireGuard admission evidence.
set -euo pipefail
MODE=EXAMPLE_ONLY
PROJECT_ID=freeflex-example-123456
ZONE=us-west1-b
REGION=us-west1
NODE_ID=gcp-usw1-01
MACHINE_TYPE=e2-micro
SSH_SOURCE=203.0.113.10/32
SSH_PORT=22
WG_PORT=51820
ADDRESS_NAME=gcp-usw1-01-ip
SSH_RULE=gcp-usw1-01-ssh
WG_RULE=gcp-usw1-01-wg
EXPECTED_CLOUD_INIT_SHA256=C415D18F3B0CF59AC8364D00F8B4C9DEF4CD7D4A28B7736FDF8C111D9FE027EA
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [[ "$MODE" == "EXAMPLE_ONLY" ]]; then
  echo "EXAMPLE_ONLY: 이 묶음은 구조 확인용이며 클라우드 명령을 실행하지 않습니다." >&2
  exit 64
fi
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "활성 Google 계정이 없습니다. Cloud Shell 로그인 상태를 확인하세요." >&2
  exit 65
fi
gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null
MACHINE="$(gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format='value(machineType.basename())')"
FORWARD="$(gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format='value(canIpForward)')"
SERVICE_ACCOUNT="$(gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format='value(serviceAccounts.email)')"
IP="$(gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(address)')"
SSH_RANGE="$(gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" --format='value(sourceRanges.list())')"
WG_RANGE="$(gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" --format='value(sourceRanges.list())')"
[[ "$MACHINE" == "$MACHINE_TYPE" ]] || { echo "machine type 불일치" >&2; exit 72; }
[[ "$FORWARD" == "True" || "$FORWARD" == "true" ]] || { echo "IP forwarding 불일치" >&2; exit 72; }
[[ -z "$SERVICE_ACCOUNT" ]] || { echo "예상하지 않은 service account가 있습니다." >&2; exit 72; }
[[ "$SSH_RANGE" == "$SSH_SOURCE" ]] || { echo "SSH source range 불일치" >&2; exit 72; }
[[ "$WG_RANGE" == "0.0.0.0/0" ]] || { echo "WireGuard source range 불일치" >&2; exit 72; }
printf '{"schema":"FreeFlexVPNGCPProviderReadbackV1","project_id":"%s","zone":"%s","node_id":"%s","machine_type":"%s","can_ip_forward":true,"service_account_present":false,"reserved_ip":"%s","ssh_source":"%s","wireguard_source":"0.0.0.0/0","admission_ready":false,"r6_ready":false}
' "$PROJECT_ID" "$ZONE" "$NODE_ID" "$MACHINE" "$IP" "$SSH_RANGE" > "$SCRIPT_DIR/provider-readback.json"
echo "PROVIDER READBACK PASS, NOT ADMITTED: provider-readback.json은 IP를 포함하므로 저장소에 커밋하지 마세요."
echo "다음: 공급자 콘솔에서 cloud-init 상태·서버 공개키·SSH host fingerprint를 확인하세요."
