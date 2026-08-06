#!/usr/bin/env python3
"""비밀값 없이 GCP 첫 exit 노드 배포 계획과 안전 관문을 생성한다."""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any

from infra.cloud_init import EXAMPLE_ADMIN_CIDR, GOOGLE_IAP_TCP_FORWARDING_CIDR, ExitNodeSpec


EXAMPLE_PROJECT_ID = "freeflex-example-123456"
DEFAULT_ZONE = "us-west1-b"
DEFAULT_MACHINE_TYPE = "e2-micro"
ALLOWED_FIRST_NODE_REGIONS = ("us-west1", "us-central1", "us-east1")
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
_ZONE = re.compile(r"([a-z]+-[a-z0-9]+[0-9])-([a-z])")


@dataclass(frozen=True)
class GCPNodePlanSpec:
    project_id: str
    admin_ssh_cidr: str
    zone: str = DEFAULT_ZONE
    node_id: str = "gcp-usw1-01"
    machine_type: str = DEFAULT_MACHINE_TYPE
    wg_port: int = 51820
    ssh_port: int = 22
    example: bool = False

    def validated(self) -> "GCPNodePlanSpec":
        if not _PROJECT_ID.fullmatch(self.project_id):
            raise ValueError("GCP project-id 형식이 올바르지 않습니다")
        if self.project_id == EXAMPLE_PROJECT_ID and not self.example:
            raise ValueError("문서용 project-id는 --example에서만 허용됩니다")
        match = _ZONE.fullmatch(self.zone)
        if not match or match.group(1) not in ALLOWED_FIRST_NODE_REGIONS:
            raise ValueError("첫 GCP 노드는 us-west1/us-central1/us-east1 zone만 허용합니다")
        if self.machine_type != DEFAULT_MACHINE_TYPE:
            raise ValueError("비용 기준선은 e2-micro만 허용합니다")
        ExitNodeSpec(
            admin_ssh_cidr=self.admin_ssh_cidr,
            wg_port=self.wg_port,
            ssh_port=self.ssh_port,
            node_id=self.node_id,
            example=self.example,
        ).validated()
        return self

    @property
    def region(self) -> str:
        match = _ZONE.fullmatch(self.zone)
        if not match:
            raise ValueError("GCP zone 형식이 올바르지 않습니다")
        return match.group(1)


def build_gcp_plan(spec: GCPNodePlanSpec, *, cloud_init_path: str, cloud_init_sha256: str) -> dict[str, Any]:
    spec = spec.validated()
    try:
        admin = ipaddress.ip_network(spec.admin_ssh_cidr, strict=True)
    except ValueError as exc:
        raise ValueError("관리자 SSH CIDR이 올바르지 않습니다") from exc
    tag = "freeflexvpn-exit"
    address = f"{spec.node_id}-ip"
    ssh_rule = f"{spec.node_id}-ssh"
    wg_rule = f"{spec.node_id}-wg"
    quoted_user_data = cloud_init_path.replace("'", "''")
    commands = [
        f"gcloud services enable compute.googleapis.com --project={spec.project_id}",
        (
            f"gcloud compute firewall-rules create {ssh_rule} --project={spec.project_id} "
            f"--network=default --direction=INGRESS --action=ALLOW --rules=tcp:{spec.ssh_port} "
            f"--source-ranges={admin.with_prefixlen} --target-tags={tag}"
        ),
        (
            f"gcloud compute firewall-rules create {wg_rule} --project={spec.project_id} "
            f"--network=default --direction=INGRESS --action=ALLOW --rules=udp:{spec.wg_port} "
            f"--source-ranges=0.0.0.0/0 --target-tags={tag}"
        ),
        f"gcloud compute addresses create {address} --project={spec.project_id} --region={spec.region}",
        (
            f"gcloud compute instances create {spec.node_id} --project={spec.project_id} --zone={spec.zone} "
            f"--machine-type={spec.machine_type} --image-family=ubuntu-2404-lts-amd64 "
            f"--image-project=ubuntu-os-cloud --boot-disk-size=10GB --boot-disk-type=pd-standard "
            f"--address={address} --can-ip-forward --tags={tag} --no-service-account --no-scopes "
            f"--shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring "
            f"--metadata-from-file=user-data='{quoted_user_data}'"
        ),
    ]
    return {
        "schema": "FreeFlexVPNGCPNodePlanV1",
        "mode": "EXAMPLE_ONLY" if spec.example else "DEPLOY_CANDIDATE",
        "provider": "gcp",
        "project_id": spec.project_id,
        "zone": spec.zone,
        "region": spec.region,
        "node_id": spec.node_id,
        "machine_type": spec.machine_type,
        "network": {
            "ssh_source": admin.with_prefixlen,
            "ssh_access_mode": (
                "google_iap"
                if admin.with_prefixlen == GOOGLE_IAP_TCP_FORWARDING_CIDR
                else "single_ipv4"
            ),
            "ssh_port": spec.ssh_port,
            "wireguard_source": "0.0.0.0/0",
            "wireguard_udp_port": spec.wg_port,
            "can_ip_forward": True,
            "reserved_address_name": address,
        },
        "cloud_init": {"path": cloud_init_path, "sha256": cloud_init_sha256},
        "commands": commands,
        "gates": {
            "free_tier_eligibility": "VERIFY_IN_GCP_CONSOLE_BEFORE_CREATE",
            "billing_budget_alert": "REQUIRED_BUT_NOT_A_HARD_SPEND_CAP",
            "external_ipv4_and_egress": "MAY_BE_BILLABLE",
            "provider_console_recovery": "REQUIRED",
            "exit_country_and_ip": "VERIFY_AFTER_CREATE",
            "r6_ready": False,
            "provider_diversity_credit": 1,
            "next_provider_required": True,
        },
        "evidence_level": "configuration template only; no cloud, server, device, or user evidence",
        "contains_secrets": False,
    }
