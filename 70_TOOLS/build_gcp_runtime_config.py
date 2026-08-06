#!/usr/bin/env python3
"""콘솔에서 확인한 GCP 첫 노드 값을 프로젝트 밖 runtime config로 안전하게 기록한다."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_runtime import load_runtime_settings  # noqa: E402


def _inside_project(path: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def _write_new(path: pathlib.Path, payload: dict[str, object]) -> None:
    if not path.is_absolute() or _inside_project(path):
        raise ValueError("runtime config 출력은 프로젝트 밖 절대 경로여야 합니다")
    if path.exists():
        raise FileExistsError(f"기존 runtime config는 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--server-id", default="gcp-usw1-01")
    parser.add_argument("--host", required=True)
    parser.add_argument("--ssh-user", default="freeflex")
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--identity-file", required=True, type=pathlib.Path)
    parser.add_argument("--known-hosts-file", required=True, type=pathlib.Path)
    parser.add_argument("--country-code", default="US")
    parser.add_argument("--country", default="United States")
    parser.add_argument("--city", default="Oregon")
    parser.add_argument("--exit-ip", required=True)
    parser.add_argument("--wg-port", type=int, default=51820)
    parser.add_argument("--server-public-key", required=True)
    parser.add_argument("--verified-at", required=True, help="timezone 포함 ISO-8601")
    parser.add_argument("--dns", action="append", default=[])
    parser.add_argument("--capacity-percent", type=int, default=10)
    args = parser.parse_args()
    dns = args.dns or ["1.1.1.1"]
    output = args.output.resolve()
    payload = {
        "nodes": [{
            "server_id": args.server_id, "node_id": args.server_id,
            "host": args.host, "ssh_user": args.ssh_user, "ssh_port": args.ssh_port,
            "identity_file": str(args.identity_file.resolve()),
            "known_hosts_file": str(args.known_hosts_file.resolve()),
            "country_code": args.country_code, "country": args.country, "city": args.city,
            "provider_ref": "gcp", "exit_ip": args.exit_ip,
            "endpoint": f"{args.exit_ip}:{args.wg_port}",
            "server_public_key": args.server_public_key,
            "dns_addresses": dns, "exit_verified": True,
            "verified_at": args.verified_at, "capacity_percent": args.capacity_percent,
        }],
        "health_interval_seconds": 60,
        "counter_interval_seconds": 60,
    }
    _write_new(output, payload)
    try:
        load_runtime_settings(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    print(f"GCP runtime config 생성 PASS — {output}")
    print("비밀값 포함 0 · identity 파일 경로만 기록 · 기존 파일 덮어쓰기 금지")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
