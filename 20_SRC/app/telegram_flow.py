#!/usr/bin/env python3
"""Telegram 업데이트를 네트워크와 분리해 가입 흐름 명령으로 변환한다."""
from __future__ import annotations

from typing import Any

from .telegram_onboarding import OnboardingError, OnboardingLedger


def _sender(update: dict[str, Any]) -> tuple[int, str, str | None]:
    if "message" in update:
        message = update["message"]
        return int(message["from"]["id"]), str(message.get("text", "")).split("@", 1)[0], None
    if "callback_query" in update:
        query = update["callback_query"]
        return int(query["from"]["id"]), "", str(query.get("data", ""))
    raise ValueError("지원하지 않는 Telegram update입니다")


def handle_update(
    update: dict[str, Any],
    ledger: OnboardingLedger,
    *,
    policy_version: str,
    claim_base_url: str,
) -> dict[str, Any]:
    user_id, text, callback = _sender(update)
    try:
        if text == "/start":
            return {
                "text": "FreeFlexVPN은 월 1GB가 무료이고 충전분은 만료되지 않습니다. 가입에는 정책 동의가 필요합니다.",
                "buttons": [
                    {"text": "동의하고 시작", "callback_data": "consent:accept"},
                    {"text": "동의하지 않음", "callback_data": "consent:decline"},
                ],
                "loggable": True,
            }
        if callback == "consent:accept":
            ledger.accept(user_id, policy_version)
            return {"text": "동의가 저장되었습니다. /claim으로 일회용 수령 주소를 만드세요.", "loggable": True}
        if callback == "consent:decline":
            result = ledger.decline(user_id)
            return {"text": "동의하지 않음이 반영되었습니다.", "status": result["status"], "loggable": True}
        if text == "/claim":
            result = ledger.issue_claim(user_id, claim_base_url)
            return {
                "text": "아래 주소는 10분간 한 번만 사용할 수 있습니다.",
                "claim_url": result["claim_url"],
                "expires_at": result["expires_at"],
                "loggable": False,
            }
        if text == "/status":
            return {"text": "현재 상태를 확인했습니다.", "account": ledger.status(user_id), "loggable": True}
        if text == "/revoke":
            result = ledger.request_revoke(user_id)
            return {"text": "피어 폐기를 요청했습니다.", "revoke": result, "loggable": True}
        return {"text": "사용 가능한 명령: /start /claim /status /revoke", "loggable": True}
    except OnboardingError as exc:
        return {"text": str(exc), "status": "blocked", "loggable": True}

