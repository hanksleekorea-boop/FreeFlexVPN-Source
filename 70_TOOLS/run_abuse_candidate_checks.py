#!/usr/bin/env python3
"""남용 방지 후보의 관련 검사를 한 Python 프로세스에서 순차 실행한다.

각 기존 검사 파일을 그대로 소비하며 종료 코드 0 외에는 즉시 실패한다. 검사 항목을
재구현하거나 통과 조건을 완화하지 않는다.
"""
from __future__ import annotations

import pathlib
import runpy
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = (
    "40_TESTS/test_abuse_controls.py",
    "40_TESTS/test_quota_agent.py",
    "40_TESTS/test_cloud_init.py",
    "40_TESTS/test_peer_bundle.py",
    "70_TOOLS/scan_secrets.py",
)


def run_one(relative: str) -> int:
    path = ROOT / relative
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def main() -> int:
    passed = 0
    for relative in CHECKS:
        print(f"[표적] {relative}", flush=True)
        rc = run_one(relative)
        if rc != 0:
            print(f"표적 검사 FAIL — {relative} rc={rc}", file=sys.stderr, flush=True)
            return rc
        passed += 1
    print(f"남용 방지 후보 표적 스크립트 {passed}/{len(CHECKS)} 통과", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
