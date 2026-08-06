#!/usr/bin/env python3
"""Generate a new no-overwrite GCP Cloud Shell deployment bundle."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_cloud_shell_bundle import build_bundle_files, validate_inputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--cloud-init", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--example", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error(f"기존 경로를 덮어쓰지 않습니다: {output}")
    try:
        plan_bytes = args.plan.resolve().read_bytes()
        cloud_bytes = args.cloud_init.resolve().read_bytes()
        plan = json.loads(plan_bytes.decode("utf-8"))
        spec = validate_inputs(plan, plan_bytes, cloud_bytes, example=args.example)
        files = build_bundle_files(spec, cloud_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    temp = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    if temp.exists():
        parser.error(f"임시 경로가 이미 있습니다: {temp}")
    try:
        temp.mkdir(parents=True)
        for name, data in files.items():
            (temp / name).write_bytes(data)
        temp.replace(output)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    print(json.dumps({"output_dir": str(output), "mode": spec.mode, "files": sorted(files), "contains_secrets": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
