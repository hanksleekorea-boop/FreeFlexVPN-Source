#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.collaboration_runtime import (  # noqa: E402
    GitHubIntegrationBroker, SessionWorktreeManager, SignedDriveOutbox,
)
from app.collaboration_workspace import SafeWorkspace, WorkspaceError  # noqa: E402


REPOSITORY = "hanksleekorea-boop/FreeFlexVPN-Source"


def run(root: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=True,
    )
    return completed.stdout.strip()


class CollaborationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_collab_runtime_")
        self.root = pathlib.Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        run(self.source, "init")
        run(self.source, "config", "user.name", "Owner")
        run(self.source, "config", "user.email", "owner@invalid")
        run(self.source, "config", "core.autocrlf", "false")
        (self.source / "20_SRC" / "app").mkdir(parents=True)
        (self.source / "20_SRC" / "app" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        run(self.source, "add", ".")
        run(self.source, "commit", "-m", "baseline")
        run(self.source, "branch", "-M", "shared-development")
        run(self.source, "remote", "add", "origin", f"https://github.com/{REPOSITORY}.git")
        head = run(self.source, "rev-parse", "HEAD")
        run(self.source, "update-ref", "refs/remotes/origin/shared-development", head)

    def tearDown(self):
        self.temp.cleanup()

    def test_each_session_gets_stable_isolated_worktree(self):
        manager = SessionWorktreeManager(
            self.source, self.root / "sessions", REPOSITORY,
            base_ref="origin/shared-development",
        )
        first = manager.workspace_for("a" * 40)
        same = manager.workspace_for("a" * 40)
        second = manager.workspace_for("b" * 40)
        self.assertEqual(first.root, same.root)
        self.assertNotEqual(first.root, second.root)
        self.assertRegex(first.session_branch, r"^ai-session/[a-f0-9]{20}$")
        self.assertEqual(first.read("20_SRC/app/sample.py")["content"].replace("\r\n", "\n"), "VALUE = 1\n")
        self.assertEqual(run(first.root, "branch", "--show-current"), first.session_branch)

    def test_github_broker_uses_non_force_push_and_fixed_pr_base(self):
        branch = "ai-session/" + "c" * 20
        run(self.source, "branch", "-M", branch)
        workspace = SafeWorkspace(self.source, branch)
        commands: list[tuple[str, ...]] = []

        def fake(command, cwd, timeout):
            commands.append(tuple(command))
            if tuple(command[:3]) == ("git", "status", "--porcelain"):
                return subprocess.CompletedProcess(command, 0, "", "")
            if tuple(command[:3]) == ("git", "rev-parse", "HEAD"):
                return subprocess.CompletedProcess(command, 0, "d" * 40 + "\n", "")
            if tuple(command[:2]) == ("git", "push"):
                return subprocess.CompletedProcess(command, 0, "pushed\n", "")
            return subprocess.CompletedProcess(
                command, 0, f"https://github.com/{REPOSITORY}/pull/42\n", "",
            )

        broker = GitHubIntegrationBroker(
            repository=REPOSITORY, integration_branch="shared-development", runner=fake,
        )
        result = broker.request(
            workspace, operation_id="integration.request.0001", title="Improve collaboration runtime",
        )
        push = next(command for command in commands if command[:2] == ("git", "push"))
        pr = next(command for command in commands if command[:3] == ("gh", "pr", "create"))
        self.assertNotIn("--force", push)
        self.assertIn(f"HEAD:refs/heads/{branch}", push)
        self.assertEqual(pr[pr.index("--base") + 1], "shared-development")
        self.assertEqual(result["pull_request_number"], 42)
        self.assertFalse(result["force_push"])

    def test_drive_outbox_is_idempotent_and_requires_signed_readback(self):
        key = b"k" * 32
        outbox = SignedDriveOutbox(self.root / "drive-outbox", key)
        payload = {"event": "integration_requested", "commit_sha": "e" * 40}
        first = outbox.enqueue("drive.update.0001", payload)
        second = outbox.enqueue("drive.update.0001", payload)
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        body = {
            "operation_id": "drive.update.0001", "readback_verified": True,
            "content_digest": hashlib.sha256(b"drive-content").hexdigest(),
        }
        signature = hmac.new(
            key, json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        verified = outbox.verify_receipt({**body, "signature": signature})
        duplicate = outbox.verify_receipt({**body, "signature": signature})
        self.assertEqual(verified["drive_update_gate"], "verified")
        self.assertFalse(verified["deduplicated"])
        self.assertTrue(duplicate["deduplicated"])
        with self.assertRaises(WorkspaceError) as caught:
            outbox.verify_receipt({**body, "signature": "0" * 64})
        self.assertEqual(caught.exception.code, "INVALID_DRIVE_RECEIPT")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollaborationRuntimeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"공동개발 런타임 검사 {passed}/{result.testsRun} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
