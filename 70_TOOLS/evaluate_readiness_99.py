#!/usr/bin/env python3
"""외부 증거로 FreeFlexVPN의 99% 목표 충족 여부를 판정한다."""
from __future__ import annotations
import argparse, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))
from app.readiness_99_gate import Readiness99EvidenceError, verify_and_evaluate_readiness_99

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile", required=True); parser.add_argument("--pc", required=True)
    parser.add_argument("--operations", required=True); parser.add_argument("--development", required=True)
    parser.add_argument("--evidence", help="공통 증거 기준표 JSON 파일. 없으면 99% 판정은 모두 미통과입니다.")
    args = parser.parse_args()
    try:
        evidence = None
        if args.evidence:
            with open(args.evidence, "r", encoding="utf-8") as handle:
                evidence = json.load(handle)
        result = verify_and_evaluate_readiness_99(mobile_receipt=args.mobile, pc_receipt=args.pc, operations_bundle=args.operations, development_bundle=args.development, evidence_records=evidence, project_root=ROOT)
    except (OSError, Readiness99EvidenceError) as exc:
        print(json.dumps({"target_99_ready": False, "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True)); return 0 if result["target_99_ready"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
