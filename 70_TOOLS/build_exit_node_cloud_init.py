#!/usr/bin/env python3
"""FreeFlexVPN 전용 출구 노드 cloud-init 후보를 생성한다."""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.cloud_init import EXAMPLE_ADMIN_CIDR, ExitNodeSpec, parse_rendered, render_cloud_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-ssh-cidr", help="관리자 현재 공인 IPv4 한 개(/32)")
    parser.add_argument("--wg-port", type=int, default=51820)
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--node-id", default="exit-01")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--example", action="store_true", help="배포 불가 TEST-NET 예시 생성")
    args = parser.parse_args()

    if args.example:
        cidr = EXAMPLE_ADMIN_CIDR
    elif args.admin_ssh_cidr:
        cidr = args.admin_ssh_cidr
    else:
        parser.error("실배포 후보는 --admin-ssh-cidr <현재공인IP>/32가 필수입니다")

    spec = ExitNodeSpec(cidr, args.wg_port, args.ssh_port, args.node_id, args.example).validated()
    text = render_cloud_config(spec)
    parse_rendered(text)
    if re.search(r"__[A-Z][A-Z0-9_]*__", text) or "0.0.0.0/0 tcp dport" in text:
        raise SystemExit("FATAL: 미치환 토큰 또는 전면 SSH 허용을 발견했습니다")

    output = args.output
    if output is None:
        suffix = "_EXAMPLE" if args.example else ""
        output = ROOT / "60_OUTPUTS" / "infra" / f"FreeFlexVPN_exit_node_cloud_init_v1{suffix}.yaml"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    print(f"cloud-init 생성 PASS — {output}")
    print(f"SHA-256 {digest}")
    print("비밀값 포함 0 · WireGuard 개인키는 서버 첫 부팅 때 서버 안에서만 생성")
    if args.example:
        print("상태 EXAMPLE_ONLY — TEST-NET 주소이므로 서버 투입 금지")


if __name__ == "__main__":
    main()
