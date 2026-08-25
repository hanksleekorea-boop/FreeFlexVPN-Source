#!/usr/bin/env python3
"""Locate and read one approved GCP VPN target without disclosing project identifiers."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_target_locator import locate_and_check  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcloud", required=True)
    parser.add_argument("--expected-target-fingerprint", required=True)
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--instance", default="gcp-usw1-01")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="new redacted JSON receipt; never overwrites")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"existing receipt is never overwritten: {output}")
    receipt = locate_and_check(
        gcloud=args.gcloud, expected_target_fingerprint=args.expected_target_fingerprint,
        zone=args.zone, instance=args.instance,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"GCP target locator: {receipt['status']} · provider={receipt.get('provider_status', 'not_attempted')} · mutation 0")
    return 0 if receipt["server_internal_readback_ready"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
