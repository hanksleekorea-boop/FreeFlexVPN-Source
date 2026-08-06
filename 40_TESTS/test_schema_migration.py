#!/usr/bin/env python3
"""v2 알파 SQLite migration 구조·재실행·제약 검사."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_api import ControlAPI  # noqa: E402


REQUIRED_TABLES = {
    "accounts", "api_claims", "api_sessions", "devices", "peer_runtime",
    "safety_observations", "deletion_requests", "wallet_entries", "wallet_events",
    "session_receipts", "referral_tokens", "referrals", "referral_usage_events",
    "servers", "usage_events", "peer_counter_state", "audit_events",
}


class SchemaMigrationTests(unittest.TestCase):
    def test_migration_is_repeatable_and_complete(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_schema_") as temp:
            path = pathlib.Path(temp) / "control.sqlite3"
            first = ControlAPI(path)
            second = ControlAPI(path)
            self.assertEqual(first.persistence_status, "persistent")
            self.assertEqual(second.persistence_status, "persistent")
            with closing(sqlite3.connect(path)) as connection:
                tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            self.assertTrue(REQUIRED_TABLES.issubset(tables), REQUIRED_TABLES - tables)
            self.assertEqual(violations, [])

    def test_schema_constraints_reject_impossible_rows_negative_control(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_schema_negative_") as temp:
            path = pathlib.Path(temp) / "control.sqlite3"
            ControlAPI(path)
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("PRAGMA foreign_keys=ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """INSERT INTO wallet_entries
                           (account_id,bucket,delta_bytes,reason,idem_key,free_month,created_at)
                           VALUES ('a','invented',1,'x','x',NULL,'now')"""
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """INSERT INTO usage_events VALUES
                           ('event','node','device','account','session',0,-1,0,0,0,'{}','now')"""
                    )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SchemaMigrationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"DB migration 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
