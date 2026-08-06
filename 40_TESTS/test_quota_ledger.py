#!/usr/bin/env python3
"""FreeFlexVPN 1GB 무료·무기한 충전 원장 검사."""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from datetime import date
from unittest import mock

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.quota_ledger import GB, InsufficientBalance, QuotaLedger
from cost_model import CAP_GB_FREE, PRODUCT_NAME


class QuotaLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_ledger_")
        self.path = pathlib.Path(self.temp.name) / "ledger.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_monthly_free_cap_comes_from_contract(self):
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        state = ledger.snapshot(now=date(2026, 7, 1))
        self.assertEqual(state["product"], PRODUCT_NAME)
        self.assertEqual(state["free_cap_bytes"], int(CAP_GB_FREE * GB))

    def test_free_is_used_before_paid_balance(self):
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        ledger.top_up_gb(2)
        result = ledger.consume(int(CAP_GB_FREE * GB) + GB // 2, now=date(2026, 7, 2))
        self.assertEqual(result["consumed_free_bytes"], int(CAP_GB_FREE * GB))
        self.assertEqual(result["consumed_paid_bytes"], GB // 2)
        self.assertEqual(result["paid_bytes"], GB + GB // 2)

    def test_month_reset_does_not_expire_paid_balance(self):
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        ledger.top_up_gb(3)
        ledger.consume(GB // 2, now=date(2026, 7, 10))
        august = ledger.snapshot(now=date(2026, 8, 1))
        self.assertEqual(august["free_remaining_bytes"], int(CAP_GB_FREE * GB))
        self.assertEqual(august["paid_bytes"], 3 * GB)
        next_year = ledger.snapshot(now=date(2027, 8, 1))
        self.assertEqual(next_year["paid_bytes"], 3 * GB)
        self.assertFalse(next_year["topup_expires"])

    def test_insufficient_balance_keeps_state_unchanged(self):
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        before = ledger.snapshot(now=date(2026, 7, 1))
        with self.assertRaises(InsufficientBalance):
            ledger.consume(before["total_available_bytes"] + 1, now=date(2026, 7, 1))
        after = ledger.snapshot(now=date(2026, 7, 1))
        self.assertEqual(before["free_used_bytes"], after["free_used_bytes"])
        self.assertEqual(before["paid_bytes"], after["paid_bytes"])

    def test_persisted_balance_reloads(self):
        first = QuotaLedger(self.path, now=date(2026, 7, 1))
        first.top_up_gb(4)
        first.consume(GB // 4, now=date(2026, 7, 1))
        second = QuotaLedger(self.path, now=date(2026, 7, 1))
        july_state = second.snapshot(now=date(2026, 7, 1))
        self.assertEqual(july_state["paid_bytes"], 4 * GB)
        self.assertEqual(july_state["free_used_bytes"], GB // 4)

    def test_save_failure_keeps_input_in_memory_and_warns(self):
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        with mock.patch.object(ledger, "_write_atomic", side_effect=OSError("blocked")):
            state = ledger.top_up_gb(2)
        self.assertEqual(state["paid_bytes"], 2 * GB)
        self.assertEqual(state["persistence_status"], "memory_only")
        self.assertIn("메모리", state["warning"])

    def test_corrupt_storage_is_preserved_and_honestly_reported(self):
        original = b"{not-json"
        self.path.write_bytes(original)
        ledger = QuotaLedger(self.path, now=date(2026, 7, 1))
        state = ledger.snapshot()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(state["persistence_status"], "memory_only")
        self.assertIn("덮어쓰지 않았", state["warning"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QuotaLedgerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"쿼터 원장 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
