#!/usr/bin/env python3
"""FreeFlexVPN Telegram 봇의 비밀 없는 설정 후보를 만든다."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.telegram_bot_config import build_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-base-url")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--example", action="store_true")
    args = parser.parse_args()
    if args.example:
        url = "https://example.invalid/claim"
    elif args.claim_base_url:
        url = args.claim_base_url
    else:
        parser.error("실사용 후보는 --claim-base-url이 필요합니다")
    config = build_config(claim_base_url=url, example=args.example)
    output = args.output or ROOT / "60_OUTPUTS" / "infra" / ("FreeFlexVPN_telegram_bot_config_v1_EXAMPLE.json" if args.example else "FreeFlexVPN_telegram_bot_config_v1.json")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    print(f"Telegram 설정 생성 PASS — {output}")
    print(f"SHA-256 {digest}")
    print("실제 토큰·HMAC 키·webhook secret 포함 0")
    if args.example:
        print("상태 ADAPTER_OR_DEMO — 공개 claim endpoint와 BotFather 토큰이 없어 실행 금지")


if __name__ == "__main__":
    main()

