#!/usr/bin/env python3
"""Fail-closed policy and provider isolation for the private Kakao Connect candidate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


PROFILE_ID = "kakao_connect"
DEFAULT_TRANSPORT = "wireguard"
PRICING_STATUS = "unresolved"
SUPPORTED_PURPOSES = frozenset({"text_message", "photo_message", "voice_call"})
UNSUPPORTED_PURPOSES = frozenset({"bulk_download", "p2p", "video_4k"})
REQUIRED_REUSE = frozenset({
    "wallet_ledger",
    "quota_ledger",
    "quota_agent",
    "referral_ledger",
    "server_catalog",
    "profile_replacement_guard",
})
FORBIDDEN_BINDINGS = frozenset({"billing_guard", "xui_panel_billing"})
FORBIDDEN_TELEMETRY = frozenset({
    "private_key",
    "raw_ip",
    "raw_destination",
    "message_content",
    "dns_query",
})


@dataclass(frozen=True)
class ProviderPolicy:
    provider_id: str
    state: str
    config_namespace: str
    evidence_namespace: str
    replaces_wireguard: bool = False
    manual_activation_required: bool = True


PROVIDERS: Mapping[str, ProviderPolicy] = {
    "wireguard": ProviderPolicy(
        provider_id="wireguard",
        state="default_existing",
        config_namespace="freeflex/wireguard",
        evidence_namespace="freeflex/wireguard",
    ),
    "vless_xtls_reality": ProviderPolicy(
        provider_id="vless_xtls_reality",
        state="unverified_research_only",
        config_namespace="research/vless_xtls_reality",
        evidence_namespace="research/vless_xtls_reality",
    ),
    "hysteria2": ProviderPolicy(
        provider_id="hysteria2",
        state="unverified_research_only",
        config_namespace="research/hysteria2",
        evidence_namespace="research/hysteria2",
    ),
}


@dataclass(frozen=True)
class CandidateEvidence:
    legal_reviewed: bool = False
    server_verified: bool = False
    android_message_verified: bool = False
    android_voice_verified: bool = False
    disconnect_recovery_verified: bool = False
    existing_profile_preserved: bool = False
    bounded_pilot_verified: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    reason: str
    profile_id: str
    transport: str
    pricing_status: str
    can_prepare_candidate: bool
    can_offer_publicly: bool
    can_charge: bool
    can_replace_existing_profile: bool


def validate_bindings(bindings: Mapping[str, object]) -> None:
    """Require existing FreeFlex services and reject the weaker imported billing path."""
    names = set(bindings)
    missing = sorted(REQUIRED_REUSE - names)
    forbidden = sorted(FORBIDDEN_BINDINGS & names)
    if missing:
        raise ValueError(f"missing existing FreeFlex bindings: {', '.join(missing)}")
    if forbidden:
        raise ValueError(f"forbidden Kakao package bindings: {', '.join(forbidden)}")
    if any(bindings[name] is None for name in REQUIRED_REUSE):
        raise ValueError("existing FreeFlex bindings must be concrete")


def validate_telemetry(fields: Mapping[str, object]) -> None:
    """Reject content, private keys, raw addresses, and raw destinations at the boundary."""
    forbidden = sorted(FORBIDDEN_TELEMETRY & set(fields))
    if forbidden:
        raise ValueError(f"forbidden telemetry fields: {', '.join(forbidden)}")


def evaluate_candidate(
    *,
    current_country: str,
    purpose: str,
    transport: str = DEFAULT_TRANSPORT,
    evidence: CandidateEvidence | None = None,
) -> PolicyDecision:
    """Return an allowlisted decision without carrying user text or network identifiers."""
    country = (current_country or "").strip().upper()
    use = (purpose or "").strip().lower()
    proof = evidence or CandidateEvidence()

    if transport not in PROVIDERS:
        return _blocked("unknown_transport", transport)
    provider = PROVIDERS[transport]
    if use in UNSUPPORTED_PURPOSES or use not in SUPPORTED_PURPOSES:
        return _blocked("unsupported_purpose", transport)
    if provider.state == "unverified_research_only":
        return _blocked("research_transport_unverified", transport)
    if not proof.existing_profile_preserved:
        return _blocked("existing_profile_preservation_required", transport)
    if not proof.server_verified:
        return _blocked("server_readback_required", transport)
    if country == "CN" and not proof.legal_reviewed:
        return _blocked("legal_review_required", transport)
    if not proof.android_message_verified:
        return _blocked("android_message_evidence_required", transport)
    if use == "voice_call" and not proof.android_voice_verified:
        return _blocked("android_voice_evidence_required", transport)
    if not proof.disconnect_recovery_verified:
        return _blocked("disconnect_recovery_required", transport)

    return PolicyDecision(
        status="private_candidate",
        reason="bounded_pilot_required" if not proof.bounded_pilot_verified else "commercial_review_required",
        profile_id=PROFILE_ID,
        transport=transport,
        pricing_status=PRICING_STATUS,
        can_prepare_candidate=True,
        can_offer_publicly=False,
        can_charge=False,
        can_replace_existing_profile=False,
    )


def _blocked(reason: str, transport: str) -> PolicyDecision:
    return PolicyDecision(
        status="blocked",
        reason=reason,
        profile_id=PROFILE_ID,
        transport=transport,
        pricing_status=PRICING_STATUS,
        can_prepare_candidate=False,
        can_offer_publicly=False,
        can_charge=False,
        can_replace_existing_profile=False,
    )


def private_preview_model() -> dict[str, object]:
    """Return fixed copy for a local-only preview; it never contains user or provider data."""
    return {
        "profile_id": PROFILE_ID,
        "title": "Kakao Connect",
        "status": "검증 전 비공개 후보",
        "summary": "중국 체류 중 메시지·사진·통화 사용을 위한 추가 특화 프로필입니다.",
        "badges": ["비공개 후보", "가격 미결정", "기존 설정 보존"],
        "warnings": [
            "중국 실제망·카카오톡·LINE·통화는 아직 확인되지 않았습니다.",
            "가격은 미결정이며 결제나 공개 신청을 받지 않습니다.",
            "기존 FreeFlexVPN과 WireGuard 설정은 자동으로 바꾸거나 지우지 않습니다.",
        ],
        "supported": ["텍스트 메시지", "사진 메시지", "음성 통화 후보"],
        "unsupported": ["4K 영상", "대용량 다운로드", "P2P", "우회 성공 보장"],
        "primary_action": {"label": "가격 미결정 · 실제 검증 전 사용 불가", "enabled": False},
    }
