#!/usr/bin/env python3
"""Telegram 동의·일회용 수령권·개인정보 최소화 계약 검사."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.telegram_flow import handle_update
from app.telegram_onboarding import OnboardingError, OnboardingLedger
from infra.telegram_bot_config import build_config

SECRET = b"identity-hmac-key-for-tests-only-32-bytes-plus"
USER_ID = 918273645
PUBLIC_KEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA="
NOW = datetime(2026, 8, 1, 3, 0, tzinfo=timezone.utc)
BASE_URL = "https://claim.freeflexvpn.example/claim"


class TelegramOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_tg_")
        self.path = pathlib.Path(self.temp.name) / "onboarding.json"
        self.ledger = OnboardingLedger(self.path, SECRET)

    def tearDown(self):
        self.temp.cleanup()

    def accept(self):
        return self.ledger.accept(USER_ID, "privacy-v1", now=NOW)

    def issue(self, **kwargs):
        self.accept()
        return self.ledger.issue_claim(USER_ID, BASE_URL, now=NOW, **kwargs)

    @staticmethod
    def token(result):
        return parse_qs(urlparse(result["claim_url"]).query)["ticket"][0]

    def test_start_message_stores_nothing(self):
        fake_phone = "010-" + "1234-" + "5678"
        update = {"message": {"from": {"id": USER_ID, "username": "raw-user", "phone_number": fake_phone}, "text": "/start"}}
        result = handle_update(update, self.ledger, policy_version="privacy-v1", claim_base_url=BASE_URL)
        self.assertIn("월 1GB", result["text"])
        self.assertFalse(self.path.exists())

    def test_accept_persists_hmac_subject_not_raw_identity(self):
        self.accept()
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn(str(USER_ID), raw)
        self.assertNotIn("username", raw)
        subject = next(iter(json.loads(raw)["users"]))
        expected = __import__("hmac").new(SECRET, str(USER_ID).encode("ascii"), hashlib.sha256).hexdigest()
        self.assertEqual(subject, expected)

    def test_claim_requires_consent(self):
        with self.assertRaises(OnboardingError):
            self.ledger.issue_claim(USER_ID, BASE_URL, now=NOW)

    def test_claim_token_is_returned_once_but_never_persisted(self):
        result = self.issue()
        token = self.token(result)
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn(token, raw)
        self.assertIn(hashlib.sha256(token.encode("ascii")).hexdigest(), raw)
        self.assertFalse(result["loggable"])

    def test_new_claim_invalidates_previous_unused_claim(self):
        first = self.issue()
        second = self.ledger.issue_claim(USER_ID, BASE_URL, now=NOW + timedelta(seconds=1))
        with self.assertRaises(OnboardingError):
            self.ledger.consume_claim(self.token(first), PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=2))
        consumed = self.ledger.consume_claim(self.token(second), PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=2))
        self.assertEqual(consumed["status"], "claim_consumed")

    def test_claim_is_single_use(self):
        result = self.issue()
        token = self.token(result)
        self.ledger.consume_claim(token, PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=1))
        with self.assertRaises(OnboardingError):
            self.ledger.consume_claim(token, PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=2))

    def test_expired_claim_is_rejected_without_peer(self):
        result = self.issue(ttl_seconds=60)
        with self.assertRaises(OnboardingError):
            self.ledger.consume_claim(self.token(result), PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=60))
        self.assertEqual(self.ledger.status(USER_ID)["peer_status"], "not_issued")

    def test_claim_rejects_out_of_pool_ip_without_mutation(self):
        result = self.issue()
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.ledger.consume_claim(self.token(result), PUBLIC_KEY, "10.67.0.2/32", now=NOW + timedelta(seconds=1))
        self.assertEqual(self.path.read_bytes(), before)

    def test_decline_without_peer_erases_pseudonymous_record(self):
        self.issue()
        result = self.ledger.decline(USER_ID)
        self.assertEqual(result["status"], "not_stored")
        state = self.ledger.audit_snapshot()
        self.assertEqual(state["users"], {})
        self.assertEqual(state["claims"], {})

    def test_revoke_is_two_phase_and_confirmed_only_after_server_action(self):
        claim = self.issue()
        self.ledger.consume_claim(self.token(claim), PUBLIC_KEY, "10.66.0.2/32", now=NOW + timedelta(seconds=1))
        pending = self.ledger.request_revoke(USER_ID)
        self.assertEqual(pending["status"], "revoke_pending")
        self.assertEqual(self.ledger.status(USER_ID)["peer_status"], "revoke_pending")
        confirmed = self.ledger.confirm_revoke(PUBLIC_KEY, now=NOW + timedelta(seconds=2))
        self.assertEqual(confirmed["status"], "revoked")
        self.assertEqual(self.ledger.status(USER_ID)["peer_status"], "revoked")

    def test_corrupt_state_is_preserved_and_fails_closed(self):
        original = b"{broken"
        self.path.write_bytes(original)
        with self.assertRaises(OnboardingError):
            self.ledger.accept(USER_ID, "privacy-v1", now=NOW)
        self.assertEqual(self.path.read_bytes(), original)

    def test_save_failure_returns_no_claim_and_preserves_consent(self):
        self.accept()
        before = self.path.read_bytes()
        with mock.patch("app.telegram_onboarding.os.replace", side_effect=OSError("blocked")):
            with self.assertRaises(OnboardingError):
                self.ledger.issue_claim(USER_ID, BASE_URL, now=NOW)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.ledger.audit_snapshot()["claims"], {})

    def test_flow_marks_claim_response_non_loggable(self):
        self.accept()
        update = {"message": {"from": {"id": USER_ID}, "text": "/claim"}}
        result = handle_update(update, self.ledger, policy_version="privacy-v1", claim_base_url=BASE_URL)
        self.assertFalse(result["loggable"])
        self.assertIn("ticket=", result["claim_url"])

    def test_example_config_has_env_names_not_secret_values(self):
        config = build_config(claim_base_url="https://example.invalid/claim", example=True)
        self.assertFalse(config["enabled"])
        self.assertEqual(config["status"], "ADAPTER_OR_DEMO")
        self.assertEqual(config["claim"]["private_key_delivery"], "forbidden_in_telegram")
        self.assertIn("telegram_user_id", config["privacy"]["not_stored"])
        self.assertTrue(all(value.startswith("FREEFLEX_") for value in config["environment"].values()))

    def test_config_cli_is_deterministic_and_secret_free(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_tg_config_") as tmp:
            first = pathlib.Path(tmp) / "first.json"
            second = pathlib.Path(tmp) / "second.json"
            outputs = []
            for path in (first, second):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "70_TOOLS" / "build_telegram_bot_config.py"), "--example", "--output", str(path)],
                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                outputs.append(proc.stdout)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            text = first.read_text(encoding="utf-8")
            self.assertNotIn("123456:", text)
            self.assertIn(hashlib.sha256(first.read_bytes()).hexdigest().upper(), outputs[0])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TelegramOnboardingTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"Telegram 온보딩 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
