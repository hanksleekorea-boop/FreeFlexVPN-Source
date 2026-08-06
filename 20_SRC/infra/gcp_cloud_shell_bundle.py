#!/usr/bin/env python3
"""Build a fail-closed Cloud Shell bundle from a verified GCP node plan."""
from __future__ import annotations

import hashlib
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infra.gcp_node_plan import GCPNodePlanSpec


BUNDLE_SCHEMA = "FreeFlexVPNGCPCloudShellBundleV2"
PLAN_SCHEMA = "FreeFlexVPNGCPNodePlanV1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _q(value: str) -> str:
    return shlex.quote(value)


@dataclass(frozen=True)
class CloudShellBundleSpec:
    project_id: str
    zone: str
    region: str
    node_id: str
    machine_type: str
    ssh_source: str
    ssh_port: int
    wg_port: int
    address_name: str
    mode: str
    cloud_init_sha256: str
    source_plan_sha256: str

    @property
    def example(self) -> bool:
        return self.mode == "EXAMPLE_ONLY"

    @property
    def ssh_rule(self) -> str:
        return f"{self.node_id}-ssh"

    @property
    def wg_rule(self) -> str:
        return f"{self.node_id}-wg"


def validate_inputs(plan: dict[str, Any], plan_bytes: bytes, cloud_init: bytes, *, example: bool) -> CloudShellBundleSpec:
    if plan.get("schema") != PLAN_SCHEMA or plan.get("provider") != "gcp":
        raise ValueError("GCP node plan v1만 허용합니다")
    expected_mode = "EXAMPLE_ONLY" if example else "DEPLOY_CANDIDATE"
    if plan.get("mode") != expected_mode:
        raise ValueError(f"plan mode must be {expected_mode}")
    if plan.get("contains_secrets") is not False:
        raise ValueError("비밀값 없음이 명시된 plan만 허용합니다")
    gates = plan.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("plan gates가 없습니다")
    required_gates = {
        "free_tier_eligibility": "VERIFY_IN_GCP_CONSOLE_BEFORE_CREATE",
        "billing_budget_alert": "REQUIRED_BUT_NOT_A_HARD_SPEND_CAP",
        "external_ipv4_and_egress": "MAY_BE_BILLABLE",
        "r6_ready": False,
        "provider_diversity_credit": 1,
        "next_provider_required": True,
    }
    for key, expected in required_gates.items():
        if gates.get(key) != expected:
            raise ValueError(f"안전 gate 불일치: {key}")
    network = plan.get("network")
    cloud = plan.get("cloud_init")
    if not isinstance(network, dict) or not isinstance(cloud, dict):
        raise ValueError("network/cloud_init 계약이 없습니다")
    actual_cloud_hash = sha256_bytes(cloud_init)
    if cloud.get("sha256") != actual_cloud_hash:
        raise ValueError("cloud-init SHA-256이 plan과 다릅니다")
    node_spec = GCPNodePlanSpec(
        project_id=str(plan.get("project_id", "")),
        admin_ssh_cidr=str(network.get("ssh_source", "")),
        zone=str(plan.get("zone", "")),
        node_id=str(plan.get("node_id", "")),
        machine_type=str(plan.get("machine_type", "")),
        wg_port=int(network.get("wireguard_udp_port", 0)),
        ssh_port=int(network.get("ssh_port", 0)),
        example=example,
    ).validated()
    if plan.get("region") != node_spec.region:
        raise ValueError("zone과 region이 일치하지 않습니다")
    if network.get("can_ip_forward") is not True or network.get("wireguard_source") != "0.0.0.0/0":
        raise ValueError("필수 forwarding/WireGuard 방화벽 계약이 없습니다")
    expected_address = f"{node_spec.node_id}-ip"
    if network.get("reserved_address_name") != expected_address:
        raise ValueError("예약 IP 이름이 node ID와 일치하지 않습니다")
    return CloudShellBundleSpec(
        project_id=node_spec.project_id,
        zone=node_spec.zone,
        region=node_spec.region,
        node_id=node_spec.node_id,
        machine_type=node_spec.machine_type,
        ssh_source=node_spec.admin_ssh_cidr,
        ssh_port=node_spec.ssh_port,
        wg_port=node_spec.wg_port,
        address_name=expected_address,
        mode=expected_mode,
        cloud_init_sha256=actual_cloud_hash,
        source_plan_sha256=sha256_bytes(plan_bytes),
    )


def _variables(spec: CloudShellBundleSpec) -> str:
    return "\n".join([
        "set -euo pipefail",
        f"MODE={_q(spec.mode)}",
        f"PROJECT_ID={_q(spec.project_id)}",
        f"ZONE={_q(spec.zone)}",
        f"REGION={_q(spec.region)}",
        f"NODE_ID={_q(spec.node_id)}",
        f"MACHINE_TYPE={_q(spec.machine_type)}",
        f"SSH_SOURCE={_q(spec.ssh_source)}",
        f"SSH_PORT={spec.ssh_port}",
        f"WG_PORT={spec.wg_port}",
        f"ADDRESS_NAME={_q(spec.address_name)}",
        f"SSH_RULE={_q(spec.ssh_rule)}",
        f"WG_RULE={_q(spec.wg_rule)}",
        f"EXPECTED_CLOUD_INIT_SHA256={_q(spec.cloud_init_sha256)}",
        "SCRIPT_DIR=\"$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\"",
    ])


def _example_guard() -> str:
    return """if [[ "$MODE" == "EXAMPLE_ONLY" ]]; then
  echo "EXAMPLE_ONLY: 이 묶음은 구조 확인용이며 클라우드 명령을 실행하지 않습니다." >&2
  exit 64
fi"""


def _auth_guard() -> str:
    return """ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "활성 Google 계정이 없습니다. Cloud Shell 로그인 상태를 확인하세요." >&2
  exit 65
fi
gcloud projects describe "$PROJECT_ID" --format='value(projectId)' >/dev/null"""


def render_preflight(spec: CloudShellBundleSpec) -> str:
    return f"""#!/usr/bin/env bash
# Read-only preflight. It never enables APIs or creates/deletes resources.
{_variables(spec)}
{_example_guard()}
command -v gcloud >/dev/null || {{ echo "gcloud가 없습니다." >&2; exit 69; }}
command -v sha256sum >/dev/null || {{ echo "sha256sum이 없습니다." >&2; exit 69; }}
{_auth_guard()}
ACTUAL_HASH="$(sha256sum "$SCRIPT_DIR/cloud-init.yaml" | awk '{{print toupper($1)}}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_CLOUD_INIT_SHA256" ]] || {{ echo "cloud-init 해시 불일치" >&2; exit 66; }}
BILLING_ENABLED="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || true)"
[[ "$BILLING_ENABLED" == "True" || "$BILLING_ENABLED" == "true" ]] || {{ echo "결제 연결 여부를 읽지 못했거나 비활성입니다." >&2; exit 67; }}
echo "PASS: 계정·프로젝트·결제 연결·cloud-init 해시를 읽기 전용으로 확인했습니다."
echo "REQUIRED MANUAL REVIEW: 무료 등급/크레딧 만료, 예산 알림, 외부 IPv4, 송신 비용."
echo "예산 알림은 지출을 자동 차단하지 않습니다."
"""


def render_deploy(spec: CloudShellBundleSpec) -> str:
    return f"""#!/usr/bin/env bash
# Mutating deployment. Three explicit acknowledgements are required.
{_variables(spec)}
{_example_guard()}
[[ "${{FREEFLEX_COST_REVIEWED:-}}" == "YES" ]] || {{ echo "FREEFLEX_COST_REVIEWED=YES가 필요합니다." >&2; exit 70; }}
[[ "${{FREEFLEX_PROJECT_CONFIRM:-}}" == "$PROJECT_ID" ]] || {{ echo "FREEFLEX_PROJECT_CONFIRM에 project ID를 정확히 입력하세요." >&2; exit 70; }}
[[ "${{FREEFLEX_APPLY:-}}" == "YES" ]] || {{ echo "FREEFLEX_APPLY=YES가 필요합니다." >&2; exit 70; }}
{_auth_guard()}
ACTUAL_HASH="$(sha256sum "$SCRIPT_DIR/cloud-init.yaml" | awk '{{print toupper($1)}}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_CLOUD_INIT_SHA256" ]] || {{ echo "cloud-init 해시 불일치" >&2; exit 66; }}
gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" >/dev/null 2>&1 && {{ echo "동일 VM이 이미 있습니다." >&2; exit 71; }} || true
gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1 && {{ echo "동일 예약 IP가 이미 있습니다." >&2; exit 71; }} || true
gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" >/dev/null 2>&1 && {{ echo "동일 SSH 방화벽 규칙이 이미 있습니다." >&2; exit 71; }} || true
gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" >/dev/null 2>&1 && {{ echo "동일 WireGuard 방화벽 규칙이 이미 있습니다." >&2; exit 71; }} || true
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"
gcloud compute firewall-rules create "$SSH_RULE" --project="$PROJECT_ID" --network=default --direction=INGRESS --action=ALLOW --rules="tcp:$SSH_PORT" --source-ranges="$SSH_SOURCE" --target-tags=freeflexvpn-exit
gcloud compute firewall-rules create "$WG_RULE" --project="$PROJECT_ID" --network=default --direction=INGRESS --action=ALLOW --rules="udp:$WG_PORT" --source-ranges=0.0.0.0/0 --target-tags=freeflexvpn-exit
gcloud compute addresses create "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION"
gcloud compute instances create "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --machine-type="$MACHINE_TYPE" --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=10GB --boot-disk-type=pd-standard --address="$ADDRESS_NAME" --can-ip-forward --tags=freeflexvpn-exit --no-service-account --no-scopes --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --metadata-from-file="user-data=$SCRIPT_DIR/cloud-init.yaml"
echo "CREATE FINISHED, NOT ADMITTED: 03_provider_readback.sh와 공급자 콘솔 검증을 계속하세요."
"""


def render_readback(spec: CloudShellBundleSpec) -> str:
    return f"""#!/usr/bin/env bash
# Provider API readback only. This is not SSH/WireGuard admission evidence.
{_variables(spec)}
{_example_guard()}
{_auth_guard()}
command -v python3 >/dev/null || {{ echo "python3가 없습니다." >&2; exit 69; }}
INSTANCE_JSON="$(mktemp)"
ADDRESS_JSON="$(mktemp)"
DISK_JSON="$(mktemp)"
SSH_JSON="$(mktemp)"
WG_JSON="$(mktemp)"
cleanup() {{ rm -f -- "$INSTANCE_JSON" "$ADDRESS_JSON" "$DISK_JSON" "$SSH_JSON" "$WG_JSON"; }}
trap cleanup EXIT
gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format=json > "$INSTANCE_JSON"
gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" --format=json > "$ADDRESS_JSON"
gcloud compute disks describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --format=json > "$DISK_JSON"
gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" --format=json > "$SSH_JSON"
gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" --format=json > "$WG_JSON"
python3 "$SCRIPT_DIR/verify_provider_readback.py" \
  --project-id "$PROJECT_ID" --zone "$ZONE" --region "$REGION" \
  --node-id "$NODE_ID" --machine-type "$MACHINE_TYPE" --address-name "$ADDRESS_NAME" \
  --ssh-rule "$SSH_RULE" --wg-rule "$WG_RULE" --ssh-source "$SSH_SOURCE" \
  --ssh-port "$SSH_PORT" --wg-port "$WG_PORT" --cloud-init-sha256 "$EXPECTED_CLOUD_INIT_SHA256" \
  --instance "$INSTANCE_JSON" --address "$ADDRESS_JSON" --disk "$DISK_JSON" \
  --ssh-firewall "$SSH_JSON" --wg-firewall "$WG_JSON" \
  --output "$SCRIPT_DIR/provider-readback-v2.json"
echo "PROVIDER READBACK PASS, NOT ADMITTED: provider-readback-v2.json은 IP를 포함하므로 저장소에 커밋하지 마세요."
echo "다음: 공급자 콘솔에서 cloud-init 상태·서버 공개키·SSH host fingerprint를 확인하세요."
"""


def render_rollback(spec: CloudShellBundleSpec) -> str:
    return f"""#!/usr/bin/env bash
# Exact-resource rollback. It does not disable the Compute API or delete the project.
{_variables(spec)}
{_example_guard()}
[[ "${{FREEFLEX_PROJECT_CONFIRM:-}}" == "$PROJECT_ID" ]] || {{ echo "FREEFLEX_PROJECT_CONFIRM 불일치" >&2; exit 73; }}
[[ "${{FREEFLEX_ROLLBACK:-}}" == "YES" ]] || {{ echo "FREEFLEX_ROLLBACK=YES가 필요합니다." >&2; exit 73; }}
{_auth_guard()}
if gcloud compute instances describe "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" >/dev/null 2>&1; then gcloud compute instances delete "$NODE_ID" --project="$PROJECT_ID" --zone="$ZONE" --quiet; fi
if gcloud compute addresses describe "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1; then gcloud compute addresses delete "$ADDRESS_NAME" --project="$PROJECT_ID" --region="$REGION" --quiet; fi
if gcloud compute firewall-rules describe "$SSH_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then gcloud compute firewall-rules delete "$SSH_RULE" --project="$PROJECT_ID" --quiet; fi
if gcloud compute firewall-rules describe "$WG_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then gcloud compute firewall-rules delete "$WG_RULE" --project="$PROJECT_ID" --quiet; fi
echo "ROLLBACK FINISHED: project와 Compute API는 보존했습니다. 콘솔에서 잔여 과금 리소스를 다시 확인하세요."
"""


def render_readme(spec: CloudShellBundleSpec) -> str:
    mode_note = "이 묶음은 EXAMPLE_ONLY라 모든 셸 스크립트가 cloud 명령 전에 종료합니다." if spec.example else "이 묶음은 실제 후보지만 명시적 비용·project·APPLY 확인 없이는 생성하지 않습니다."
    return f"""# FreeFlexVPN GCP Cloud Shell bundle v2

{mode_note}

## 순서

1. Google Cloud Console에서 프로젝트 `{spec.project_id}`와 무료 크레딧 만료·예산 알림·외부 IPv4·송신 비용을 직접 확인합니다.
2. Cloud Shell에 이 폴더를 업로드하고 `bash 01_preflight.sh`를 실행합니다. 이 단계는 읽기 전용입니다.
3. 실제 후보에서만 아래 확인값을 입력한 뒤 배포합니다.

```bash
export FREEFLEX_COST_REVIEWED=YES
export FREEFLEX_PROJECT_CONFIRM={_q(spec.project_id)}
export FREEFLEX_APPLY=YES
bash 02_deploy.sh
bash 03_provider_readback.sh
```

4. provider readback은 VM·디스크·Shielded 설정·공인 IP·cloud-init 해시·방화벽을 확인할 뿐 VPN admission이 아닙니다. 공급자 콘솔에서 cloud-init 완료·WireGuard 공개키·SSH fingerprint를 별도 확인합니다.
5. 예상 밖 비용·설정 오류가 있으면 아래처럼 이 묶음이 만든 정확한 네 리소스만 제거합니다.

```bash
export FREEFLEX_PROJECT_CONFIRM={_q(spec.project_id)}
export FREEFLEX_ROLLBACK=YES
bash 04_rollback.sh
```

`provider-readback-v2.json`은 공인 IP를 포함하므로 프로젝트/Git에 복사하지 않습니다. 이 묶음에는 토큰·비밀번호·개인키가 없습니다.
"""


def build_bundle_files(spec: CloudShellBundleSpec, cloud_init: bytes) -> dict[str, bytes]:
    verifier = Path(__file__).with_name("gcp_provider_readback.py").read_bytes()
    files = {
        "README.md": render_readme(spec).encode("utf-8"),
        "01_preflight.sh": render_preflight(spec).encode("utf-8"),
        "02_deploy.sh": render_deploy(spec).encode("utf-8"),
        "03_provider_readback.sh": render_readback(spec).encode("utf-8"),
        "04_rollback.sh": render_rollback(spec).encode("utf-8"),
        "cloud-init.yaml": cloud_init,
        "verify_provider_readback.py": verifier,
    }
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "mode": spec.mode,
        "project_id": spec.project_id,
        "zone": spec.zone,
        "node_id": spec.node_id,
        "source_plan_sha256": spec.source_plan_sha256,
        "cloud_init_sha256": spec.cloud_init_sha256,
        "files_sha256": {name: sha256_bytes(data) for name, data in sorted(files.items())},
        "contains_secrets": False,
        "provider_readback_is_admission": False,
        "r6_ready": False,
    }
    files["bundle-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files
