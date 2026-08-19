#!/usr/bin/env python3
"""Safety contracts for one-idle-phone Android test selection."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.android_idle_guard import CommandResult, _read_only, inspect_devices, select_one_idle_device, write_new_json  # noqa: E402


class ScriptedRunner:
    def __init__(self, results):
        self.results = list(results)
        self.commands = []

    def __call__(self, argv):
        self.commands.append(tuple(argv))
        return self.results.pop(0)


def listing(*rows: str) -> str:
    return "List of devices attached\n" + "\n".join(rows) + "\n"


class AndroidIdleGuardTests(unittest.TestCase):
    def test_awake_devices_are_never_selected_and_raw_identifiers_are_absent(self):
        serial = "R3CR106852H"
        runner = ScriptedRunner([
            CommandResult(0, listing(f"{serial} device model:SM_G996N")),
            CommandResult(0, "mWakefulness=Awake\n"), CommandResult(0, "mCurrentFocus=Window{abc}\n"),
            CommandResult(0, "null\n"), CommandResult(0, "0\n"),
        ])
        observations = inspect_devices(adb="adb", runner=runner)
        receipt = select_one_idle_device(observations, checked_at=datetime(2026, 8, 19, tzinfo=timezone.utc))
        encoded = json.dumps(receipt)
        self.assertEqual(receipt["status"], "blocked_no_idle_device")
        self.assertEqual(receipt["mutation_count"], 0)
        self.assertNotIn(serial, encoded)
        self.assertNotIn("mCurrentFocus", encoded)

    def test_exactly_one_sleeping_unprotected_device_is_selected(self):
        runner = ScriptedRunner([
            CommandResult(0, listing("R3CR106852H device model:SM_G996N", "R5CY32TNJFM device model:SM_A5660")),
            CommandResult(0, "mWakefulness=Asleep\n"), CommandResult(0, ""), CommandResult(0, "null\n"), CommandResult(0, "0\n"),
            CommandResult(0, "mWakefulness=Awake\n"), CommandResult(0, "mCurrentFocus=Window{x}\n"), CommandResult(0, "null\n"), CommandResult(0, "0\n"),
        ])
        receipt = select_one_idle_device(inspect_devices(adb="adb", runner=runner))
        self.assertEqual(receipt["status"], "selected")
        self.assertEqual(receipt["eligible_count"], 1)
        self.assertEqual(receipt["next_action"], "manual_user_confirmation_then_test")

    def test_multiple_idle_devices_fail_closed(self):
        observations = [
            {"device_fingerprint": "a", "eligible": True}, {"device_fingerprint": "b", "eligible": True},
        ]
        receipt = select_one_idle_device(observations)
        self.assertEqual(receipt["status"], "blocked_multiple_idle_devices")
        self.assertIsNone(receipt["selected_device_fingerprint"])

    def test_always_on_or_lockdown_blocks_selection(self):
        runner = ScriptedRunner([
            CommandResult(0, listing("R3CR106852H device model:SM_G996N")),
            CommandResult(0, "mWakefulness=Asleep\n"), CommandResult(0, ""), CommandResult(0, "com.wireguard.android\n"), CommandResult(0, "1\n"),
        ])
        receipt = select_one_idle_device(inspect_devices(adb="adb", runner=runner))
        self.assertEqual(receipt["status"], "blocked_no_idle_device")
        self.assertEqual(receipt["devices"][0]["reason"], "existing_vpn_protection_present_or_unknown")

    def test_non_ready_adb_state_is_not_probed_or_selected(self):
        runner = ScriptedRunner([CommandResult(0, listing("R3CR106852H offline model:SM_G996N"))])
        receipt = select_one_idle_device(inspect_devices(adb="adb", runner=runner))
        self.assertEqual(receipt["devices"][0]["reason"], "adb_not_ready")
        self.assertEqual(len(runner.commands), 1)

    def test_command_policy_rejects_mutation_forms(self):
        self.assertTrue(_read_only(("adb", "devices", "-l")))
        self.assertTrue(_read_only(("adb", "-s", "R3CR106852H", "shell", "settings", "get", "secure", "always_on_vpn_app")))
        self.assertFalse(_read_only(("adb", "-s", "R3CR106852H", "shell", "settings", "put", "secure", "always_on_vpn_app", "x")))
        self.assertFalse(_read_only(("adb", "-s", "R3CR106852H", "shell", "input", "keyevent", "HOME")))

    def test_receipt_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "selection.json"
            write_new_json(path, {"status": "first"})
            with self.assertRaises(FileExistsError):
                write_new_json(path, {"status": "second"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"status": "first"})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AndroidIdleGuardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Android idle guard contract {passed}/{result.testsRun}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
