import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "10_PLAN" / "CURRENT_SERVICE_PLAN.md"
DEVELOPMENT = ROOT / "10_PLAN" / "CURRENT_DEVELOPMENT_EXECUTION_PLAN.md"
START = ROOT / "00_START" / "시작하세요.md"
DASHBOARD = ROOT / "00_START" / "DEVELOPMENT_DASHBOARD.md"
DECISIONS = ROOT / "10_STATE" / "DECISIONS.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_task_rows(text: str):
    pattern = re.compile(
        r"^\| (TASK-[123]-\d{3}) [^|]+\| (REQ-\d{3}) \| ([^|]+) \| "
        r"(READY|PLANNED|WAITING-EXTERNAL) \|",
        re.MULTILINE,
    )
    return [(task, req, pred.strip(), status) for task, req, pred, status in pattern.findall(text)]


def dependency_errors(rows):
    ids = [row[0] for row in rows]
    known = set(ids)
    errors = []
    for index, (task, _req, predecessor, _status) in enumerate(rows):
        expected = "없음" if index == 0 else ids[index - 1]
        if predecessor == task:
            errors.append(f"self:{task}")
        if predecessor != "없음" and predecessor not in known:
            errors.append(f"missing:{task}->{predecessor}")
        if predecessor != expected:
            errors.append(f"order:{task}->{predecessor}!={expected}")
    return errors


class CanonicalPlanIntegrationTest(unittest.TestCase):
    def test_service_has_exact_requirement_set(self):
        text = read(SERVICE)
        reqs = re.findall(r"^\| (REQ-\d{3}) \|", text, re.MULTILINE)
        expected = [f"REQ-{number:03d}" for number in range(1, 29)]
        self.assertEqual(reqs, expected)
        self.assertIn("최종 통합일: 2026-08-25", text)
        self.assertIn("Gap-Compression v3", text)
        self.assertIn("이 파일만 현재 제품 기획 정본", text)
        self.assertIn("integrated-product-spec-vNEXT.md", text)

    def test_development_has_exact_order_without_cycles(self):
        text = read(DEVELOPMENT)
        rows = parse_task_rows(text)
        expected_tasks = (
            [f"TASK-1-{number:03d}" for number in range(1, 15)]
            + [f"TASK-2-{number:03d}" for number in range(1, 10)]
            + [f"TASK-3-{number:03d}" for number in range(1, 6)]
        )
        self.assertEqual([row[0] for row in rows], expected_tasks)
        self.assertEqual([row[1] for row in rows], [f"REQ-{number:03d}" for number in range(1, 29)])
        self.assertEqual(dependency_errors(rows), [])
        self.assertIn("최종 통합일: 2026-08-25", text)
        self.assertIn("Gap-Compression v3", text)
        self.assertIn("이 파일만 현재 상세 개발실행계획 정본", text)
        self.assertIn("detailed-development-plan-vNEXT.md", text)

    def test_negative_dependency_controls_reject_bad_rows(self):
        rows = parse_task_rows(read(DEVELOPMENT))
        self_ref = list(rows)
        task, req, _pred, status = self_ref[15]
        self_ref[15] = (task, req, task, status)
        self.assertTrue(any(item.startswith("self:") for item in dependency_errors(self_ref)))

        missing = list(rows)
        task, req, _pred, status = missing[23]
        missing[23] = (task, req, "TASK-2-010", status)
        self.assertTrue(any(item.startswith("missing:") for item in dependency_errors(missing)))

    def test_all_canonical_pointers_agree(self):
        start = read(START)
        dashboard = read(DASHBOARD)
        decisions = read(DECISIONS)
        for name in ("CURRENT_SERVICE_PLAN.md", "CURRENT_DEVELOPMENT_EXECUTION_PLAN.md"):
            self.assertIn(name, start)
            self.assertIn(name, dashboard)
        self.assertIn("D67", decisions)
        self.assertIn("REQ-001~028", decisions)
        self.assertIn("TASK 28개", decisions)
        self.assertIn("정본 기준: 2026-08-25 Gap-Compression v3", dashboard)


if __name__ == "__main__":
    unittest.main()
