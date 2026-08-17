#!/usr/bin/env python3
"""비식별 실제 모바일·PC 증거 영수증을 검사하는 명령줄 도구."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.platform_evidence import (  # noqa: E402
    PlatformEvidenceError,
    summarize_platform_evidence,
    verify_platform_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="FreeFlexVPN 실제 플랫폼 증거 영수증 검사")
    parser.add_argument("receipt", help="프로젝트 밖 비식별 영수증 JSON")
    args = parser.parse_args()
    try:
        verified = verify_platform_evidence(args.receipt, project_root=ROOT)
    except (OSError, PlatformEvidenceError) as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(summarize_platform_evidence(verified), ensure_ascii=False, sort_keys=True))
    return 0 if verified.connection_ready else 3


if __name__ == "__main__":
    raise SystemExit(main())
