#!/usr/bin/env python3
"""보호 상태 5단계와 거짓 양성 방지 검사."""
from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.connection_check import evaluate_connection  # noqa: E402


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)


def evidence(**changes):
    values = {
        "profile_present": True,
        "tunnel_started": True,
        "observed_exit_ip": "8.8.8.8",
        "expected_exit_ip": "8.8.8.8",
        "server_health": "healthy",
        "handshake_at": NOW - timedelta(seconds=30),
        "dns_protected": True,
        "ipv6_protected": True,
        "kill_switch_protected": True,
        "checked_at": NOW,
    }
    values.update(changes)
    return evaluate_connection(**values)


class ConnectionCheckTests(unittest.TestCase):
    def test_all_real_evidence_is_required_for_protected(self):
        result = evidence()
        self.assertEqual(result["state"], "protected")
        self.assertTrue(result["protected"])
        self.assertEqual(result["reasons"], [])

    def test_five_product_states_are_reachable(self):
        self.assertEqual(evidence(profile_present=False)["state"], "setup_needed")
        self.assertEqual(evidence(tunnel_started=False)["state"], "disconnected")
        self.assertEqual(evidence(observed_exit_ip=None, handshake_at=None)["state"], "checking")
        self.assertEqual(evidence(dns_protected=None)["state"], "limited")
        self.assertEqual(evidence()["state"], "protected")

    def test_button_or_tunnel_claim_alone_never_protects_negative_control(self):
        result = evidence(
            observed_exit_ip=None,
            expected_exit_ip=None,
            handshake_at=None,
            dns_protected=None,
            ipv6_protected=None,
            kill_switch_protected=None,
        )
        self.assertFalse(result["protected"])
        self.assertEqual(result["state"], "checking")

    def test_wrong_exit_ip_is_limited(self):
        result = evidence(observed_exit_ip="1.1.1.1")
        self.assertEqual(result["state"], "limited")
        self.assertIn("exit_ip_not_verified", result["reasons"])

    def test_stale_missing_or_future_handshake_is_limited(self):
        for value in (
            None,
            NOW - timedelta(seconds=181),
            NOW + timedelta(seconds=31),
            "invalid",
        ):
            with self.subTest(value=value):
                result = evidence(handshake_at=value)
                self.assertFalse(result["protected"])
                self.assertIn("handshake_missing_or_stale", result["reasons"])

    def test_dns_ipv6_and_kill_switch_each_fail_closed(self):
        for field in ("dns_protected", "ipv6_protected", "kill_switch_protected"):
            for value in (False, None):
                with self.subTest(field=field, value=value):
                    result = evidence(**{field: value})
                    self.assertEqual(result["state"], "limited")
                    self.assertFalse(result["protected"])

    def test_unavailable_server_is_not_protected(self):
        for health in (None, "maintenance", "unavailable", "invented"):
            with self.subTest(health=health):
                result = evidence(server_health=health)
                self.assertIn("server_not_available", result["reasons"])
                self.assertFalse(result["protected"])

    def test_invalid_observed_ip_is_redacted(self):
        result = evidence(observed_exit_ip="not-an-ip")
        self.assertIsNone(result["observed_exit_ip"])
        self.assertFalse(result["protected"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConnectionCheckTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"보호 상태 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
