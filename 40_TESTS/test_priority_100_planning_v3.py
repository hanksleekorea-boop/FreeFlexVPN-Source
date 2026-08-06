"""Structural checks for the v3 product and execution planning artifacts."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "10_STATE"
CATALOG = STATE / "PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md"
PRODUCT = STATE / "APP_SERVICE_PLAN_v3.0_2026-08-05.md"
EXECUTION = STATE / "DEV_EXECUTION_PLAN_v3.0_2026-08-05.md"


class Priority100PlanningV3Tests(unittest.TestCase):
    def test_all_new_artifacts_exist(self):
        for path in (CATALOG, PRODUCT, EXECUTION):
            self.assertTrue(path.is_file(), path)

    def test_catalog_has_each_priority_exactly_once(self):
        text = CATALOG.read_text(encoding="utf-8")
        found = re.findall(r"\| (P[0-4]-\d{2,3}) \|", text)
        expected = [f"P{band}-{number:02d}" for band, numbers in (
            (0, range(1, 11)), (1, range(11, 26)), (2, range(26, 41)),
            (3, range(41, 51)), (4, range(51, 101)),
        ) for number in numbers]
        self.assertEqual(found, expected)

    def test_product_and_execution_link_the_catalog_and_legacy_plans(self):
        product = PRODUCT.read_text(encoding="utf-8")
        execution = EXECUTION.read_text(encoding="utf-8")
        self.assertIn("PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md", product)
        self.assertIn("PRODUCT_UX_100_PRIORITY_CATALOG_v3.0_2026-08-05.md", execution)
        self.assertIn("APP_SERVICE_PLAN_v2.0_2026-08-01.md", product)
        self.assertIn("DEV_EXECUTION_PLAN_v2.0_2026-08-01.md", execution)

    def test_execution_has_release_trains_and_priority_boundaries(self):
        text = EXECUTION.read_text(encoding="utf-8")
        for train in ("T0-A", "T0-B", "T1-A", "T1-B", "T2-A", "T2-B", "T3-A", "T3-B", "T3-C", "T4-A", "T4-B", "T5-A", "T5-B"):
            self.assertIn(train, text)
        for token in ("P0-01", "P1-11~18", "P2-33~38", "P3-41~45", "P4-89", "P4-100"):
            self.assertIn(token, text)

    def test_honest_state_and_approval_boundaries_are_explicit(self):
        joined = PRODUCT.read_text(encoding="utf-8") + EXECUTION.read_text(encoding="utf-8")
        for phrase in ("확인 불가", "활성 WireGuard 세션", "실기기 확인 전", "명시 승인", "실제처럼"):
            self.assertIn(phrase, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
