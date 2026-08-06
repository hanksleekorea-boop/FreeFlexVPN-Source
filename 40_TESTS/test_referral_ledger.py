#!/usr/bin/env python3
"""FreeFlexVPN 추천 귀속·자격·양쪽 보상 원장 검사."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.referral_ledger import (  # noqa: E402
    MONTHLY_REWARD_CAP,
    QUALIFY_BYTES,
    REWARD_BYTES,
    ReferralLedger,
    ReferralRejected,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


class ReferralLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_referral_")
        self.path = pathlib.Path(self.temp.name) / "control.sqlite3"
        self.ledger = ReferralLedger(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def attribute(self, inviter: str = "inviter", invitee: str = "invitee") -> str:
        token = self.ledger.issue_token(inviter, now=NOW)["token"]
        return self.ledger.attribute(token, invitee, is_new_account=True, now=NOW)["referral_id"]

    def test_token_is_256_bit_random_and_only_hash_is_stored(self):
        first = self.ledger.issue_token("inviter", now=NOW)["token"]
        second = self.ledger.issue_token("inviter", now=NOW)["token"]
        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 40)
        self.assertNotIn(first.encode(), self.path.read_bytes())
        with closing(sqlite3.connect(self.path)) as connection:
            stored = connection.execute("SELECT token_hash FROM referral_tokens").fetchall()
        self.assertEqual(len(stored), 2)
        self.assertTrue(all(len(row[0]) == 64 for row in stored))

    def test_self_referral_and_existing_account_are_rejected(self):
        token = self.ledger.issue_token("same", now=NOW)["token"]
        with self.assertRaises(ReferralRejected):
            self.ledger.attribute(token, "same", is_new_account=True, now=NOW)
        token2 = self.ledger.issue_token("inviter", now=NOW)["token"]
        with self.assertRaises(ReferralRejected):
            self.ledger.attribute(token2, "existing", is_new_account=False, now=NOW)

    def test_invitee_can_be_attributed_only_once(self):
        self.attribute("a", "new-user")
        second = self.ledger.issue_token("b", now=NOW)["token"]
        with self.assertRaises(ReferralRejected):
            self.ledger.attribute(second, "new-user", is_new_account=True, now=NOW)

    def test_circular_attribution_is_rejected(self):
        self.attribute("alice", "bob")
        reverse = self.ledger.issue_token("bob", now=NOW)["token"]
        with self.assertRaises(ReferralRejected):
            self.ledger.attribute(reverse, "alice", is_new_account=True, now=NOW)

    def test_protected_and_100mb_rewards_both_sides_atomically(self):
        referral_id = self.attribute()
        self.ledger.mark_protected(referral_id, now=NOW)
        result = self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id="usage-100", now=NOW)
        self.assertTrue(result["rewarded_now"])
        self.assertEqual(result["status"], "rewarded")
        inviter = self.ledger.wallet.snapshot("inviter", now=NOW)["balances"]
        invitee = self.ledger.wallet.snapshot("invitee", now=NOW)["balances"]
        self.assertEqual(inviter["earned"], REWARD_BYTES)
        self.assertEqual(invitee["earned"], REWARD_BYTES)

    def test_usage_before_protection_or_below_100mb_does_not_reward(self):
        referral_id = self.attribute()
        before = self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id="usage-before", now=NOW)
        self.assertEqual(before["status"], "attributed")
        self.ledger.mark_protected(referral_id, now=NOW)
        below = self.ledger.record_usage(referral_id, 1, event_id="usage-after", now=NOW)
        self.assertEqual(below["status"], "rewarded")
        self.assertTrue(below["rewarded_now"])

    def test_duplicate_usage_event_never_pays_twice(self):
        referral_id = self.attribute()
        self.ledger.mark_protected(referral_id, now=NOW)
        first = self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id="usage-dupe", now=NOW)
        second = self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id="usage-dupe", now=NOW)
        self.assertTrue(first["rewarded_now"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(self.ledger.wallet.snapshot("inviter", now=NOW)["balances"]["earned"], REWARD_BYTES)

    def test_monthly_five_reward_cap_holds_sixth(self):
        for index in range(MONTHLY_REWARD_CAP + 1):
            referral_id = self.attribute("cap-inviter", f"invitee-{index}")
            self.ledger.mark_protected(referral_id, now=NOW)
            result = self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id=f"cap-usage-{index}", now=NOW)
        self.assertEqual(result["status"], "held")
        self.assertEqual(result["held_reason"], "monthly_cap")
        balance = self.ledger.wallet.snapshot("cap-inviter", now=NOW)["balances"]["earned"]
        self.assertEqual(balance, MONTHLY_REWARD_CAP * REWARD_BYTES)

    def test_holding_rewarded_case_does_not_claw_back(self):
        referral_id = self.attribute()
        self.ledger.mark_protected(referral_id, now=NOW)
        self.ledger.record_usage(referral_id, QUALIFY_BYTES, event_id="reward-first", now=NOW)
        before = self.ledger.wallet.snapshot("inviter", now=NOW)["balances"]["earned"]
        held = self.ledger.hold(referral_id, "late_signal")
        after = self.ledger.wallet.snapshot("inviter", now=NOW)["balances"]["earned"]
        self.assertEqual(held["status"], "rewarded")
        self.assertEqual(before, after)

    def test_storage_failure_is_fail_closed_and_honest(self):
        original = self.path.read_bytes()
        with mock.patch.object(self.ledger, "_connect", side_effect=OSError("blocked")):
            result = self.ledger.issue_token("inviter", now=NOW)
        self.assertFalse(result["applied"])
        self.assertIn("적용하지 않았", result["warning"])
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReferralLedgerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"추천 원장 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
