#!/usr/bin/env python3
"""Build the self-contained FreeFlexVPN GCP billing review helper."""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.gcp_cost_review import (  # noqa: E402
    DESTINATION_RATES_USD_PER_GIB,
    FREE_TIER_EGRESS_EXCLUDED,
    GCPPriceSnapshot,
)


def _data_url(path: pathlib.Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def build_html() -> bytes:
    template = (ROOT / "20_SRC" / "html_templates" / "gcp_billing_review_v2_13.html").read_text(encoding="utf-8")
    icon192 = ROOT / "20_SRC" / "github_pages" / "icon-192.png"
    icon512 = ROOT / "20_SRC" / "github_pages" / "icon-512.png"
    for required in (icon192, icon512):
        if not required.is_file():
            raise FileNotFoundError(f"required icon missing: {required}")
    manifest = {
        "id": "/FreeFlexVPN/gcp-billing-review-v2.13",
        "name": "FreeFlexVPN GCP 비용 확인 도우미",
        "short_name": "GCP 비용 확인",
        "description": "GCP 첫 VPN 노드의 비용 하한과 생성 전 확인 항목을 기록합니다.",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#f3f8f6",
        "theme_color": "#0b5f53",
        "icons": [
            {"src": _data_url(icon192), "sizes": "192x192", "type": "image/png"},
            {"src": _data_url(icon512), "sizes": "512x512", "type": "image/png"},
        ],
    }
    manifest_b64 = base64.b64encode(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")
    prices = GCPPriceSnapshot()
    price_data = {
        "snapshot_date": prices.as_of,
        "external_ipv4_usd_per_hour": prices.external_ipv4_usd_per_hour,
        "free_tier_egress_gib": prices.free_tier_egress_gib,
        "free_egress_excluded": list(FREE_TIER_EGRESS_EXCLUDED),
        "rates": DESTINATION_RATES_USD_PER_GIB,
    }
    rendered = template.replace("__MANIFEST_B64__", manifest_b64)
    rendered = rendered.replace("__PRICE_DATA__", json.dumps(price_data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"))
    rendered = rendered.replace("__PRICE_DATE__", prices.as_of)
    if "__MANIFEST_B64__" in rendered or "__PRICE_DATA__" in rendered or "__PRICE_DATE__" in rendered:
        raise ValueError("unresolved template placeholder")
    return rendered.encode("utf-8")


def write_new(path: pathlib.Path, data: bytes) -> None:
    path = path.resolve()
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_bytes(data)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = build_html()
        write_new(args.output, data)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"GCP 비용 확인 도우미 빌드 PASS — {args.output} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
