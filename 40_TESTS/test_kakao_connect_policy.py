#!/usr/bin/env python3
"""Kakao Connect K1-K3 fail-closed policy tests."""
from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.kakao_connect_policy import (  # noqa: E402
    CandidateEvidence,
    DEFAULT_TRANSPORT,
    PROVIDERS,
    REQUIRED_REUSE,
    evaluate_candidate,
    private_preview_model,
    validate_bindings,
    validate_telemetry,
)
from app.kakao_connect_preview import render_private_preview  # noqa: E402


FULL_MESSAGE = CandidateEvidence(
    legal_reviewed=True,
    server_verified=True,
    android_message_verified=True,
    android_voice_verified=True,
    disconnect_recovery_verified=True,
    existing_profile_preserved=True,
)


class KakaoConnectPolicyTests(unittest.TestCase):
    def test_default_is_existing_wireguard(self):
        self.assertEqual(DEFAULT_TRANSPORT, "wireguard")
        self.assertEqual(PROVIDERS["wireguard"].state, "default_existing")

    def test_research_transports_are_isolated_and_never_replace_wireguard(self):
        for name in ("vless_xtls_reality", "hysteria2"):
            provider = PROVIDERS[name]
            self.assertEqual(provider.state, "unverified_research_only")
            self.assertFalse(provider.replaces_wireguard)
            self.assertNotEqual(provider.config_namespace, PROVIDERS["wireguard"].config_namespace)
            self.assertNotEqual(provider.evidence_namespace, PROVIDERS["wireguard"].evidence_namespace)

    def test_missing_existing_bindings_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing existing FreeFlex bindings"):
            validate_bindings({})

    def test_existing_freeflex_bindings_are_required(self):
        validate_bindings({name: object() for name in REQUIRED_REUSE})

    def test_imported_billing_guard_is_forbidden(self):
        bindings = {name: object() for name in REQUIRED_REUSE}
        bindings["billing_guard"] = object()
        with self.assertRaisesRegex(ValueError, "forbidden Kakao package bindings"):
            validate_bindings(bindings)

    def test_sensitive_telemetry_is_rejected(self):
        for field in ("private_key", "raw_ip", "raw_destination", "message_content", "dns_query"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_telemetry({field: "do-not-store"})

    def test_planning_state_cannot_charge_or_publish(self):
        decision = evaluate_candidate(current_country="CN", purpose="text_message")
        self.assertFalse(decision.can_prepare_candidate)
        self.assertFalse(decision.can_offer_publicly)
        self.assertFalse(decision.can_charge)
        self.assertEqual(decision.pricing_status, "unresolved")

    def test_existing_profile_preservation_is_mandatory(self):
        decision = evaluate_candidate(
            current_country="CN", purpose="text_message",
            evidence=CandidateEvidence(server_verified=True, android_message_verified=True),
        )
        self.assertEqual(decision.reason, "existing_profile_preservation_required")
        self.assertFalse(decision.can_replace_existing_profile)

    def test_china_requires_legal_review(self):
        decision = evaluate_candidate(
            current_country="CN", purpose="text_message",
            evidence=CandidateEvidence(
                server_verified=True,
                android_message_verified=True,
                disconnect_recovery_verified=True,
                existing_profile_preserved=True,
            ),
        )
        self.assertEqual(decision.reason, "legal_review_required")

    def test_voice_requires_separate_android_evidence(self):
        evidence = CandidateEvidence(
            legal_reviewed=True,
            server_verified=True,
            android_message_verified=True,
            disconnect_recovery_verified=True,
            existing_profile_preserved=True,
        )
        decision = evaluate_candidate(current_country="CN", purpose="voice_call", evidence=evidence)
        self.assertEqual(decision.reason, "android_voice_evidence_required")

    def test_unverified_research_transport_is_blocked_even_with_full_evidence(self):
        for transport in ("vless_xtls_reality", "hysteria2"):
            with self.subTest(transport=transport):
                decision = evaluate_candidate(
                    current_country="CN", purpose="voice_call", transport=transport, evidence=FULL_MESSAGE,
                )
                self.assertEqual(decision.reason, "research_transport_unverified")

    def test_full_wireguard_evidence_only_opens_private_candidate(self):
        decision = evaluate_candidate(
            current_country="CN", purpose="voice_call", evidence=FULL_MESSAGE,
        )
        self.assertEqual(decision.status, "private_candidate")
        self.assertTrue(decision.can_prepare_candidate)
        self.assertFalse(decision.can_offer_publicly)
        self.assertFalse(decision.can_charge)
        self.assertFalse(decision.can_replace_existing_profile)

    def test_unsupported_heavy_uses_remain_blocked(self):
        for purpose in ("bulk_download", "p2p", "video_4k"):
            with self.subTest(purpose=purpose):
                self.assertEqual(
                    evaluate_candidate(current_country="CN", purpose=purpose, evidence=FULL_MESSAGE).reason,
                    "unsupported_purpose",
                )

    def test_private_preview_is_disabled_and_explicit(self):
        model = private_preview_model()
        self.assertFalse(model["primary_action"]["enabled"])
        self.assertEqual(model["badges"], ["비공개 후보", "가격 미결정", "기존 설정 보존"])
        page = render_private_preview()
        for phrase in ("검증 전 비공개 후보", "가격은 미결정", "기존 FreeFlexVPN", "가격 미결정", "기존 설정 보존", "disabled"):
            self.assertIn(phrase, page)
        self.assertNotIn("private_key", page)
        self.assertNotIn("raw_ip", page)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KakaoConnectPolicyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"Kakao Connect K1-K3 policy tests {passed}/{total} passed")
    raise SystemExit(0 if result.wasSuccessful() else 1)
