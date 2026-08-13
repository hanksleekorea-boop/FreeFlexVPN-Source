#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.collaboration_workspace import SafeWorkspace, WorkspaceError  # noqa: E402


def run(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=True,
    )
    return completed.stdout.strip()


class CollaborationWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ffvpn_workspace_")
        self.root = pathlib.Path(self.temp.name)
        run(self.root, "init")
        run(self.root, "config", "user.name", "Session Worker")
        run(self.root, "config", "user.email", "session-worker")
        run(self.root, "config", "core.autocrlf", "false")
        (self.root / "20_SRC" / "app").mkdir(parents=True)
        (self.root / "40_TESTS").mkdir()
        (self.root / ".github").mkdir()
        (self.root / ".project-continuity").mkdir()
        (self.root / "20_SRC" / "app" / "sample.py").write_bytes(b"VALUE = 1\n")
        (self.root / "README.md").write_bytes(b"FreeFlexVPN sample\n")
        (self.root / ".github" / "workflows.yml").write_bytes(b"protected\n")
        (self.root / ".project-continuity" / "STATE.md").write_bytes(b"owner only\n")
        run(self.root, "add", ".")
        run(self.root, "commit", "-m", "baseline")
        run(self.root, "branch", "-M", "ai-session/test/task")
        self.workspace = SafeWorkspace(self.root, "ai-session/test/task")

    def tearDown(self):
        self.temp.cleanup()

    def test_read_search_write_diff_commit_round_trip(self):
        read = self.workspace.read("20_SRC/app/sample.py")
        searched = self.workspace.search("FreeFlexVPN")
        written = self.workspace.write(
            "20_SRC/app/sample.py", "VALUE = 2\n",
            expected_revision=read["revision"], operation_id="write.roundtrip.1",
        )
        diff = self.workspace.diff()
        committed = self.workspace.commit("Update sample value", ["20_SRC/app/sample.py"])
        self.assertEqual(read["content"], "VALUE = 1\n")
        self.assertEqual(searched["matches"][0]["path"], "README.md")
        self.assertTrue(written["changed"])
        self.assertIn("+VALUE = 2", diff["diff"])
        self.assertEqual(len(committed["commit_sha"]), 40)
        self.assertEqual(run(self.root, "status", "--porcelain"), "")

    def test_stale_revision_preserves_newer_content(self):
        read = self.workspace.read("20_SRC/app/sample.py")
        (self.root / "20_SRC" / "app" / "sample.py").write_text("OTHER = 3\n", encoding="utf-8")
        with self.assertRaises(WorkspaceError) as caught:
            self.workspace.write(
                "20_SRC/app/sample.py", "VALUE = 9\n",
                expected_revision=read["revision"], operation_id="write.stale.1",
            )
        self.assertEqual(caught.exception.code, "STALE_REVISION")
        self.assertEqual((self.root / "20_SRC" / "app" / "sample.py").read_text(), "OTHER = 3\n")

    def test_traversal_owner_paths_binary_large_and_secret_input_are_blocked(self):
        empty = hashlib.sha256(b"").hexdigest()
        cases = (
            ("../outside.txt", "plain", "INVALID_PATH"),
            (".github/workflows.yml", "plain", "PATH_FORBIDDEN"),
            (".project-continuity/STATE.md", "plain", "PATH_FORBIDDEN"),
            ("20_SRC/app/key.txt", "api_key=abcdefghijklmnopqrstuvwxyz123456", "SECRET_INPUT_BLOCKED"),
        )
        for path, content, code in cases:
            with self.assertRaises(WorkspaceError) as caught:
                self.workspace.write(path, content, expected_revision=empty, operation_id="write.blocked.1")
            self.assertEqual(caught.exception.code, code)

    def test_arbitrary_check_is_rejected(self):
        with self.assertRaises(WorkspaceError) as caught:
            self.workspace.run_check("shell", python_executable=sys.executable)
        self.assertEqual(caught.exception.code, "CHECK_NOT_ALLOWED")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollaborationWorkspaceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공동개발 작업공간 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
