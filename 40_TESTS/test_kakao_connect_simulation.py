#!/usr/bin/env python3
"""Kakao Connect 1,000-person synthetic review contract tests."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_kakao_connect_simulation", ROOT / "70_TOOLS" / "run_kakao_connect_simulation.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KakaoConnectSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.personas = MODULE.build_personas()
        cls.result = MODULE.summarize(cls.personas)

    def test_exactly_one_thousand_unique_synthetic_personas(self):
        self.assertEqual(len(self.personas), 1_000)
        self.assertEqual(len({p["persona_id"] for p in self.personas}), 1_000)
        self.assertTrue(all(p["synthetic"] is True for p in self.personas))

    def test_generation_is_deterministic(self):
        self.assertEqual(self.personas, MODULE.build_personas())

    def test_no_actual_network_or_android_claim(self):
        self.assertEqual(self.result["evidence_grade"], "modeled_not_actual_users")
        self.assertFalse(self.result["network_test_performed"])
        self.assertFalse(self.result["android_test_performed"])

    def test_pricing_and_public_release_stay_closed(self):
        self.assertEqual(self.result["pricing_status"], "unresolved")
        self.assertFalse(self.result["public_release"])
        self.assertFalse(self.result["preview_action_enabled"])
        self.assertTrue(all(p["can_charge"] is False for p in self.personas))
        self.assertTrue(all(p["can_offer_publicly"] is False for p in self.personas))

    def test_all_unsupported_intents_are_blocked(self):
        metric = self.result["metrics"]["unsupported_intent_blocked"]
        self.assertGreater(metric["modeled_total"], 0)
        self.assertEqual(metric["modeled_count"], metric["modeled_total"])

    def test_personas_contain_no_real_identity_or_network_fields(self):
        forbidden = {"name", "email", "account", "ip", "address", "message", "private_key"}
        for persona in self.personas:
            self.assertFalse(forbidden & set(persona))

    def test_report_labels_modeled_and_actual_limits(self):
        report = MODULE.render_report(self.result)
        self.assertIn("[추정]", report)
        self.assertIn("실제 네트워크·Android 검사: 0건", report)
        self.assertIn("K5 실제 Android", report)

    def test_weak_modeled_comprehension_generates_improvements(self):
        weak = [
            key for key in (
                "understands_private_candidate",
                "understands_pricing_unresolved",
                "understands_existing_profile_preserved",
            )
            if self.result["metrics"][key]["modeled_percent"] < 90
        ]
        if weak:
            self.assertTrue(self.result["recommendations"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KakaoConnectSimulationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"Kakao Connect K4 simulation tests {passed}/{total} passed")
    raise SystemExit(0 if result.wasSuccessful() else 1)
