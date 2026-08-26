#!/usr/bin/env python3
"""GCP-TASK-0-01 공통 증거 계약의 양성·음성 대조."""
from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.evidence_contract import (  # noqa: E402
    EvidenceContractError,
    SCHEMA,
    evidence_freshness,
    require_all_sources,
    require_source_for_use,
    validate_evidence_record,
)


NOW = datetime(2026, 8, 25, 6, 0, tzinfo=timezone.utc)


def record(**changes):
    value = {
        "schema": SCHEMA,
        "evidence_id": "android-check-001",
        "subject_scope": "device",
        "observed_at": "2026-08-25T05:00:00+00:00",
        "expires_at": "2026-08-25T07:00:00+00:00",
        "source_class": "android",
        "result": "pass",
        "redaction": ["account", "identifier", "ip", "key"],
        "version": {"app": "1.0.0", "policy": "2026-08-25"},
    }
    value.update(changes)
    return value


class EvidenceContractTests(unittest.TestCase):
    def test_valid_record_is_public_and_fresh(self):
        verified = validate_evidence_record(record(), now=NOW)
        self.assertEqual(evidence_freshness(verified, now=NOW), "fresh")
        self.assertEqual(verified.public_summary()["source_class"], "android")
        self.assertNotIn("endpoint", verified.public_summary())

    def test_missing_or_unsafe_shape_is_rejected(self):
        for changes in (
            {"schema": "wrong"},
            {"evidence_id": "x"},
            {"observed_at": "2026-08-25T05:00:00"},
            {"redaction": []},
            {"version": {}},
            {"unreviewed_note": "raw value"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(EvidenceContractError):
                    validate_evidence_record(record(**changes), now=NOW)

    def test_future_expired_and_no_expiry_freshness_are_not_overclaimed(self):
        with self.assertRaises(EvidenceContractError):
            validate_evidence_record(record(observed_at="2026-08-25T06:06:00+00:00"), now=NOW)
        with self.assertRaises(EvidenceContractError):
            validate_evidence_record(record(expires_at="2026-08-25T04:59:00+00:00"), now=NOW)
        stale = validate_evidence_record(record(expires_at="2026-08-25T05:59:00+00:00"), now=NOW)
        self.assertEqual(evidence_freshness(stale, now=NOW), "stale")
        timeless = validate_evidence_record(record(expires_at=None), now=NOW)
        self.assertEqual(evidence_freshness(timeless, now=NOW), "unknown")
        self.assertEqual(evidence_freshness(timeless, now=NOW, max_age_seconds=7200), "fresh")

    def test_sensitive_fields_are_rejected_at_any_depth(self):
        value = record(version={"app": "1.0", "nested": {"serial": "redacted"}})
        with self.assertRaisesRegex(EvidenceContractError, "민감"):
            validate_evidence_record(value, now=NOW)

    def test_source_class_cannot_be_promoted_to_real_world_evidence(self):
        automatic = validate_evidence_record(record(source_class="automatic"), now=NOW)
        with self.assertRaises(EvidenceContractError):
            require_source_for_use(automatic, "android_protection")
        with self.assertRaises(EvidenceContractError):
            require_all_sources([automatic], "payment_transaction")
        android = validate_evidence_record(record(), now=NOW)
        require_source_for_use(android, "android_protection")
        require_all_sources([automatic, android], "android_protection")


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(0 if result.wasSuccessful() else 1)
