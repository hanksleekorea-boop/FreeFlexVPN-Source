#!/usr/bin/env python3
"""비밀값 없는 Telegram 봇 설정 후보를 생성·검증한다."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def build_config(*, claim_base_url: str, example: bool = False) -> dict[str, Any]:
    parsed = urlparse(claim_base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("claim_base_url은 query·fragment 없는 HTTPS URL이어야 합니다")
    if parsed.hostname == "example.invalid" and not example:
        raise ValueError("문서용 주소는 example 모드에서만 허용합니다")
    return {
        "schema_version": 1,
        "product": "FreeFlexVPN",
        "status": "ADAPTER_OR_DEMO" if example else "PLANNED",
        "enabled": False,
        "policy_version": "privacy-terms-draft-v1",
        "claim": {
            "base_url": claim_base_url.rstrip("/"),
            "ttl_seconds": 600,
            "one_time": True,
            "private_key_delivery": "forbidden_in_telegram",
        },
        "environment": {
            "bot_token": "FREEFLEX_TELEGRAM_BOT_TOKEN",
            "identity_hmac_key": "FREEFLEX_TELEGRAM_IDENTITY_HMAC_KEY",
            "webhook_secret": "FREEFLEX_TELEGRAM_WEBHOOK_SECRET",
        },
        "privacy": {
            "stored": ["hmac_user_ref", "consent_version", "claim_sha256", "peer_public_key", "allowed_ip"],
            "not_stored": ["telegram_user_id", "username", "phone", "message_text", "claim_token", "client_private_key"],
        },
        "commands": ["start", "claim", "status", "revoke"],
    }

