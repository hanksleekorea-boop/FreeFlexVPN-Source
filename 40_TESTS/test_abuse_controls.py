#!/usr/bin/env python3
"""FreeFlexVPN 남용 방지 기준선과 계정당 기기 제한 검사."""
from __future__ import annotations

import copy
import datetime as dt
import pathlib
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra import quota_agent as qa
from infra.cloud_init import EXAMPLE_ADMIN_CIDR, ExitNodeSpec, build_config

ACCOUNT_A = "a" * 64
ACCOUNT_B = "b" * 64
KEY_1 = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA="
KEY_2 = "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI="
KEY_3 = "AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM="
NOW = dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc)


def rendered_files():
    config = build_config(ExitNodeSpec(EXAMPLE_ADMIN_CIDR, example=True))
    return {item["path"]: item["content"] for item in config["write_files"]}


class AbuseControlTests(unittest.TestCase):
    def test_smtp_25_is_blocked_only_for_forwarded_vpn_clients(self):
        nft = rendered_files()["/etc/nftables.conf"]
        rule = 'iifname "wg0" tcp dport 25 counter reject with tcp reset'
        self.assertIn(rule, nft)
        self.assertLess(nft.index(rule), nft.index('iifname "wg0" oifname != "wg0" accept'))
        self.assertNotIn("chain output {\n    type filter hook output priority filter; policy drop", nft)

    def test_p2p_rule_is_explicitly_heuristic_not_complete(self):
        nft = rendered_files()["/etc/nftables.conf"]
        self.assertIn("P2P 휴리스틱 기준선", nft)
        self.assertIn("완전 차단을 주장하지 않는다", nft)
        self.assertIn('tcp dport { 6881-6999, 51413 }', nft)
        self.assertIn('udp dport { 6881-6999, 51413 }', nft)

    def test_fail2ban_has_bounded_ssh_policy(self):
        jail = rendered_files()["/etc/fail2ban/jail.d/freeflexvpn-sshd.local"]
        for marker in ("enabled = true", "backend = systemd", "maxretry = 5", "findtime = 10m", "bantime = 1h", "usedns = no"):
            self.assertIn(marker, jail)

    def test_health_probe_includes_fail2ban(self):
        health = rendered_files()["/usr/local/sbin/freeflexvpn-health"]
        self.assertIn("probe fail2ban systemctl is-active --quiet fail2ban", health)

    def test_account_id_requires_hmac_shaped_pseudonym(self):
        for value in ("", "raw-user-id", "A" * 64, "a" * 63):
            with self.assertRaises(ValueError):
                qa.validate_account_id(value)
        self.assertEqual(qa.validate_account_id(ACCOUNT_A), ACCOUNT_A)

    def test_two_active_peer_limit_and_third_is_fail_closed(self):
        state = qa.empty_state()
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        qa.enroll(state, ACCOUNT_A, KEY_2, "10.66.0.3/32", {}, NOW)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError, "2대 제한"):
            qa.enroll(state, ACCOUNT_A, KEY_3, "10.66.0.4/32", {}, NOW)
        self.assertEqual(state, before)

    def test_reenrolling_same_peer_is_idempotent_for_device_count(self):
        state = qa.empty_state()
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        self.assertEqual(sum(1 for p in state["peers"].values() if p["enrolled"]), 1)

    def test_revocation_frees_one_device_slot(self):
        state = qa.empty_state()
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        qa.enroll(state, ACCOUNT_A, KEY_2, "10.66.0.3/32", {}, NOW)
        qa.revoke(state, KEY_1)
        qa.enroll(state, ACCOUNT_A, KEY_3, "10.66.0.4/32", {}, NOW)
        active = [p for p in state["peers"].values() if p["enrolled"] and p["account_id"] == ACCOUNT_A]
        self.assertEqual(len(active), 2)

    def test_peer_key_cannot_move_between_accounts(self):
        state = qa.empty_state()
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        with self.assertRaisesRegex(ValueError, "다른 가명 계정"):
            qa.enroll(state, ACCOUNT_B, KEY_1, "10.66.0.2/32", {}, NOW)

    def test_allowed_ip_cannot_be_shared_by_active_peers(self):
        state = qa.empty_state()
        qa.enroll(state, ACCOUNT_A, KEY_1, "10.66.0.2/32", {}, NOW)
        with self.assertRaisesRegex(ValueError, "Allowed IP"):
            qa.enroll(state, ACCOUNT_B, KEY_2, "10.66.0.2/32", {}, NOW)

    def test_unknown_runtime_peer_has_no_account_and_is_blocked(self):
        state = qa.empty_state()
        observed = {KEY_1: {"allowed_ip": "10.66.0.2", "total_bytes": 0}}
        qa.poll_state(state, observed, NOW)
        self.assertIsNone(state["peers"][KEY_1]["account_id"])
        self.assertTrue(state["peers"][KEY_1]["blocked"])

    def test_enrolled_peer_without_account_is_invalid_state(self):
        state = qa.empty_state()
        peer = qa.new_peer("10.66.0.2", enrolled=False, now=NOW)
        peer["enrolled"] = True
        state["peers"][KEY_1] = peer
        with self.assertRaises(ValueError):
            qa._validate_state(state)

    def test_policy_constant_is_exactly_two(self):
        self.assertEqual(qa.MAX_ACTIVE_PEERS_PER_ACCOUNT, 2)

    def test_schema_is_bumped_for_account_binding(self):
        self.assertEqual(qa.SCHEMA_VERSION, 2)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AbuseControlTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"남용 방지 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
