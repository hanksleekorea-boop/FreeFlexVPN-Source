#!/usr/bin/env python3
"""모바일·PC·상업 운영 외부 증거로 95% 출시 후보 게이트를 판정한다."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.release_95_gate import Release95EvidenceError, verify_and_evaluate_release_95  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="FreeFlexVPN 95% 출시 증거 게이트")
    parser.add_argument("--mobile", required=True, help="프로젝트 밖 모바일 영수증")
    parser.add_argument("--pc", required=True, help="프로젝트 밖 PC 영수증")
    parser.add_argument("--operations", required=True, help="프로젝트 밖 상업 운영 증거 번들")
    args = parser.parse_args()
    try:
        result = verify_and_evaluate_release_95(
            mobile_receipt=args.mobile,
            pc_receipt=args.pc,
            operations_bundle=args.operations,
            project_root=ROOT,
        )
    except (OSError, Release95EvidenceError) as exc:
        print(json.dumps({"target_95_ready": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["target_95_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
