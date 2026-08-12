#!/usr/bin/env python3
"""AI 인계 생성기의 깨끗한 기준점·민감 로컬 상태 제외 계약 검사."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("create_ai_handoff", ROOT / "70_TOOLS" / "create_ai_handoff.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

MANIFEST_SPEC = importlib.util.spec_from_file_location("make_manifest", ROOT / "70_TOOLS" / "make_manifest.py")
assert MANIFEST_SPEC and MANIFEST_SPEC.loader
MANIFEST_MODULE = importlib.util.module_from_spec(MANIFEST_SPEC)
MANIFEST_SPEC.loader.exec_module(MANIFEST_MODULE)


class AiHandoffTests(unittest.TestCase):
    def test_device_local_and_active_lock_paths_are_excluded(self):
        excluded = (
            pathlib.Path(".project-continuity/local/EVIDENCE.jsonl"),
            pathlib.Path(".project-continuity/LOCK.json"),
            pathlib.Path(".project-continuity/LOCK.worker.json"),
            pathlib.Path(".tools/platform-tools.zip"),
            pathlib.Path("debug.log"),
            pathlib.Path("inst_user_settings.tmp"),
            pathlib.Path("60_OUTPUTS/AI_HANDOFF_CURRENT/old.zip"),
        )
        for relative in excluded:
            with self.subTest(relative=relative):
                self.assertTrue(MODULE.is_excluded(relative))

    def test_project_source_and_handoff_ledgers_remain_included(self):
        included = (
            pathlib.Path("20_SRC/app/control_api.py"),
            pathlib.Path(".project-continuity/STATE.md"),
            pathlib.Path(".project-continuity/HISTORY.md"),
            pathlib.Path("00_START/DEVELOPMENT_DASHBOARD.md"),
            pathlib.Path("90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v4.0_2026-08-06.md"),
        )
        for relative in included:
            with self.subTest(relative=relative):
                self.assertFalse(MODULE.is_excluded(relative))

    def test_selected_source_is_only_tracked_and_excludes_current_outputs(self):
        if not MODULE.git_metadata_available():
            with self.assertRaisesRegex(RuntimeError, "Git metadata is required"):
                MODULE.selected_source_paths()
            return
        selected = {path.relative_to(ROOT).as_posix() for path in MODULE.selected_source_paths()}
        tracked = set(MODULE.run("git", "ls-files", "-z").split("\0"))
        self.assertTrue(selected)
        self.assertTrue(selected <= tracked)
        self.assertFalse(any(path.startswith("60_OUTPUTS/AI_HANDOFF_CURRENT/") for path in selected))
        self.assertFalse(any(path.startswith(".project-continuity/LOCK") for path in selected))

    def test_manifest_inventory_matches_handoff_source_policy(self):
        if not MODULE.git_metadata_available():
            self.assertTrue((ROOT / "MANIFEST.md").is_file())
            return
        selected = {path.relative_to(ROOT).as_posix() for path in MODULE.selected_source_paths()}
        inventory = {path.as_posix() for path in MANIFEST_MODULE.files(ROOT)} | {"MANIFEST.md"}
        self.assertEqual(selected, inventory)

    def test_latest_regression_is_read_from_dashboard(self):
        summary = MODULE.latest_regression_summary()
        self.assertRegex(summary, r"전체 회귀 \d+/\d+ 파일·\d+/\d+ 항목 통과")

    def test_obsolete_dirty_release_claims_are_removed(self):
        source = (ROOT / "70_TOOLS" / "create_ai_handoff.py").read_text(encoding="utf-8")
        self.assertNotIn("그 위의 미저장 변경을 함께 담습니다", source)
        self.assertNotIn("GitHub Release와 새 PC 독립 재현은 아직 검증하지 않았습니다", source)
        self.assertIn("ahead/behind 0/0", source)

    def test_https_and_ssh_remotes_map_to_fixed_release_url(self):
        tag = "handoff-20260812T000000Z-abc1234"
        expected = f"https://github.com/example/FreeFlexVPN-Source/releases/tag/{tag}"
        self.assertEqual(MODULE.github_release_url("https://github.com/example/FreeFlexVPN-Source.git", tag), expected)
        self.assertEqual(MODULE.github_release_url("git@github.com:example/FreeFlexVPN-Source.git", tag), expected)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AiHandoffTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"AI 인계 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
