#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공개 Pages 파일의 SHA-256 원장을 생성하거나 대조한다."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PUBLIC_MANIFEST.json"


def records() -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path == OUTPUT or "__pycache__" in path.parts:
            continue
        raw = path.read_bytes()
        result[path.relative_to(ROOT).as_posix()] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    return result


def main() -> None:
    current = records()
    if "--check" in sys.argv:
        expected = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
        if current != expected:
            missing = sorted(set(expected) - set(current))
            extra = sorted(set(current) - set(expected))
            changed = sorted(key for key in set(current) & set(expected) if current[key] != expected[key])
            print(f"PUBLIC_MANIFEST FAIL — 없음 {len(missing)} · 추가 {len(extra)} · 변경 {len(changed)}")
            if missing:
                print("  없음:", ", ".join(missing))
            if extra:
                print("  추가:", ", ".join(extra))
            if changed:
                print("  변경:", ", ".join(changed))
            raise SystemExit(1)
        print(f"PUBLIC_MANIFEST PASS — 파일 {len(current)}개")
        return
    OUTPUT.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PUBLIC_MANIFEST 생성 — 파일 {len(current)}개")


if __name__ == "__main__":
    main()
