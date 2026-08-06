#!/usr/bin/env bash
# Exact-resource rollback. It does not disable the Compute API or delete the project.
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
[[ "${FREEFLEX_PROJECT_CONFIRM:-}" == "$PROJECT_ID" ]] || { echo "FREEFLEX_PROJECT_CONFIRM 불일치" >&2; exit 73; }
[[ "${FREEFLEX_ROLLBACK:-}" == "YES" ]] || { echo "FREEFLEX_ROLLBACK=YES가 필요합니다." >&2; exit 73; }
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "활성 Google 계정이 없습니다. Cloud Shell 로그인 상태를 확인하세요." >&2
  exit 65
fi
gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null
if gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" >/dev/null 2>&1; then gcloud compute instances delete "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --quiet; fi
if gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1; then gcloud compute addresses delete "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" --quiet; fi
if gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then gcloud compute firewall-rules delete "$SSH_RULE" --project="$PROJECT_ID" --quiet; fi
if gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then gcloud compute firewall-rules delete "$WG_RULE" --project="$PROJECT_ID" --quiet; fi
echo "ROLLBACK FINISHED: project와 Compute API는 보존했습니다. 콘솔에서 잔여 과금 리소스를 다시 확인하세요."
