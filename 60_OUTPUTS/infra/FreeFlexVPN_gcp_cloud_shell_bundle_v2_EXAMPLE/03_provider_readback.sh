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
command -v python3 >/dev/null || { echo "python3가 없습니다." >&2; exit 69; }
INSTANCE_JSON="$(mktemp)"
ADDRESS_JSON="$(mktemp)"
DISK_JSON="$(mktemp)"
SSH_JSON="$(mktemp)"
WG_JSON="$(mktemp)"
cleanup() { rm -f -- "$INSTANCE_JSON" "$ADDRESS_JSON" "$DISK_JSON" "$SSH_JSON" "$WG_JSON"; }
trap cleanup EXIT
gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format=json > "$INSTANCE_JSON"
gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" --format=json > "$ADDRESS_JSON"
gcloud compute disks describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format=json > "$DISK_JSON"
gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" --format=json > "$SSH_JSON"
gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" --format=json > "$WG_JSON"
python3 "$SCRIPT_DIR/verify_provider_readback.py"   --project-id "$PROJECT_ID" --zone "$ZONE" --region "$REGION"   --node-id "$NODE_ID" --machine-type "$MACHINE_TYPE" --address-name "$ADDRESS_NAME"   --ssh-rule "$SSH_RULE" --wg-rule "$WG_RULE" --ssh-source "$SSH_SOURCE"   --ssh-port "$SSH_PORT" --wg-port "$WG_PORT" --cloud-init-sha256 "$EXPECTED_CLOUD_INIT_SHA256"   --instance "$INSTANCE_JSON" --address "$ADDRESS_JSON" --disk "$DISK_JSON"   --ssh-firewall "$SSH_JSON" --wg-firewall "$WG_JSON"   --output "$SCRIPT_DIR/provider-readback-v2.json"
echo "PROVIDER READBACK PASS, NOT ADMITTED: provider-readback-v2.json은 IP를 포함하므로 저장소에 커밋하지 마세요."
echo "다음: 공급자 콘솔에서 cloud-init 상태·서버 공개키·SSH host fingerprint를 확인하세요."
