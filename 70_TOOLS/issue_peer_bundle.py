#!/usr/bin/env python3
"""저장소 밖에 FreeFlexVPN 클라이언트 구성·QR 묶음을 발급한다."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.peer_bundle import PeerSpec, build_bundle

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--server-public-key", required=True)
    parser.add_argument("--endpoint", required=True, help="서버IPv4또는호스트명:WireGuard포트")
    parser.add_argument("--client-ip", required=True, help="10.66.0.2/32 형식")
    parser.add_argument("--dns", default="1.1.1.1")
    parser.add_argument("--output-dir", type=pathlib.Path, required=True, help="프로젝트 밖의 새 폴더")
    args = parser.parse_args()

    result = build_bundle(
        PeerSpec(args.name, args.server_public_key, args.endpoint, args.client_ip, args.dns),
        args.output_dir,
    )
    safe = {
        "status": "PASS",
        "output_dir": result["output_dir"],
        "peer_name": result["peer_name"],
        "file_count": len(result["files"]) + 1,
        "qr_payload_match": result["qr_payload_match"],
        "private_material_in_project": result["private_material_in_project"],
    }
    print(json.dumps(safe, ensure_ascii=False))
    print("개인키·클라이언트 구성 내용은 stdout과 저장소에 출력하지 않았습니다.")


if __name__ == "__main__":
    main()

