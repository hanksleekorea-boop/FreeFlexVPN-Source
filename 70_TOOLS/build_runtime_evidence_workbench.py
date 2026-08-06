#!/usr/bin/env python3
"""v2.17 T1~T10 로컬 증거 번들 작성기를 재현 가능하게 빌드한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "20_SRC" / "html_templates" / "runtime_evidence_workbench_v2_17.html"
DEFAULT_OUTPUT = ROOT / "60_OUTPUTS" / "FreeFlexVPN_runtime_evidence_workbench_v2.17_2026-08-03.html"
TOKEN = "__SOURCE_SHA256__"


def build_html() -> bytes:
    source = SOURCE.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    text = source.decode("utf-8")
    if text.count(TOKEN) != 1:
        raise ValueError("source SHA-256 토큰은 정확히 1개여야 합니다")
    rendered = text.replace(TOKEN, source_hash)
    required = (
        "FreeFlexVPNRuntimeEvidenceBundleV2", "crypto.subtle.digest", "LOCAL ONLY",
        "contains_secret:false", "T1~T10", "실제 서버·실기기·독립 사용자",
    )
    missing = [item for item in required if item not in rendered]
    if missing:
        raise ValueError(f"워크벤치 필수 계약 누락: {missing}")
    return rendered.encode("utf-8")


def write_new(path: pathlib.Path, content: bytes) -> None:
    path = path.resolve()
    if path.exists():
        raise FileExistsError(f"기존 후보를 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    content = build_html()
    write_new(args.output, content)
    print(json.dumps({
        "version": "v2.17", "output": str(args.output.resolve()), "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(), "network_requests": 0,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
