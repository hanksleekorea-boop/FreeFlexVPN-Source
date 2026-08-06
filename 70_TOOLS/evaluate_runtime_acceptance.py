#!/usr/bin/env python3
"""프로젝트 밖의 T1~T10 JSON 증거를 읽어 실패 폐쇄형 판정을 출력한다."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.runtime_acceptance import evaluate_runtime_acceptance  # noqa: E402
from app.runtime_evidence import EvidenceBundleError, verify_evidence_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", help="프로젝트 밖 FreeFlexVPNRuntimeEvidenceBundleV2 JSON 경로")
    args = parser.parse_args()
    source = pathlib.Path(args.evidence).resolve()
    if ROOT == source or ROOT in source.parents:
        parser.error("실환경 IP·기기·사용자 증거는 프로젝트 밖에서만 읽습니다")
    try:
        payload, verified = verify_evidence_bundle(source, project_root=ROOT)
        result = evaluate_runtime_acceptance(payload, verified_artifacts=verified)
    except (EvidenceBundleError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ready": False, "status": "invalid_bundle", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
