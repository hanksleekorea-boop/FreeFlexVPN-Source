#!/usr/bin/env bash
# Read-only preflight. It never enables APIs or creates/deletes resources.
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
command -v gcloud >/dev/null || { echo "gcloud가 없습니다." >&2; exit 69; }
command -v sha256sum >/dev/null || { echo "sha256sum이 없습니다." >&2; exit 69; }
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "활성 Google 계정이 없습니다. Cloud Shell 로그인 상태를 확인하세요." >&2
  exit 65
fi
gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null
ACTUAL_HASH="$(sha256sum "$SCRIPT_DIR/cloud-init.yaml" | awk '{print toupper($1)}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_CLOUD_INIT_SHA256" ]] || { echo "cloud-init 해시 불일치" >&2; exit 66; }
BILLING_ENABLED="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || true)"
[[ "$BILLING_ENABLED" == "True" || "$BILLING_ENABLED" == "true" ]] || { echo "결제 연결 여부를 읽지 못했거나 비활성입니다." >&2; exit 67; }
echo "PASS: 계정·프로젝트·결제 연결·cloud-init 해시를 읽기 전용으로 확인했습니다."
echo "REQUIRED MANUAL REVIEW: 무료 등급/크레딧 만료, 예산 알림, 외부 IPv4, 송신 비용."
echo "예산 알림은 지출을 자동 차단하지 않습니다."
