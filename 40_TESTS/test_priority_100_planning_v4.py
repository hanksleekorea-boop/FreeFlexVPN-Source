"""Contract checks for the feature-first v4 planning artifacts."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "10_STATE"
ARCHIVE = ROOT / "90_ARCHIVE" / "10_STATE_plans"
CATALOG = STATE / "PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md"
ROADMAP = STATE / "FEATURE_FIRST_ROADMAP_100_v4.0_2026-08-06.md"
PRODUCT = ARCHIVE / "APP_SERVICE_PLAN_v4.0_2026-08-06.md"
EXECUTION = ARCHIVE / "DEV_EXECUTION_PLAN_v4.0_2026-08-06.md"


def expected_ids():
    return [
        *(f"P0-{n:02d}" for n in range(1, 11)),
        *(f"P1-{n:02d}" for n in range(11, 26)),
        *(f"P2-{n:02d}" for n in range(26, 41)),
        *(f"P3-{n:02d}" for n in range(41, 51)),
        *(f"P4-{n:02d}" for n in range(51, 100)),
        "P4-100",
    ]


def expand_ranges(text):
    expanded = []
    for band1, start, band2, end in re.findall(r"(P[0-4])-(\d{2,3})~(P[0-4])-(\d{2,3})", text):
        if band1 != band2:
            raise AssertionError(f"cross-band range is invalid: {band1}-{start}~{band2}-{end}")
        expanded.extend(f"{band1}-{number:02d}" if number < 100 else f"{band1}-100" for number in range(int(start), int(end) + 1))
    return expanded


class FeatureFirstPlanningV4Tests(unittest.TestCase):
    def test_all_artifacts_exist(self):
        for path in (CATALOG, ROADMAP, PRODUCT, EXECUTION):
            self.assertTrue(path.is_file(), path)

    def test_catalog_still_contains_exactly_100_requirements(self):
        found = re.findall(r"\| (P[0-4]-\d{2,3}) \|", CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(found, expected_ids())

    def test_roadmap_assigns_all_100_once_in_priority_order(self):
        table = ROADMAP.read_text(encoding="utf-8").split("## 4.", 1)[0]
        self.assertEqual(expand_ranges(table), expected_ids())

    def test_twenty_work_packages_are_present_and_ordered(self):
        text = ROADMAP.read_text(encoding="utf-8")
        expected = [
            "F0-1", "F0-2", "F1-1", "F1-2", "F1-3", "F2-1", "F2-2", "F2-3",
            "F3-1", "F3-2", "F4-1", "F4-2", "F4-3", "F4-4", "F5-1", "F5-2",
            "F5-3", "F5-4", "F6-1", "F6-2",
        ]
        positions = [text.index(f"| {number} | {name} ") for number, name in enumerate(expected, 1)]
        self.assertEqual(positions, sorted(positions))

    def test_new_features_are_explicitly_ahead_of_legacy_work(self):
        joined = PRODUCT.read_text(encoding="utf-8") + EXECUTION.read_text(encoding="utf-8")
        for phrase in (
            "PARKED_AFTER_F6",
            "기존 대기 작업보다 앞선",
            "마케팅·장식·수익화",
            "보안·개인정보·전면 장애",
        ):
            self.assertIn(phrase, joined)

    def test_honesty_and_approval_boundaries_remain(self):
        joined = PRODUCT.read_text(encoding="utf-8") + EXECUTION.read_text(encoding="utf-8")
        for phrase in (
            "활성 WireGuard 세션",
            "iPhone 실기기",
            "확인 불가",
            "실제 IP",
            "배포 승인",
            "다섯 상태",
        ):
            self.assertIn(phrase, joined)

    def test_execution_has_detail_for_every_work_package(self):
        text = EXECUTION.read_text(encoding="utf-8")
        expected = (
            "F0-1", "F0-2", "F1-1", "F1-2", "F1-3", "F2-1", "F2-2", "F2-3",
            "F3-1", "F3-2", "F4-1", "F4-2", "F4-3", "F4-4", "F5-1", "F5-2",
            "F5-3", "F5-4", "F6-1", "F6-2",
        )
        for package in expected:
            self.assertRegex(text, rf"#### {re.escape(package)} · P[0-4]-")


if __name__ == "__main__":
    unittest.main(verbosity=2)
