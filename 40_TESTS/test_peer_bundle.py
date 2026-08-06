#!/usr/bin/env python3
"""저장소 외부 WireGuard 클라이언트 구성·QR 발급 검사."""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.peer_bundle import PeerSpec, build_bundle, generate_keypair, render_client_config

SERVER_KEY = "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI="
PRIVATE_BYTES = bytes(range(1, 33))
PRIVATE_B64 = base64.b64encode(PRIVATE_BYTES).decode("ascii")


def spec(**changes):
    values = {
        "name": "light-01",
        "server_public_key": SERVER_KEY,
        "endpoint": "198.51.100.20:51820",
        "client_ip": "10.66.0.2/32",
        "dns": "1.1.1.1",
    }
    values.update(changes)
    return PeerSpec(**values)


class PeerBundleTests(unittest.TestCase):
    def test_keypair_is_raw_x25519_base64(self):
        private, public = generate_keypair(PRIVATE_BYTES)
        self.assertEqual(private, PRIVATE_B64)
        self.assertEqual(len(base64.b64decode(public, validate=True)), 32)
        self.assertNotEqual(private, public)

    def test_config_routes_ipv4_and_ipv6_to_tunnel(self):
        config = render_client_config(spec(), PRIVATE_B64)
        self.assertIn("AllowedIPs = 0.0.0.0/0, ::/0", config)
        self.assertIn("Address = 10.66.0.2/32", config)
        self.assertIn("PersistentKeepalive = 25", config)

    def test_invalid_key_endpoint_and_client_ranges_are_rejected(self):
        bad = [
            spec(server_public_key="not-base64"),
            spec(endpoint="0.0.0.0:51820"),
            spec(endpoint="vpn host:51820"),
            spec(client_ip="10.66.0.1/32"),
            spec(client_ip="10.66.0.0/24"),
            spec(client_ip="10.67.0.2/32"),
        ]
        for candidate in bad:
            with self.assertRaises(ValueError):
                candidate.validated()

    def test_bundle_qr_roundtrip_and_public_enrollment_separation(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_peer_") as tmp:
            target = pathlib.Path(tmp) / "bundle"
            result = build_bundle(spec(), target, private_bytes=PRIVATE_BYTES)
            config_path = target / "FreeFlexVPN-light-01.conf"
            qr_path = target / "FreeFlexVPN-light-01-QR.png"
            config = config_path.read_text(encoding="utf-8")
            self.assertIn(PRIVATE_B64, config)
            qr_image = cv2.imdecode(np.frombuffer(qr_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
            decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(qr_image)
            self.assertIsNotNone(points)
            self.assertEqual(decoded, config)
            public_text = (target / "enrollment.json").read_text(encoding="utf-8") + (target / "SERVER_COMMANDS.txt").read_text(encoding="utf-8")
            self.assertNotIn(PRIVATE_B64, public_text)
            self.assertIn(result["client_public_key"], public_text)
            self.assertFalse(result["private_material_in_project"])

    def test_bundle_manifest_hashes_every_pre_manifest_file(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_peer_") as tmp:
            target = pathlib.Path(tmp) / "bundle"
            build_bundle(spec(), target, private_bytes=PRIVATE_BYTES)
            manifest = json.loads((target / "BUNDLE_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 5)
            for name, record in manifest.items():
                raw = (target / name).read_bytes()
                self.assertEqual(record["bytes"], len(raw))
                self.assertEqual(record["sha256"], hashlib.sha256(raw).hexdigest().upper())

    def test_existing_or_project_internal_output_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_peer_") as tmp:
            with self.assertRaises(FileExistsError):
                build_bundle(spec(), pathlib.Path(tmp), private_bytes=PRIVATE_BYTES)
        with self.assertRaises(ValueError):
            build_bundle(spec(), ROOT / "60_OUTPUTS" / "must-not-exist", private_bytes=PRIVATE_BYTES)

    def test_two_live_key_generations_are_unique(self):
        first = generate_keypair()
        second = generate_keypair()
        self.assertNotEqual(first, second)

    def test_three_random_key_qrs_roundtrip(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_peer_") as tmp:
            root = pathlib.Path(tmp)
            for index in range(3):
                target = root / f"bundle-{index}"
                result = build_bundle(spec(name=f"random-{index}"), target)
                self.assertTrue(result["qr_payload_match"])

    def test_cli_stdout_does_not_contain_private_material(self):
        with tempfile.TemporaryDirectory(prefix="ffvpn_peer_") as tmp:
            target = pathlib.Path(tmp) / "bundle"
            proc = subprocess.run(
                [
                    sys.executable, str(ROOT / "70_TOOLS" / "issue_peer_bundle.py"),
                    "--name", "cli-01", "--server-public-key", SERVER_KEY,
                    "--endpoint", "198.51.100.20:51820", "--client-ip", "10.66.0.3/32",
                    "--output-dir", str(target),
                ],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            config = (target / "FreeFlexVPN-cli-01.conf").read_text(encoding="utf-8")
            private_line = next(line for line in config.splitlines() if line.startswith("PrivateKey = "))
            private_value = private_line.split(" = ", 1)[1]
            self.assertNotIn(private_value, proc.stdout + proc.stderr)
            report = json.loads(proc.stdout.splitlines()[0])
            self.assertFalse(report["private_material_in_project"])
            self.assertTrue(report["qr_payload_match"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PeerBundleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"피어 묶음 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
