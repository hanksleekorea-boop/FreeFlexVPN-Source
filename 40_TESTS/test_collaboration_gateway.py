#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.collaboration_gateway import (  # noqa: E402
    CollaborationGateway, GatewayError, ProjectContext,
)


NOW = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
PASSWORD = "correct horse battery staple 2026"
SHA = "a" * 40
DIGEST = "b" * 64


class FakeBroker:
    calls = 0

    def deploy(self, **kwargs):
        self.calls += 1
        return {
            "status": "succeeded", "provider_deployment_id": "opaque-deployment",
            "release_revision": "revision-1", "served_identity_verified": True,
            "critical_probes_passed": True,
        }


class CollaborationGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_collaboration_")
        self.path = pathlib.Path(self.temp.name) / "gateway.sqlite3"
        self.context = ProjectContext(
            project_id="freeflexvpn",
            project_name="FreeFlexVPN",
            repository="hanksleekorea-boop/FreeFlexVPN-Source",
            production_branch="feature/pc-commercial-readiness-90",
            integration_branch="shared-development",
            production_environment="gcs-existing-production",
            production_url="https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
        )
        self.gateway = CollaborationGateway(
            self.path, context=self.context, bootstrap_password=PASSWORD,
        )

    def tearDown(self):
        self.temp.cleanup()

    def login(self):
        return self.gateway.login(PASSWORD, client_hint="test-client", now=NOW).body

    def test_password_session_and_csrf_are_only_hashed_at_rest(self):
        session = self.login()
        raw = self.path.read_bytes()
        self.assertNotIn(PASSWORD.encode(), raw)
        self.assertNotIn(session["session_token"].encode(), raw)
        self.assertNotIn(session["csrf_token"].encode(), raw)
        self.assertEqual(session["role"], "participant")
        self.assertEqual(session["project"]["context_fingerprint"], self.context.fingerprint)

    def test_wrong_password_never_echoes_and_rate_limits(self):
        for index in range(5):
            with self.assertRaises(GatewayError) as caught:
                self.gateway.login("wrong password value", client_hint="same-client", now=NOW + timedelta(seconds=index))
            self.assertNotIn("wrong", str(caught.exception))
        with self.assertRaises(GatewayError) as blocked:
            self.gateway.login(PASSWORD, client_hint="same-client", now=NOW + timedelta(seconds=6))
        self.assertEqual(blocked.exception.status, 429)

    def test_session_expires_after_fifteen_minutes(self):
        session = self.login()
        ok = self.gateway.status(session["session_token"], now=NOW + timedelta(minutes=14))
        self.assertEqual(ok.status, 200)
        with self.assertRaises(GatewayError):
            self.gateway.status(session["session_token"], now=NOW + timedelta(minutes=15))

    def test_prepare_requires_csrf_exact_context_verified_main_and_signed_artifact(self):
        session = self.login()
        base = {
            "operation_id": "deploy.prepare.0001",
            "candidate_sha": SHA,
            "production_head": SHA,
            "artifact_digest": DIGEST,
            "artifact_signature_valid": True,
            "ci_status": "success",
            "environment": self.context.production_environment,
            "context_fingerprint": self.context.fingerprint,
            "config_revision": "cfg-1",
            "side_effect_class": "NONE",
        }
        for changed, code in (
            ({"candidate_sha": "c" * 40}, "UNVERIFIED_MAIN_SHA"),
            ({"ci_status": "failure"}, "RELEASE_GATES_FAILED"),
            ({"artifact_signature_valid": False}, "RELEASE_GATES_FAILED"),
            ({"environment": "other"}, "ENVIRONMENT_MISMATCH"),
            ({"context_fingerprint": "0" * 64}, "CONTEXT_MISMATCH"),
            ({"side_effect_class": "PRIVILEGED"}, "OWNER_SPECIAL_RELEASE_ONLY"),
        ):
            body = {**base, **changed, "operation_id": "deploy." + code.lower()}
            with self.assertRaises(GatewayError) as caught:
                self.gateway.prepare_deployment(
                    session["session_token"], session["csrf_token"], body, now=NOW
                )
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(GatewayError) as csrf:
            self.gateway.prepare_deployment(session["session_token"], "wrong", base, now=NOW)
        self.assertEqual(csrf.exception.code, "CSRF_REQUIRED")

    def test_release_broker_absence_fails_closed(self):
        session = self.login()
        body = {
            "operation_id": "deploy.prepare.closed",
            "candidate_sha": SHA, "production_head": SHA,
            "artifact_digest": DIGEST, "artifact_signature_valid": True,
            "ci_status": "success", "environment": self.context.production_environment,
            "context_fingerprint": self.context.fingerprint, "config_revision": "cfg-1",
            "side_effect_class": "NONE",
        }
        with self.assertRaises(GatewayError) as caught:
            self.gateway.prepare_deployment(
                session["session_token"], session["csrf_token"], body, now=NOW
            )
        self.assertEqual(caught.exception.code, "DEPLOY_BROKER_UNAVAILABLE")
        with self.assertRaises(ValueError):
            self.gateway.set_participant_deploy_enabled(True)

    def test_prepare_execute_rechecks_every_binding_and_deduplicates_release(self):
        broker = FakeBroker()
        gateway = CollaborationGateway(
            pathlib.Path(self.temp.name) / "release.sqlite3",
            context=self.context, bootstrap_password=PASSWORD, release_broker=broker,
        )
        gateway.set_participant_deploy_enabled(True)
        session = gateway.login(PASSWORD, client_hint="release-client", now=NOW).body
        prepared = gateway.prepare_deployment(
            session["session_token"], session["csrf_token"], {
                "operation_id": "deploy.prepare.release1", "candidate_sha": SHA,
                "production_head": SHA, "artifact_digest": DIGEST,
                "artifact_signature_valid": True, "ci_status": "success",
                "environment": self.context.production_environment,
                "context_fingerprint": self.context.fingerprint, "config_revision": "cfg-1",
                "side_effect_class": "NONE",
            }, now=NOW,
        ).body
        execute = {
            "operation_id": "deploy.execute.release1",
            "prepare_token": prepared["prepare_token"],
            "current_production_head": SHA, "current_artifact_digest": DIGEST,
            "current_config_revision": "cfg-1", "context_fingerprint": self.context.fingerprint,
            "environment": self.context.production_environment,
        }
        stale = dict(execute, operation_id="deploy.execute.stale", current_production_head="c" * 40)
        with self.assertRaises(GatewayError) as caught:
            gateway.execute_deployment(
                session["session_token"], session["csrf_token"], prepared["deployment_id"], stale, now=NOW
            )
        self.assertEqual(caught.exception.code, "PREPARATION_STALE")
        first = gateway.execute_deployment(
            session["session_token"], session["csrf_token"], prepared["deployment_id"], execute, now=NOW
        )
        repeated = gateway.execute_deployment(
            session["session_token"], session["csrf_token"], prepared["deployment_id"], execute, now=NOW
        )
        self.assertEqual(first.status, 200)
        self.assertTrue(first.body["served_identity_verified"])
        self.assertEqual(repeated.body, first.body)
        self.assertEqual(broker.calls, 1)

    def test_unknown_provider_result_freezes_preparation(self):
        class UnknownBroker:
            def deploy(self, **kwargs): return {"status": "unknown"}
        gateway = CollaborationGateway(
            pathlib.Path(self.temp.name) / "unknown.sqlite3", context=self.context,
            bootstrap_password=PASSWORD, release_broker=UnknownBroker(),
        )
        gateway.set_participant_deploy_enabled(True)
        session = gateway.login(PASSWORD, client_hint="unknown-client", now=NOW).body
        prepared = gateway.prepare_deployment(
            session["session_token"], session["csrf_token"], {
                "operation_id": "deploy.prepare.unknown1", "candidate_sha": SHA,
                "production_head": SHA, "artifact_digest": DIGEST,
                "artifact_signature_valid": True, "ci_status": "success",
                "environment": self.context.production_environment,
                "context_fingerprint": self.context.fingerprint, "config_revision": "cfg-1",
                "side_effect_class": "NONE",
            }, now=NOW,
        ).body
        with self.assertRaises(GatewayError) as caught:
            gateway.execute_deployment(
                session["session_token"], session["csrf_token"], prepared["deployment_id"], {
                    "operation_id": "deploy.execute.unknown1", "prepare_token": prepared["prepare_token"],
                    "current_production_head": SHA, "current_artifact_digest": DIGEST,
                    "current_config_revision": "cfg-1", "context_fingerprint": self.context.fingerprint,
                    "environment": self.context.production_environment,
                }, now=NOW,
            )
        self.assertEqual(caught.exception.code, "DEPLOYMENT_UNKNOWN")

    def test_restart_requires_same_password_and_project(self):
        CollaborationGateway(self.path, context=self.context, bootstrap_password=PASSWORD)
        with self.assertRaises(ValueError):
            CollaborationGateway(self.path, context=self.context, bootstrap_password="different password 123")
        other = ProjectContext(**{**self.context.__dict__, "project_id": "another-project"})
        with self.assertRaises(ValueError):
            CollaborationGateway(self.path, context=other, bootstrap_password=PASSWORD)

    def test_revoke_all_requires_target_bound_confirmation_and_invalidates_sessions(self):
        session = self.login()
        with self.assertRaises(GatewayError):
            self.gateway.revoke_all(context_fingerprint=self.context.fingerprint, confirmation="REVOKE")
        result = self.gateway.revoke_all(
            context_fingerprint=self.context.fingerprint,
            confirmation="REVOKE ALL freeflexvpn", now=NOW,
        )
        self.assertEqual(result["revoked_sessions"], 1)
        self.assertTrue(result["owner_access_preserved"])
        with self.assertRaises(GatewayError):
            self.gateway.status(session["session_token"], now=NOW)

    def test_database_contains_no_account_email_ip_or_provider_secret_columns(self):
        with closing(sqlite3.connect(self.path)) as connection:
            columns = []
            for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                columns.extend(row[1] for row in connection.execute(f"PRAGMA table_info({name})"))
        joined = " ".join(columns).lower()
        for forbidden in ("email", "password_plain", "token_plain", "remote_ip", "provider_secret"):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollaborationGatewayTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공동개발 게이트웨이 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
