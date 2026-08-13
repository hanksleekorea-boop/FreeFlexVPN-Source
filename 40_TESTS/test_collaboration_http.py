#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.collaboration_gateway import CollaborationGateway, ProjectContext  # noqa: E402
from app.collaboration_http import create_server  # noqa: E402
from app.collaboration_workspace import SafeWorkspace  # noqa: E402


PASSWORD = "correct horse battery staple 2026"
ORIGIN = "https://collaboration.freeflexvpn.example"


class CollaborationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_collab_http_")
        context = ProjectContext(
            project_id="freeflexvpn", project_name="FreeFlexVPN",
            repository="hanksleekorea-boop/FreeFlexVPN-Source",
            production_branch="feature/pc-commercial-readiness-90",
            integration_branch="shared-development",
            production_environment="gcs-existing-production",
            production_url="https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
        )
        self.gateway = CollaborationGateway(
            pathlib.Path(self.temp.name) / "gateway.sqlite3",
            context=context, bootstrap_password=PASSWORD,
        )
        self.repo = pathlib.Path(self.temp.name) / "repo"
        self.repo.mkdir()
        for args in (
            ("init",), ("config", "user.name", "Session Worker"),
            ("config", "user.email", "session-worker"), ("config", "core.autocrlf", "false"),
        ):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "20_SRC" / "app").mkdir(parents=True)
        (self.repo / "20_SRC" / "app" / "sample.py").write_bytes(b"VALUE = 1\n")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "branch", "-M", "ai-session/http/task"], cwd=self.repo, check=True, capture_output=True)
        workspace = SafeWorkspace(self.repo, "ai-session/http/task")
        self.server = create_server(
            self.gateway,
            portal_path=ROOT / "20_SRC" / "html_templates" / "collaboration_portal.html",
            allowed_origin=ORIGIN, port=0, workspace=workspace,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, path, *, method="GET", body=None, headers=None):
        request_headers = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, method=method, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        payload = json.loads(raw.decode("utf-8")) if "json" in content_type else raw.decode("utf-8")
        return response.status, dict(response.headers), payload

    def login(self):
        status, headers, body = self.request(
            "/api/development/login", method="POST", body={"password": PASSWORD}, headers={"Origin": ORIGIN}
        )
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        return status, headers, body, cookie

    def test_portal_and_health_have_strict_security_headers(self):
        status, headers, portal = self.request("/collaboration")
        script_status, _, script = self.request("/collaboration-portal.js")
        health_status, health_headers, health = self.request("/healthz")
        self.assertEqual(status, 200)
        self.assertIn("FreeFlexVPN 공동개발", portal)
        self.assertEqual(script_status, 200)
        self.assertIn("/api/development/login", script)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(health_status, 200)
        self.assertFalse(health["secrets_exposed"])
        self.assertEqual(health_headers["Cache-Control"], "no-store")

    def test_login_uses_secure_http_only_cookie_and_does_not_return_session_token(self):
        status, headers, body, _ = self.login()
        self.assertEqual(status, 200)
        self.assertNotIn("session_token", body)
        self.assertIn("csrf_token", body)
        for marker in ("HttpOnly", "Secure", "SameSite=Strict", "Max-Age=900"):
            self.assertIn(marker, headers["Set-Cookie"])

    def test_status_requires_cookie_and_unknown_origin_is_denied(self):
        denied, _, body = self.request("/api/development/status", headers={"Origin": "https://evil.example"})
        missing, _, auth = self.request("/api/development/status")
        _, _, _, cookie = self.login()
        ok, _, current = self.request("/api/development/status", headers={"Cookie": cookie, "Origin": ORIGIN})
        self.assertEqual(denied, 403)
        self.assertEqual(body["error"], "ORIGIN_FORBIDDEN")
        self.assertEqual(missing, 401)
        self.assertEqual(auth["error"], "AUTH_REQUIRED")
        self.assertEqual(ok, 200)
        self.assertEqual(current["participant_deploy"], "policy_only")

    def test_deployment_write_requires_csrf_and_unconnected_broker_fails_closed(self):
        _, _, login, cookie = self.login()
        body = {
            "operation_id": "deploy.prepare.http1",
            "candidate_sha": "a" * 40, "production_head": "a" * 40,
            "artifact_digest": "b" * 64, "artifact_signature_valid": True,
            "ci_status": "success", "environment": "gcs-existing-production",
            "context_fingerprint": login["project"]["context_fingerprint"], "config_revision": "cfg-1",
            "side_effect_class": "NONE",
        }
        no_csrf, _, rejected = self.request(
            "/api/development/deployments/prepare", method="POST", body=body,
            headers={"Cookie": cookie, "Origin": ORIGIN},
        )
        blocked, _, unavailable = self.request(
            "/api/development/deployments/prepare", method="POST", body=body,
            headers={"Cookie": cookie, "Origin": ORIGIN, "X-FreeFlex-CSRF": login["csrf_token"]},
        )
        self.assertEqual(no_csrf, 403)
        self.assertEqual(rejected["error"], "CSRF_REQUIRED")
        self.assertEqual(blocked, 503)
        self.assertEqual(unavailable["error"], "DEPLOY_BROKER_UNAVAILABLE")

    def test_machine_manifest_and_password_only_file_round_trip(self):
        manifest_status, _, manifest = self.request("/.well-known/ai-development.json")
        _, _, login, cookie = self.login()
        common = {"Cookie": cookie, "Origin": ORIGIN}
        read_status, _, read = self.request(
            "/api/development/read?path=20_SRC%2Fapp%2Fsample.py", headers=common,
        )
        write_status, _, written = self.request(
            "/api/development/write", method="PUT",
            body={
                "operation_id": "workspace.write.http1", "path": "20_SRC/app/sample.py",
                "content": "VALUE = 2\n", "expected_revision": read["revision"],
            },
            headers={**common, "X-FreeFlex-CSRF": login["csrf_token"]},
        )
        duplicate_status, _, duplicate = self.request(
            "/api/development/write", method="PUT",
            body={
                "operation_id": "workspace.write.http1", "path": "20_SRC/app/sample.py",
                "content": "VALUE = 2\n", "expected_revision": read["revision"],
            },
            headers={**common, "X-FreeFlex-CSRF": login["csrf_token"]},
        )
        diff_status, _, diff = self.request("/api/development/diff", headers=common)
        self.assertEqual(manifest_status, 200)
        self.assertTrue(manifest["capabilities"]["write"])
        self.assertFalse(manifest["capabilities"]["arbitrary_shell"])
        self.assertEqual(read_status, 200)
        self.assertEqual(write_status, 200)
        self.assertEqual(duplicate_status, 200)
        self.assertEqual(duplicate, written)
        self.assertEqual(diff_status, 200)
        self.assertIn("+VALUE = 2", diff["diff"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollaborationHTTPTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공동개발 HTTP 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
