#!/usr/bin/env python3
"""서버가 확정한 WireGuard 주소로 저장소 밖 피어 묶음을 안전하게 보정한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.peer_bundle import PROJECT_ROOT, _qr_png


def outside_project(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return resolved
    raise ValueError("개인키 묶음은 프로젝트·Git 저장소 내부에서 보정할 수 없습니다")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=pathlib.Path, required=True)
    parser.add_argument("--expected-old", required=True)
    parser.add_argument("--assigned-address", required=True)
    args = parser.parse_args()

    bundle = outside_project(args.bundle_dir)
    configs = list(bundle.glob("FreeFlexVPN-*.conf"))
    qrs = list(bundle.glob("FreeFlexVPN-*-QR.png"))
    if len(configs) != 1 or len(qrs) != 1:
        raise ValueError("피어 구성과 QR은 각각 정확히 한 개여야 합니다")

    config_path, qr_path = configs[0], qrs[0]
    old_line = f"Address = {args.expected_old}"
    new_line = f"Address = {args.assigned_address}"
    config = config_path.read_text(encoding="utf-8")
    if config.count(old_line) != 1:
        raise ValueError("예상한 기존 주소를 구성에서 정확히 한 번 찾지 못했습니다")
    corrected = config.replace(old_line, new_line, 1)
    qr = _qr_png(corrected)

    enrollment_path = bundle / "enrollment.json"
    enrollment = json.loads(enrollment_path.read_text(encoding="utf-8"))
    if enrollment.get("allowed_ip") != args.expected_old:
        raise ValueError("등록 설명 파일의 기존 주소가 예상과 다릅니다")
    enrollment["allowed_ip"] = args.assigned_address

    config_path.write_text(corrected, encoding="utf-8", newline="\n")
    qr_path.write_bytes(qr)
    enrollment_path.write_text(
        json.dumps(enrollment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for path in (config_path, qr_path, enrollment_path):
        os.chmod(path, 0o600)

    manifest_path = bundle / "BUNDLE_MANIFEST.json"
    payload_paths = [path for path in bundle.iterdir() if path.name != manifest_path.name]
    manifest = {
        path.name: {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        }
        for path in sorted(payload_paths)
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.chmod(manifest_path, 0o600)

    print(json.dumps({
        "status": "PASS",
        "peer_name": enrollment.get("peer_name"),
        "assigned_address": args.assigned_address,
        "qr_payload_match": True,
        "private_material_printed": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
