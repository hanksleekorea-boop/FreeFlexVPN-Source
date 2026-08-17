#!/usr/bin/env python3
"""G1-R 읽기 전용 피어·재발급 판정 계약과 음성 대조."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.profile_reissue import SCHEMA, evaluate_profile_reissue  # noqa: E402


def snapshot(**changes):
    value = {
        "schema": SCHEMA,
        "origin": "read_only",
        "device": {
            "scope": "live_readback",
            "legacy_profile_present": True,
            "legacy_profile_enabled": False,
            "candidate_profile_present": False,
            "candidate_profile_enabled": False,
            "always_on_enabled": False,
            "lockdown_enabled": False,
        },
        "server": {
            "readback_available": False,
            "peer_count": None,
            "legacy_peer_state": "unknown",
            "candidate_peer_state": "unknown",
            "forwarding_ok": None,
            "nat_ok": None,
            "firewall_ok": None,
        },
        "candidate_evidence": {
            "scope": "none",
            "human_switch_confirmed": False,
            "tunnel_ok": None,
            "exit_path_ok": None,
            "dns_ok": None,
            "handshake_ok": None,
            "return_path_ok": None,
        },
    }
    for key, nested in changes.items():
        value[key].update(nested)
    return value


def ready_server(**changes):
    value = {
        "readback_available": True,
        "peer_count": 1,
        "legacy_peer_state": "present",
        "candidate_peer_state": "absent",
        "forwarding_ok": True,
        "nat_ok": True,
        "firewall_ok": True,
    }
    value.update(changes)
    return value


class ProfileReissueTests(unittest.TestCase):
    def test_missing_live_readback_fails_closed_and_preserves_legacy(self):
        result = evaluate_profile_reissue(snapshot())
        self.assertEqual(result["status"], "readback_required")
        self.assertEqual(result["legacy_profile_action"], "preserve")
        self.assertFalse(result["mutation_performed"])
        self.assertIn("server_readback_required", result["blocking_reasons"])

    def test_historical_device_state_never_authorizes_a_mutation_review(self):
        result = evaluate_profile_reissue(
            snapshot(device={"scope": "historical_record"}, server=ready_server())
        )
        self.assertEqual(result["status"], "readback_required")
        self.assertFalse(result["ready_for_candidate_issue_review"])
        self.assertIn("live_device_readback_required", result["blocking_reasons"])

    def test_sensitive_peer_material_is_rejected_before_evaluation(self):
        value = snapshot()
        value["server"]["public_key"] = "not-allowed"
        with self.assertRaisesRegex(ValueError, "민감 필드"):
            evaluate_profile_reissue(value)

    def test_isolated_candidate_issue_requires_known_safe_server_and_device_policy(self):
        result = evaluate_profile_reissue(snapshot(server=ready_server()))
        self.assertEqual(result["status"], "candidate_issue_review_ready")
        self.assertTrue(result["ready_for_candidate_issue_review"])
        self.assertEqual(result["server_peer_action"], "none")

    def test_always_on_or_lockdown_blocks_candidate_issue_review(self):
        for field in ("always_on_enabled", "lockdown_enabled"):
            result = evaluate_profile_reissue(snapshot(device={field: True}, server=ready_server()))
            self.assertFalse(result["ready_for_candidate_issue_review"])
            self.assertIn(f"{field.removesuffix('_enabled')}_requires_human_review", result["blocking_reasons"])

    def test_device_server_candidate_mismatch_requires_investigation(self):
        result = evaluate_profile_reissue(
            snapshot(device={"candidate_profile_present": True}, server=ready_server())
        )
        self.assertEqual(result["status"], "mapping_investigation_required")
        self.assertFalse(result["ready_for_candidate_issue_review"])

    def test_historical_success_never_authorizes_legacy_retirement(self):
        result = evaluate_profile_reissue(
            snapshot(
                device={"candidate_profile_present": True},
                server=ready_server(peer_count=2, candidate_peer_state="present"),
                candidate_evidence={
                    "scope": "historical_separate_profile",
                    "tunnel_ok": True,
                    "exit_path_ok": True,
                    "dns_ok": True,
                    "handshake_ok": True,
                    "return_path_ok": True,
                },
            )
        )
        self.assertEqual(result["status"], "candidate_validation_required")
        self.assertFalse(result["ready_for_legacy_retirement_review"])
        self.assertIn("historical_candidate_evidence_not_current_proof", result["blocking_reasons"])

    def test_current_complete_human_evidence_only_opens_review(self):
        result = evaluate_profile_reissue(
            snapshot(
                device={"candidate_profile_present": True},
                server=ready_server(peer_count=2, candidate_peer_state="present"),
                candidate_evidence={
                    "scope": "current_candidate",
                    "human_switch_confirmed": True,
                    "tunnel_ok": True,
                    "exit_path_ok": True,
                    "dns_ok": True,
                    "handshake_ok": True,
                    "return_path_ok": True,
                },
            )
        )
        self.assertEqual(result["status"], "legacy_retirement_review_ready")
        self.assertTrue(result["ready_for_legacy_retirement_review"])
        self.assertEqual(result["legacy_profile_action"], "preserve")
        self.assertFalse(result["mutation_performed"])

    def test_candidate_must_be_off_after_return_path_before_retirement_review(self):
        result = evaluate_profile_reissue(
            snapshot(
                device={"candidate_profile_present": True, "candidate_profile_enabled": True},
                server=ready_server(peer_count=2, candidate_peer_state="present"),
                candidate_evidence={
                    "scope": "current_candidate",
                    "human_switch_confirmed": True,
                    "tunnel_ok": True,
                    "exit_path_ok": True,
                    "dns_ok": True,
                    "handshake_ok": True,
                    "return_path_ok": True,
                },
            )
        )
        self.assertEqual(result["status"], "candidate_validation_required")
        self.assertFalse(result["ready_for_legacy_retirement_review"])
        self.assertIn("candidate_profile_must_be_off_after_return_path", result["blocking_reasons"])

    def test_two_present_mappings_require_at_least_two_server_peers(self):
        with self.assertRaisesRegex(ValueError, "최소 2개"):
            evaluate_profile_reissue(
                snapshot(
                    device={"candidate_profile_present": True},
                    server=ready_server(peer_count=1, candidate_peer_state="present"),
                )
            )

    def test_any_failed_candidate_evidence_keeps_both_profiles(self):
        result = evaluate_profile_reissue(
            snapshot(
                device={"candidate_profile_present": True},
                server=ready_server(peer_count=2, candidate_peer_state="present"),
                candidate_evidence={"scope": "current_candidate", "dns_ok": False},
            )
        )
        self.assertEqual(result["status"], "candidate_failure_investigation")
        self.assertEqual(result["device_setting_action"], "none")

    def test_cli_writes_new_redacted_evidence_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_g1r_") as temp:
            root = pathlib.Path(temp)
            source = root / "input.json"
            target = root / "evidence.json"
            source.write_text(json.dumps(snapshot(), ensure_ascii=False), encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "70_TOOLS" / "compare_profile_reissue.py"),
                "--input", str(source),
                "--output", str(target),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            report = json.loads(target.read_text(encoding="utf-8"))
            self.assertFalse(report["evidence_boundary"]["contains_sensitive_data"])
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("덮어쓰지 않습니다", second.stderr)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProfileReissueTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"G1-R 피어·재발급 판정 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
