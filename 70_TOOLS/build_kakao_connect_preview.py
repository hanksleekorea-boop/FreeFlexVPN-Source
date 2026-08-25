#!/usr/bin/env python3
"""Build the local-only Kakao Connect preview without touching public assets."""
from __future__ import annotations

import argparse
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.kakao_connect_preview import render_private_preview  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=ROOT / "60_OUTPUTS" / "prototype" / "KAKAO_CONNECT_PRIVATE_PREVIEW_2026-08-19.html",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT.resolve() not in output.parents:
        raise SystemExit("output must stay inside the project")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_private_preview(), encoding="utf-8", newline="\n")
    print(f"Kakao Connect private preview: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
