#!/usr/bin/env python3
"""안전한 JSON 스냅샷으로 G1-R 피어·재발급 경로를 읽기 전용 판정한다."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.profile_reissue import evaluate_profile_reissue  # noqa: E402


MAX_INPUT_BYTES = 32 * 1024


def _write_new(path: pathlib.Path, result: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(f"기존 증거 파일은 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path, help="민감정보 없는 readback JSON")
    parser.add_argument("--output", type=pathlib.Path, help="새 증거 JSON 경로. 생략하면 stdout만 사용")
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("입력 JSON 파일을 찾을 수 없습니다")
    if args.input.stat().st_size > MAX_INPUT_BYTES:
        parser.error("입력 JSON이 허용 크기를 초과했습니다")
    try:
        snapshot = json.loads(args.input.read_text(encoding="utf-8"))
        result = evaluate_profile_reissue(snapshot)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.output:
        try:
            _write_new(args.output.resolve(), result)
        except (OSError, FileExistsError) as exc:
            parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
