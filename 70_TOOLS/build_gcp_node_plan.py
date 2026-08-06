#!/usr/bin/env python3
"""GCP 첫 exit 노드의 cloud-init과 배포 명령 계획을 새 파일로 생성한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.cloud_init import EXAMPLE_ADMIN_CIDR, ExitNodeSpec, render_cloud_config  # noqa: E402
from infra.gcp_node_plan import EXAMPLE_PROJECT_ID, GCPNodePlanSpec, build_gcp_plan  # noqa: E402


def _write_new(path: pathlib.Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"기존 파일은 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id")
    parser.add_argument("--admin-ssh-cidr")
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--node-id", default="gcp-usw1-01")
    parser.add_argument("--wg-port", type=int, default=51820)
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--output", type=pathlib.Path, help="새 계획 JSON 경로")
    parser.add_argument("--cloud-init-output", type=pathlib.Path, help="새 cloud-init 경로")
    parser.add_argument("--example", action="store_true")
    args = parser.parse_args()

    project_id = EXAMPLE_PROJECT_ID if args.example else args.project_id
    admin_cidr = EXAMPLE_ADMIN_CIDR if args.example else args.admin_ssh_cidr
    if not project_id or not admin_cidr:
        parser.error("실배포 후보는 --project-id와 --admin-ssh-cidr <현재공인IP>/32가 필요합니다")
    spec = GCPNodePlanSpec(
        project_id=project_id,
        admin_ssh_cidr=admin_cidr,
        zone=args.zone,
        node_id=args.node_id,
        wg_port=args.wg_port,
        ssh_port=args.ssh_port,
        example=args.example,
    ).validated()
    suffix = "_EXAMPLE" if args.example else ""
    plan_path = (args.output or ROOT / "60_OUTPUTS" / "infra" / f"FreeFlexVPN_gcp_node_plan_v1{suffix}.json").resolve()
    cloud_path = (
        args.cloud_init_output
        or ROOT / "60_OUTPUTS" / "infra" / f"FreeFlexVPN_gcp_node_cloud_init_v1{suffix}.yaml"
    ).resolve()
    cloud_text = render_cloud_config(
        ExitNodeSpec(admin_cidr, args.wg_port, args.ssh_port, args.node_id, args.example)
    ).encode("utf-8")
    cloud_sha256 = hashlib.sha256(cloud_text).hexdigest().upper()
    plan = build_gcp_plan(spec, cloud_init_path=str(cloud_path), cloud_init_sha256=cloud_sha256)
    plan_bytes = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_new(cloud_path, cloud_text)
    try:
        _write_new(plan_path, plan_bytes)
    except Exception:
        cloud_path.unlink(missing_ok=True)
        raise
    print(f"GCP 노드 계획 생성 PASS — {plan_path}")
    print(f"cloud-init — {cloud_path} · SHA-256 {cloud_sha256}")
    print("상태 CONFIGURATION TEMPLATE ONLY · R6 READY=false · 비밀값 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
