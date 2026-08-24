#!/usr/bin/env python3
"""FreeFlexVPN v2 3지갑 append-only 원장 검사."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.wallet_ledger import (  # noqa: E402
    FREE_CAP_BYTES,
    GB,
    MB,
    InsufficientWalletBalance,
    IdempotencyConflict,
    WalletLedger,
)


class WalletLedgerV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_wallet_v2_")
        self.path = pathlib.Path(self.temp.name) / "wallet.sqlite3"
        self.ledger = WalletLedger(self.path)
        self.account = "acct_test_001"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_three_buckets_and_free_earned_paid_order(self):
        self.ledger.credit(self.account, "earned", 500 * MB, event_id="reward-1", reason="referral")
        self.ledger.credit(self.account, "paid", 2 * GB, event_id="topup-1", reason="topup")
        result = self.ledger.consume(
            self.account,
            FREE_CAP_BYTES + 700 * MB,
            event_id="usage-1",
            session_id="session-1",
            now=date(2026, 8, 1),
        )
        self.assertEqual(result["consumed"], {"free": FREE_CAP_BYTES, "earned": 500 * MB, "paid": 200 * MB})
        self.assertEqual(result["balances"]["paid"], 1_800 * MB)

    def test_duplicate_usage_is_idempotent_and_receipt_is_single(self):
        first = self.ledger.consume(self.account, 100 * MB, event_id="usage-dupe", session_id="session-dupe", now=date(2026, 8, 1))
        second = self.ledger.consume(self.account, 100 * MB, event_id="usage-dupe", session_id="ignored-new-session", now=date(2026, 8, 1))
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["balances"], second["balances"])
        self.assertEqual(len(self.ledger.receipts(self.account)), 1)

    def test_month_rollover_expires_free_only(self):
        self.ledger.credit(self.account, "earned", 500 * MB, event_id="reward-roll", reason="referral")
        self.ledger.credit(self.account, "paid", GB, event_id="topup-roll", reason="topup")
        self.ledger.consume(self.account, 600 * MB, event_id="usage-july", session_id="july", now=date(2026, 7, 31))
        august = self.ledger.snapshot(self.account, now=date(2026, 8, 1))
        self.assertEqual(august["balances"], {"free": FREE_CAP_BYTES, "earned": 500 * MB, "paid": GB})

    def test_insufficient_usage_is_atomic(self):
        before = self.ledger.snapshot(self.account, now=date(2026, 8, 1))["balances"]
        with self.assertRaises(InsufficientWalletBalance):
            self.ledger.consume(self.account, FREE_CAP_BYTES + 1, event_id="too-large", session_id="too-large", now=date(2026, 8, 1))
        after = self.ledger.snapshot(self.account, now=date(2026, 8, 1))["balances"]
        self.assertEqual(before, after)
        self.assertEqual(self.ledger.receipts(self.account), [])

    def test_restart_recovers_append_only_balances(self):
        self.ledger.credit(self.account, "earned", 500 * MB, event_id="reward-restart", reason="referral")
        self.ledger.consume(self.account, 200 * MB, event_id="usage-restart", session_id="restart", now=date(2026, 8, 1))
        reopened = WalletLedger(self.path)
        state = reopened.snapshot(self.account, now=date(2026, 8, 1))
        self.assertEqual(state["balances"], {"free": 800 * MB, "earned": 500 * MB, "paid": 0})
        self.assertEqual(len(reopened.receipts(self.account)), 1)

    def test_entries_are_append_only_and_idem_keys_unique(self):
        self.ledger.credit(self.account, "earned", 500 * MB, event_id="reward-audit", reason="referral")
        self.ledger.consume(self.account, 1_100 * MB, event_id="usage-audit", session_id="audit", now=date(2026, 8, 1))
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute("SELECT delta_bytes, idem_key FROM wallet_entries ORDER BY entry_id").fetchall()
        self.assertEqual(len(rows), len({row[1] for row in rows}))
        self.assertTrue(any(row[0] > 0 for row in rows))
        self.assertTrue(any(row[0] < 0 for row in rows))

    def test_storage_failure_is_fail_closed_and_honest(self):
        before = self.path.read_bytes()
        with mock.patch.object(self.ledger, "_connect", side_effect=OSError("blocked")):
            result = self.ledger.credit(self.account, "paid", GB, event_id="failed-topup", reason="topup")
        self.assertFalse(result["applied"])
        self.assertIsNone(result["balances"])
        self.assertIn("적용하지 않았", result["warning"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_database_is_preserved(self):
        corrupt_path = pathlib.Path(self.temp.name) / "corrupt.sqlite3"
        original = b"not-a-sqlite-database"
        corrupt_path.write_bytes(original)
        ledger = WalletLedger(corrupt_path)
        result = ledger.snapshot(self.account)
        self.assertFalse(result["applied"])
        self.assertEqual(corrupt_path.read_bytes(), original)
        self.assertIn("덮어쓰지 않았", result["warning"])

    def test_negative_controls_reject_invalid_credit_and_usage(self):
        with self.assertRaises(ValueError):
            self.ledger.credit(self.account, "free", GB, event_id="bad-free", reason="manual")
        with self.assertRaises(ValueError):
            self.ledger.credit(self.account, "earned", -1, event_id="bad-negative", reason="manual")
        with self.assertRaises(ValueError):
            self.ledger.consume(self.account, 0, event_id="bad-zero", session_id="bad-zero")

    def test_low_balance_signal_uses_real_balances(self):
        result = self.ledger.consume(self.account, 950 * MB, event_id="usage-low", session_id="low", now=date(2026, 8, 1))
        self.assertEqual(result["low_balance"], "100mb")

    def test_event_id_is_bound_to_account_type_and_amount(self):
        self.ledger.credit(self.account, "paid", GB, event_id="bound-event", reason="topup")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.credit("another-account", "paid", GB, event_id="bound-event", reason="topup")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.credit(self.account, "paid", 2 * GB, event_id="bound-event", reason="topup")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.consume(self.account, MB, event_id="bound-event", session_id="bound-session", now=date(2026, 8, 1))

    def test_concurrent_duplicate_usage_is_charged_once(self):
        def consume_once(_index: int):
            ledger = WalletLedger(self.path)
            return ledger.consume(self.account, 100 * MB, event_id="concurrent-usage", session_id="concurrent-session", now=date(2026, 8, 1))
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(consume_once, range(6)))
        self.assertEqual(sum(result["duplicate"] is False for result in results), 1)
        self.assertEqual(sum(result["duplicate"] is True for result in results), 5)
        self.assertEqual(self.ledger.snapshot(self.account, now=date(2026, 8, 1))["balances"]["free"], 900 * MB)

    def test_aware_datetime_month_uses_utc_boundary(self):
        bangkok = timezone(timedelta(hours=7))
        local_august = datetime(2026, 8, 1, 1, 0, tzinfo=bangkok)
        state = self.ledger.snapshot(self.account, now=local_august)
        self.assertEqual(state["month"], "2026-07")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WalletLedgerV2Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"v2 지갑 원장 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
