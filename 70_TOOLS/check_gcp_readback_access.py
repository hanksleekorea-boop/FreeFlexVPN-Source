#!/usr/bin/env python3
"""Check existing GCP VPN-node read access and write a redacted receipt."""
from __future__ import annotations

import argparse
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_readback_access import check_readback_access, write_new_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcloud", required=True, help="gcloud executable path")
    parser.add_argument("--project", required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    receipt = check_readback_access(
        gcloud=args.gcloud,
        project=args.project,
        zone=args.zone,
        instance=args.instance,
    )
    write_new_json(args.output, receipt)
    print(f"GCP readback access: {receipt['status']}")
    print(f"receipt: {args.output.resolve()}")
    return 0 if receipt["status"] == "provider_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
