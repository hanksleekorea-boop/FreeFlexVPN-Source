#!/usr/bin/env python3
"""FreeFlexVPN GCP 첫 노드 비용 검토 JSON을 새 파일로 생성한다."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_cost_review import DESTINATION_RATES_USD_PER_GIB, build_cost_review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", choices=sorted(DESTINATION_RATES_USD_PER_GIB), default="korea")
    parser.add_argument("--usage-gib", type=float, action="append", dest="usages")
    parser.add_argument("--hours", type=float, default=730.0)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"refusing to overwrite existing output: {args.output}")
    review = build_cost_review(
        destination=args.destination,
        usages_gib=tuple(args.usages or (1.0, 10.0, 100.0)),
        hours=args.hours,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GCP 비용 검토 생성 PASS — {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
