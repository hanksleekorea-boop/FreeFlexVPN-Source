#!/usr/bin/env python3
"""WireGuard 카운터 기반 1GB·충전 쿼터 에이전트 검사."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra import quota_agent as qa
from infra.cloud_init import EXAMPLE_ADMIN_CIDR, ExitNodeSpec, build_config

KEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA="
OTHER_KEY = "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI="
ACCOUNT_ID = "a" * 64
JULY = dt.datetime(2026, 7, 10, tzinfo=dt.timezone.utc)
AUGUST = dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc)


def dump(peer_key=KEY, allowed="10.66.0.2/32", rx=100, tx=200):
    return (
        "priv\tpub\t51820\toff\n"
        f"{peer_key}\t(none)\t198.51.100.2:50000\t{allowed}\t1\t{rx}\t{tx}\toff\n"
    )


class QuotaAgentTests(unittest.TestCase):
    def test_wg_dump_parses_rx_plus_tx(self):
        peer = qa.parse_wg_dump(dump())[KEY]
        self.assertEqual(peer["allowed_ip"], "10.66.0.2")
        self.assertEqual(peer["total_bytes"], 300)

    def test_wg_dump_rejects_multiple_or_wide_allowed_ips(self):
        for value in ("10.66.0.2/32,0.0.0.0/0", "10.66.0.0/24"):
            with self.assertRaises(ValueError):
                qa.parse_wg_dump(dump(allowed=value))

    def test_free_bytes_are_charged_before_paid(self):
        peer = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        peer["paid_bytes"] = qa.GB
        result = qa.charge_counter(peer, qa.GB + 250, JULY)
        self.assertEqual(result["charged_bytes"], qa.GB + 250)
        self.assertEqual(peer["free_used_bytes"], qa.GB)
        self.assertEqual(peer["paid_bytes"], qa.GB - 250)
        self.assertFalse(peer["blocked"])

    def test_counter_reset_charges_new_counter_not_negative_delta(self):
        peer = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, baseline=900, now=JULY)
        result = qa.charge_counter(peer, 100, JULY)
        self.assertEqual(result["delta_bytes"], 100)
        self.assertEqual(peer["free_used_bytes"], 100)

    def test_cumulative_counter_charges_only_growth(self):
        peer = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, baseline=100, now=JULY)
        result = qa.charge_counter(peer, 350, JULY)
        self.assertEqual(result["delta_bytes"], 250)
        self.assertEqual(peer["free_used_bytes"], 250)

    def test_exhaustion_blocks_and_never_goes_negative(self):
        peer = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        result = qa.charge_counter(peer, qa.GB + 1, JULY)
        self.assertEqual(result["charged_bytes"], qa.GB)
        self.assertEqual(peer["paid_bytes"], 0)
        self.assertTrue(peer["blocked"])

    def test_month_reset_restores_free_and_preserves_paid(self):
        peer = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        peer["free_used_bytes"] = qa.GB
        peer["paid_bytes"] = 777
        self.assertEqual(qa.available_bytes(peer, AUGUST), qa.GB + 777)
        self.assertEqual(peer["paid_bytes"], 777)

    def test_unknown_peer_is_fail_closed_without_key_in_result(self):
        state = qa.empty_state()
        result = qa.poll_state(state, qa.parse_wg_dump(dump()), JULY)
        self.assertEqual(result["unknown_peers"], 1)
        self.assertNotIn(KEY, json.dumps(result))
        self.assertTrue(state["peers"][KEY]["blocked"])
        self.assertEqual(state["peers"][KEY]["block_reason"], "enrollment_required")

    def test_changed_allowed_ip_is_blocked(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        qa.poll_state(state, {KEY: {"allowed_ip": "10.66.0.9", "total_bytes": 1}}, JULY)
        self.assertTrue(state["peers"][KEY]["blocked"])
        self.assertEqual(state["peers"][KEY]["block_reason"], "allowed_ip_changed")

    def test_nft_batch_contains_only_blocked_peer_ips(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=False, now=JULY)
        state["peers"][OTHER_KEY] = qa.new_peer("10.66.0.3", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        batch = qa.nft_batch(state)
        self.assertIn("10.66.0.2", batch)
        self.assertNotIn("10.66.0.3", batch)
        self.assertTrue(batch.startswith("flush set"))

    def test_topup_unblocks_and_does_not_expire(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        state["peers"][KEY]["free_used_bytes"] = qa.GB
        state["peers"][KEY]["blocked"] = True
        qa.topup(state, KEY, 500, JULY)
        self.assertEqual(state["peers"][KEY]["paid_bytes"], 500)
        self.assertFalse(state["peers"][KEY]["blocked"])
        self.assertEqual(qa.available_bytes(state["peers"][KEY], AUGUST), qa.GB + 500)

    def test_corrupt_state_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_quota_") as tmp:
            path = pathlib.Path(tmp) / "state.json"
            original = b"{broken"
            path.write_bytes(original)
            with self.assertRaises(qa.QuotaStateError):
                qa.load_state(path)
            self.assertEqual(path.read_bytes(), original)

    def test_atomic_write_roundtrip(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_quota_") as tmp:
            path = pathlib.Path(tmp) / "state.json"
            state = qa.empty_state()
            state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
            qa.write_state_atomic(path, state)
            loaded = qa.load_state(path)
            self.assertEqual(loaded["peers"][KEY]["allowed_ip"], "10.66.0.2")

    def test_failed_replace_preserves_previous_state(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_quota_") as tmp:
            path = pathlib.Path(tmp) / "state.json"
            original = qa.empty_state()
            qa.write_state_atomic(path, original)
            before = path.read_bytes()
            changed = qa.empty_state()
            changed["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
            with mock.patch.object(qa.os, "replace", side_effect=OSError("blocked")):
                with self.assertRaises(qa.QuotaStateError):
                    qa.write_state_atomic(path, changed)
            self.assertEqual(path.read_bytes(), before)

    def test_cloud_init_embeds_exact_agent_and_enforcement_timer(self):
        config = build_config(ExitNodeSpec(EXAMPLE_ADMIN_CIDR, example=True))
        files = {item["path"]: item for item in config["write_files"]}
        self.assertEqual(files["/opt/freeflexvpn/quota_agent.py"]["content"], pathlib.Path(qa.__file__).read_text(encoding="utf-8"))
        self.assertIn("quota_blocked_v4", files["/etc/nftables.conf"]["content"])
        self.assertIn("OnUnitActiveSec=1min", files["/etc/systemd/system/freeflexvpn-quota.timer"]["content"])

    def test_public_key_validation_rejects_zero_and_malformed(self):
        for value in ("not-base64", "A" * 43 + "="):
            with self.assertRaises(ValueError):
                qa.validate_public_key(value)
        self.assertEqual(qa.validate_public_key(KEY), KEY)

    def test_revoke_preserves_balance_and_marks_fail_closed(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        state["peers"][KEY]["paid_bytes"] = 1234
        qa.revoke(state, KEY)
        peer = state["peers"][KEY]
        self.assertFalse(peer["enrolled"])
        self.assertTrue(peer["blocked"])
        self.assertEqual(peer["block_reason"], "revoked")
        self.assertEqual(peer["paid_bytes"], 1234)

    def test_wireguard_sync_removes_unknown_and_restores_enrolled(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        observed = {OTHER_KEY: {"allowed_ip": "10.66.0.3", "total_bytes": 0}}
        completed = SimpleNamespace(returncode=0, stderr="")
        with mock.patch.object(qa.subprocess, "run", return_value=completed) as run:
            result = qa.sync_wireguard(state, observed)
        self.assertEqual(result, {"removed_peers": 1, "ensured_peers": 1})
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["wg", "set", "wg0", "peer", OTHER_KEY, "remove"], commands)
        self.assertIn(["wg", "set", "wg0", "peer", KEY, "allowed-ips", "10.66.0.2/32"], commands)

    def test_revoked_peer_is_removed_and_never_restored(self):
        state = qa.empty_state()
        state["peers"][KEY] = qa.new_peer("10.66.0.2", enrolled=True, account_id=ACCOUNT_ID, now=JULY)
        qa.revoke(state, KEY)
        observed = {KEY: {"allowed_ip": "10.66.0.2", "total_bytes": 10}}
        completed = SimpleNamespace(returncode=0, stderr="")
        with mock.patch.object(qa.subprocess, "run", return_value=completed) as run:
            result = qa.sync_wireguard(state, observed)
        self.assertEqual(result, {"removed_peers": 1, "ensured_peers": 0})
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands, [["wg", "set", "wg0", "peer", KEY, "remove"]])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QuotaAgentTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"쿼터 에이전트 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
