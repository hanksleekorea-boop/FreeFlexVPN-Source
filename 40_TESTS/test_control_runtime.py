#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_runtime import RuntimeConfigError, build_runtime, load_runtime_settings


KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
NOW = datetime.now(timezone.utc).isoformat()


class FakeSSH:
    def __call__(self, command):
        remote = command[-1]
        if remote.endswith(" health"):
            body = {"node_id": "sg-edge-1", "health": "healthy", "measured_at": NOW, "server_public_key": KEY}
        elif remote.endswith(" counters"):
            body = {"node_id": "sg-edge-1", "observed_at": NOW, "samples": []}
        else:
            body = {"error": "unexpected"}
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_runtime_")
        root = pathlib.Path(self.temp.name)
        self.identity = root / "id_ed25519"
        self.known = root / "known_hosts"
        self.identity.write_text("test-only", encoding="utf-8")
        self.known.write_text("vpn.example.test ssh-ed25519 test-only", encoding="utf-8")
        self.config = root / "nodes.json"
        self.db = root / "control.sqlite3"
        self.base = {
            "nodes": [{
                "server_id": "sg-edge-1", "node_id": "sg-edge-1", "host": "vpn.example.test",
                "ssh_user": "freeflex", "ssh_port": 22, "identity_file": str(self.identity),
                "known_hosts_file": str(self.known), "country_code": "SG", "country": "Singapore",
                "city": "Singapore", "provider_ref": "provider-a", "exit_ip": "8.8.8.8",
                "endpoint": "8.8.8.8:51820", "server_public_key": KEY,
                "dns_addresses": ["1.1.1.1"], "exit_verified": True,
                "verified_at": NOW, "capacity_percent": 10,
            }],
            "health_interval_seconds": 60,
            "counter_interval_seconds": 60,
        }
        self.write(self.base)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value):
        self.config.write_text(json.dumps(value), encoding="utf-8")

    def test_valid_external_config_builds_runtime_and_polls(self):
        api, adapter, poller = build_runtime(self.db, self.config, runner=FakeSSH())
        result = poller.run_once()
        self.assertTrue(result["health"][0]["healthy"])
        self.assertIsNone(result["counter_error"])
        self.assertEqual(api.catalog.public_catalog()["available_count"], 1)
        self.assertEqual(list(adapter.nodes), ["sg-edge-1"])

    def test_embedded_private_key_is_rejected_negative_control(self):
        changed = json.loads(json.dumps(self.base))
        changed["private_key"] = "must-not-enter-config"
        self.write(changed)
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings(self.config)

    def test_relative_config_path_is_rejected(self):
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings("nodes.json")

    def test_unknown_field_is_rejected(self):
        changed = json.loads(json.dumps(self.base))
        changed["nodes"][0]["nickname"] = "extra"
        self.write(changed)
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings(self.config)

    def test_empty_nodes_and_fast_polling_are_rejected(self):
        changed = json.loads(json.dumps(self.base))
        changed["nodes"] = []
        self.write(changed)
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings(self.config)
        changed = json.loads(json.dumps(self.base))
        changed["health_interval_seconds"] = 1
        self.write(changed)
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings(self.config)

    def test_korean_exit_is_rejected(self):
        changed = json.loads(json.dumps(self.base))
        changed["nodes"][0]["country_code"] = "KR"
        self.write(changed)
        with self.assertRaises(RuntimeConfigError):
            load_runtime_settings(self.config)

    def test_poller_start_stop_is_idempotent(self):
        _api, _adapter, poller = build_runtime(self.db, self.config, runner=FakeSSH())
        poller.start()
        poller.start()
        poller.stop()
        poller.stop()

    def test_transient_counter_failure_does_not_kill_runtime(self):
        class CounterFailure(FakeSSH):
            def __call__(self, command):
                if command[-1].endswith(" counters"):
                    return subprocess.CompletedProcess(command, 20, "", "private remote detail")
                return super().__call__(command)

        _api, _adapter, poller = build_runtime(self.db, self.config, runner=CounterFailure())
        result = poller.run_once()
        self.assertEqual(result["counter_error"], "NodeAdapterError")
        self.assertTrue(result["health"][0]["healthy"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print(f"제어 런타임 검사 {result.testsRun}/{result.testsRun} 통과")
