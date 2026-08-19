#!/usr/bin/env python3
"""카카오 특화 설계가 FreeFlexVPN의 기존 계약을 낮추지 않는지 검사한다."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "10_PLAN" / "KAKAOVPN_INTEGRATION_PLAN_v1_2026-08-19.md"
CONTRACT = ROOT / "10_PLAN" / "KAKAOVPN_NON_REGRESSION_CONTRACT_v1.json"
COST = ROOT / "20_SRC" / "cost_model.py"
MOMENTS = ROOT / "20_SRC" / "app" / "moment_catalog.js"
VERIFY_APP = ROOT / "20_SRC" / "github_pages" / "tools" / "verify_app.py"
REFERRAL_TEST = ROOT / "40_TESTS" / "test_referral_ledger.py"


class KakaoVpnIntegrationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = PLAN.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_additive_planning_only_contract(self) -> None:
        self.assertEqual(self.contract["schema"], "FreeFlexKakaoIntegrationContractV1")
        self.assertEqual(self.contract["status"], "planning_only")
        self.assertEqual(self.contract["integration_mode"], "additive_specialized_profile")
        self.assertFalse(self.contract["public_release"])
        self.assertEqual(self.contract["pricing_status"], "unresolved")

    def test_existing_product_floor_is_preserved(self) -> None:
        preserve = self.contract["preserve"]
        self.assertEqual(preserve["monthly_free_gb"], 1)
        self.assertFalse(preserve["topup_expires"])
        self.assertFalse(preserve["automatic_payment"])
        self.assertEqual(preserve["default_transport"], "wireguard")
        self.assertFalse(preserve["existing_profile_mutation"])
        self.assertTrue(preserve["existing_public_urls"])
        self.assertTrue(preserve["existing_service_qr"])
        self.assertEqual(self.contract["score_floors"], {
            "development_percent": 75,
            "mobile_percent": 58,
            "pc_percent": 60,
        })

    def test_live_freeflex_contract_matches_floor(self) -> None:
        cost = COST.read_text(encoding="utf-8")
        app = VERIFY_APP.read_text(encoding="utf-8")
        self.assertIn("CAP_GB_FREE   = 1.0", cost)
        self.assertIn("TOPUP_EXPIRES = False", cost)
        self.assertIn("무료 1GB로 시작", app)
        self.assertIn("data-gb=\"100\"' not in app", app)
        self.assertIn("data-gb=\"300\"' not in app", app)

    def test_referral_security_and_reward_are_reused(self) -> None:
        preserve = self.contract["preserve"]
        self.assertEqual(preserve["referral_reward_mb_each"], 500)
        self.assertEqual(preserve["referral_qualification_mb"], 100)
        self.assertEqual(preserve["referral_monthly_cap"], 5)
        referral_test = REFERRAL_TEST.read_text(encoding="utf-8")
        for token in (
            "test_self_referral_and_existing_account_are_rejected",
            "test_circular_attribution_is_rejected",
            "test_duplicate_usage_event_never_pays_twice",
            "test_monthly_five_reward_cap_holds_sixth",
        ):
            self.assertIn(token, referral_test)
        self.assertIn("referral_ledger", self.contract["reuse"])

    def test_unverified_transports_cannot_replace_wireguard(self) -> None:
        transports = {item["id"]: item for item in self.contract["research_transports"]}
        self.assertEqual(set(transports), {"vless_xtls_reality", "hysteria2"})
        for item in transports.values():
            self.assertEqual(item["state"], "unverified_research_only")
            self.assertFalse(item["replaces_wireguard"])
        self.assertIn("두 연구 후보는 WireGuard를 대체하지 않는다", self.plan)

    def test_pricing_conflict_is_not_silently_resolved(self) -> None:
        self.assertEqual(len(self.contract["kakao_pricing_candidates"]), 3)
        for token in ("1.5GB 1,500원", "1.5GB 1,800원", "500원/GB"):
            self.assertIn(token, self.plan)
        self.assertIn("기존 가격 유지", self.plan)

    def test_china_remains_restricted_until_evidence(self) -> None:
        moments = MOMENTS.read_text(encoding="utf-8")
        self.assertIn('CN: Object.freeze({ code: "CN"', moments)
        self.assertIn('policy: "specialized_required"', moments)
        gates = set(self.contract["promotion_gates"])
        self.assertTrue({
            "legal_review",
            "android_kakao_message_test",
            "android_line_message_test",
            "android_voice_call_test",
            "disconnect_recovery_test",
            "existing_profile_preservation",
        }.issubset(gates))

    def test_privacy_and_drive_b_exclusion_are_strict(self) -> None:
        preserve = self.contract["preserve"]
        self.assertFalse(preserve["raw_ip_storage"])
        self.assertFalse(preserve["private_key_storage"])
        self.assertFalse(preserve["raw_destination_log_storage"])
        self.assertFalse(self.contract["drive_b_allowed"])
        self.assertIn("Drive B", self.plan)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KakaoVpnIntegrationPlanTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"카카오VPN 비하향 통합 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
