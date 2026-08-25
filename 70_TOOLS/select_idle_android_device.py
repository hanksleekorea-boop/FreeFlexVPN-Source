#!/usr/bin/env python3
"""Read Android state and select exactly one sleeping, unprotected test candidate or stop."""
from __future__ import annotations

import argparse
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.android_idle_guard import inspect_devices, select_one_idle_device, write_new_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True, help="absolute adb executable path")
    parser.add_argument("--output", type=pathlib.Path, help="new redacted receipt path; never overwrites")
    args = parser.parse_args()
    receipt = select_one_idle_device(inspect_devices(adb=args.adb))
    if args.output:
        write_new_json(args.output, receipt)
        print(f"Android idle selection receipt: {args.output.resolve()}")
    print(f"Android idle selection: {receipt['status']} · eligible {receipt['eligible_count']}/{receipt['device_count']} · mutation 0")
    return 0 if receipt["status"] == "selected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
