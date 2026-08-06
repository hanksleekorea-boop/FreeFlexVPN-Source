#!/usr/bin/env python3
"""T1~T10 실환경 관문의 실패 폐쇄·증거 분리 계약 검사."""
from __future__ import annotations

import pathlib
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.runtime_acceptance import TEST_IDS, evaluate_runtime_acceptance  # noqa: E402


NOW = datetime(2026, 8, 3, tzinfo=timezone.utc)
CANDIDATE = "R6-candidate-20260803-01"


def full_evidence(origin="actual_target"):
    os_runs = [
        {"run_id": f"run-{name}", "candidate_id": CANDIDATE,
         "os_family": name, "config_source": "official_wireguard", "tunnel_started": True,
         "handshake_age_seconds": 30, "sustained_seconds": 120}
        for name in ("ios", "android", "windows")
    ]
    participants = [
        {"participant_ref": f"pilot-{index}", "candidate_id": CANDIDATE, "consented": True,
         "independent": True, "actual_protected": True, "active_weeks": 4,
         "completed_without_help": index != 5}
        for index in range(1, 6)
    ]
    return {
        "candidate_id": CANDIDATE,
        "run_at": NOW,
        "origin": origin,
        "tests": {
            "T1": {"os_runs": os_runs},
            "T2": {"baseline_ip": "1.1.1.1", "observed_exit_ip": "8.8.8.8",
                   "expected_exit_ip": "8.8.8.8", "observed_country": "JP", "expected_country": "JP"},
            "T3": {"baseline_resolvers": ["1.1.1.1"], "tunnel_resolvers": ["8.8.8.8"],
                   "unexpected_resolvers": [], "queries_tested": 10},
            "T4": {"download_mbps_runs": [31, 45, 60], "measurement_ids": ["speed-1", "speed-2", "speed-3"],
                   "packet_loss_percent": 0.2},
            "T5": {"limit_bytes": 1_000_000_000, "usage_bytes": 1_000_000_001,
                   "blocked_after_seconds": 60, "traffic_blocked": True, "user_notice": True},
            "T6": {"free_bytes_after": 1_000_000_000, "paid_bytes_before": 3000,
                   "paid_bytes_after": 3000, "traffic_active": True, "reactivated_after_seconds": 60},
            "T7": {"active_key_count": 2, "third_key_rejected": True, "duplicate_key_rejected": True},
            "T8": {"tcp_25_blocked": True, "tcp_6881_6999_blocked": True,
                   "udp_6881_6999_blocked": True, "tcp_51413_blocked": True, "udp_51413_blocked": True},
            "T9": {"node_stopped": True, "alert_received": True, "channel": "telegram",
                   "alert_after_seconds": 180, "contains_secret": False},
            "T10": {"participants": participants, "observation_days": 28},
        },
    }


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_complete_actual_target_contract_passes(self):
        result = evaluate_runtime_acceptance(full_evidence())
        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "unverified_artifacts")
        self.assertEqual(result["passed_tests"], list(TEST_IDS))

    def test_synthetic_values_never_become_target_evidence(self):
        result = evaluate_runtime_acceptance(full_evidence(origin="synthetic"))
        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "adapter_or_demo")

    def test_each_missing_test_blocks_release(self):
        for test_id in TEST_IDS:
            value = full_evidence()
            del value["tests"][test_id]
            with self.subTest(test_id=test_id):
                result = evaluate_runtime_acceptance(value)
                self.assertIn(test_id, result["blocked_tests"])

    def test_t1_requires_all_three_os_and_real_wireguard(self):
        value = full_evidence()
        value["tests"]["T1"]["os_runs"][-1]["config_source"] = "mock"
        self.assertIn("T1", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_t2_rejects_unchanged_or_private_exit_ip(self):
        for observed in ("1.1.1.1", "10.0.0.1"):
            value = full_evidence()
            value["tests"]["T2"]["observed_exit_ip"] = observed
            with self.subTest(observed=observed):
                self.assertIn("T2", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_t3_rejects_baseline_or_unexpected_dns(self):
        value = full_evidence()
        value["tests"]["T3"]["tunnel_resolvers"] = ["1.1.1.1"]
        value["tests"]["T3"]["unexpected_resolvers"] = ["9.9.9.9"]
        result = evaluate_runtime_acceptance(value)
        self.assertIn("T3", result["blocked_tests"])

    def test_t4_uses_three_run_median_and_loss_guard(self):
        value = full_evidence()
        value["tests"]["T4"] = {"download_mbps_runs": [100, 10, 10],
                                  "measurement_ids": ["speed-1", "speed-2", "speed-3"],
                                  "packet_loss_percent": 1.1}
        result = evaluate_runtime_acceptance(value)
        self.assertIn("T4", result["blocked_tests"])

    def test_t5_and_t6_enforce_one_poll_cycle_and_paid_balance(self):
        value = full_evidence()
        value["tests"]["T5"]["blocked_after_seconds"] = 61
        value["tests"]["T6"]["paid_bytes_after"] = 0
        result = evaluate_runtime_acceptance(value)
        self.assertTrue({"T5", "T6"}.issubset(result["blocked_tests"]))

    def test_t7_rejects_third_or_duplicate_key(self):
        value = full_evidence()
        value["tests"]["T7"]["duplicate_key_rejected"] = False
        self.assertIn("T7", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_t8_requires_every_documented_port_family(self):
        value = full_evidence()
        value["tests"]["T8"]["udp_51413_blocked"] = False
        self.assertIn("T8", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_t9_requires_fast_secret_free_telegram_alert(self):
        value = full_evidence()
        value["tests"]["T9"]["contains_secret"] = True
        self.assertIn("T9", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_t10_requires_five_eligible_and_four_unassisted(self):
        value = full_evidence()
        participants = deepcopy(value["tests"]["T10"]["participants"])
        participants[0]["consented"] = False
        participants[1]["completed_without_help"] = False
        value["tests"]["T10"]["participants"] = participants
        self.assertIn("T10", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_duplicate_sessions_measurements_and_participants_are_rejected(self):
        value = full_evidence()
        value["tests"]["T1"]["os_runs"][1]["run_id"] = "run-ios"
        value["tests"]["T4"]["measurement_ids"][1] = "speed-1"
        value["tests"]["T10"]["participants"][1]["participant_ref"] = "pilot-1"
        result = evaluate_runtime_acceptance(value)
        self.assertTrue({"T1", "T4", "T10"}.issubset(result["blocked_tests"]))

    def test_t10_requires_four_week_observation(self):
        value = full_evidence()
        value["tests"]["T10"]["observation_days"] = 27
        self.assertIn("T10", evaluate_runtime_acceptance(value)["blocked_tests"])

    def test_unknown_test_and_naive_time_are_rejected(self):
        value = full_evidence()
        value["tests"]["T11"] = {}
        with self.assertRaises(ValueError):
            evaluate_runtime_acceptance(value)
        value = full_evidence()
        value["run_at"] = datetime(2026, 8, 3)
        with self.assertRaises(ValueError):
            evaluate_runtime_acceptance(value)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeAcceptanceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"T1~T10 실환경 관문 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
