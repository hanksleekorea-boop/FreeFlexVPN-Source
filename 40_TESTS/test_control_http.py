#!/usr/bin/env python3
"""실제 localhost 소비 방식으로 제어 HTTP 어댑터를 확인한다."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_api import ControlAPI  # noqa: E402
from app.control_http import create_server  # noqa: E402


class ControlHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_control_http_")
        self.api = ControlAPI(pathlib.Path(self.temp.name) / "control.sqlite3")
        self.server = create_server(
            self.api, host="127.0.0.1", port=0,
            allowed_origins={"https://hanksleekorea-boop.github.io"},
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, path, *, method="GET", body=None, origin=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if origin:
            headers["Origin"] = origin
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))

    def test_health_and_catalog_are_real_http_json_with_no_store(self):
        health_status, _, health = self.request("/healthz")
        catalog_status, headers, catalog = self.request("/v1/catalog")
        self.assertEqual(health_status, 200)
        self.assertEqual(health["storage"], "persistent")
        self.assertEqual(catalog_status, 200)
        self.assertEqual(catalog["available_count"], 0)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_allowed_origin_gets_exact_cors_and_unknown_origin_is_rejected(self):
        allowed = "https://hanksleekorea-boop.github.io"
        status, headers, _ = self.request("/v1/catalog", origin=allowed)
        denied_status, denied_headers, denied = self.request("/v1/catalog", origin="https://evil.example")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], allowed)
        self.assertEqual(denied_status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", denied_headers)
        self.assertEqual(denied["error"], "ORIGIN_FORBIDDEN")

    def test_invalid_claim_and_invalid_json_fail_without_secret_echo(self):
        claim_status, _, claim = self.request(
            "/v1/claims/exchange", method="POST", body={"claim": "this-is-not-valid"}
        )
        request = urllib.request.Request(
            self.base + "/v1/claims/exchange",
            data=b"{broken",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        invalid_body = json.loads(caught.exception.read().decode("utf-8"))
        self.assertEqual(claim_status, 401)
        self.assertNotIn("this-is-not-valid", str(claim))
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(invalid_body["error"], "INVALID_JSON")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ControlHTTPTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"제어 HTTP 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
