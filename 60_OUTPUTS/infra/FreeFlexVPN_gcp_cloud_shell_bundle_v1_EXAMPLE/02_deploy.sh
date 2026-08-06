#!/usr/bin/env bash
# Mutating deployment. Three explicit acknowledgements are required.
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
[[ "${FREEFLEX_COST_REVIEWED:-}" == "YES" ]] || { echo "FREEFLEX_COST_REVIEWED=YES가 필요합니다." >&2; exit 70; }
[[ "${FREEFLEX_PROJECT_CONFIRM:-}" == "$PROJECT_ID" ]] || { echo "FREEFLEX_PROJECT_CONFIRM에 project ID를 정확히 입력하세요." >&2; exit 70; }
[[ "${FREEFLEX_APPLY:-}" == "YES" ]] || { echo "FREEFLEX_APPLY=YES가 필요합니다." >&2; exit 70; }
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "활성 Google 계정이 없습니다. Cloud Shell 로그인 상태를 확인하세요." >&2
  exit 65
fi
gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null
ACTUAL_HASH="$(sha256sum "$SCRIPT_DIR/cloud-init.yaml" | awk '{print toupper($1)}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_CLOUD_INIT_SHA256" ]] || { echo "cloud-init 해시 불일치" >&2; exit 66; }
gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" >/dev/null 2>&1 && { echo "동일 VM이 이미 있습니다." >&2; exit 71; } || true
gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1 && { echo "동일 예약 IP가 이미 있습니다." >&2; exit 71; } || true
gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" >/dev/null 2>&1 && { echo "동일 SSH 방화벽 규칙이 이미 있습니다." >&2; exit 71; } || true
gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" >/dev/null 2>&1 && { echo "동일 WireGuard 방화벽 규칙이 이미 있습니다." >&2; exit 71; } || true
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"
gcloud compute firewall-rules create "$SSH_RULE" --project="$PROJECT_ID" --network=default --direction=INGRESS --action=ALLOW --rules="tcp:$SSH_PORT" --source-ranges="$SSH_SOURCE" --target-tags=freeflexvpn-exit
gcloud compute firewall-rules create "$WG_RULE" --project="$PROJECT_ID" --network=default --direction=INGRESS --action=ALLOW --rules="udp:$WG_PORT" --source-ranges=0.0.0.0/0 --target-tags=freeflexvpn-exit
gcloud compute addresses create "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION"
gcloud compute instances create "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --machine-type="$MACHINE_TYPE" --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=10GB --boot-disk-type=pd-standard --address="$ADDRESS_NAME" --can-ip-forward --tags=freeflexvpn-exit --no-service-account --no-scopes --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --metadata-from-file="user-data=$SCRIPT_DIR/cloud-init.yaml"
echo "CREATE FINISHED, NOT ADMITTED: 03_provider_readback.sh와 공급자 콘솔 검증을 계속하세요."
