from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "10_PLAN" / "CURRENT_SERVICE_PLAN.md"
INDEX = ROOT / "10_PLAN" / "CURRENT_DEVELOPMENT_EXECUTION_PLAN.md"
DETAIL = ROOT / "10_PLAN" / "DETAILED_DEVELOPMENT_PLAN_GAP_COMPRESSION_v3_2026-08-25.md"
PROPOSAL = ROOT / "10_PLAN" / "FREEFLEXVPN_TOP10_GAP_COMPRESSION_PROPOSAL_v1_2026-08-25.md"
START = ROOT / "00_START" / "시작하세요.md"
DASHBOARD = ROOT / "00_START" / "DEVELOPMENT_DASHBOARD.md"
DECISIONS = ROOT / "10_STATE" / "DECISIONS.md"
RECEIPT = ROOT / "10_STATE" / "GCP_TASK_RECEIPT_TEMPLATE_v3.json"
RECEIPT_001 = ROOT / "10_STATE" / "GCP_TASK_0-01_2026-08-25.json"
RECEIPT_002 = ROOT / "10_STATE" / "GCP_TASK_0-02_2026-08-25.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


EXPECTED_TASKS = (
    [f"GCP-TASK-0-{number:02d}" for number in range(0, 3)]
    + [f"GCP-TASK-1-{number:02d}" for number in range(1, 17)]
    + [f"GCP-TASK-2-{number:02d}" for number in range(1, 8)]
    + [f"GCP-TASK-3-{number:02d}" for number in range(1, 6)]
)


class GapCompressionPlanV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = read(SERVICE)
        cls.index = read(INDEX)
        cls.detail = read(DETAIL)
        cls.proposal = read(PROPOSAL)

    def test_proposal_is_adopted_and_service_is_v3(self) -> None:
        self.assertIn("채택됨 — Gap-Compression v3 정본에 통합", self.proposal)
        self.assertIn("판: Gap-Compression v3", self.service)
        self.assertIn("## 15. Gap-Compression v3 통합·채택", self.service)
        self.assertIn("최신 작업 카드 정본", self.detail)
        self.assertIn(DETAIL.name, self.service)
        self.assertIn(DETAIL.name, self.index)

    def test_seven_programs_and_non_regression_are_explicit(self) -> None:
        for number in range(1, 8):
            self.assertIn(f"GCP-{number}", self.service)
        required = (
            "월 무료 1GB",
            "무기한 충전",
            "공식 WireGuard",
            "기존 `ffvpn`",
            "공개 모바일·PC URL",
            "Kakao Connect",
            "Drive B",
            "자동 갱신",
        )
        for phrase in required:
            self.assertIn(phrase, self.detail)

    def test_exact_task_set_is_unique(self) -> None:
        found = re.findall(r"^### (GCP-TASK-[0-3]-\d{2})\b", self.detail, re.MULTILINE)
        self.assertEqual(EXPECTED_TASKS, found)
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(31, len(found))

    def test_every_task_has_a_status_row(self) -> None:
        rows = re.findall(
            r"^\| (GCP-TASK-[0-3]-\d{2}) \| (READY|PLANNED|IN_PROGRESS|WAITING-EXTERNAL|BLOCKED|DONE-CODE|DONE-VERIFIED) \|",
            self.detail,
            re.MULTILINE,
        )
        self.assertEqual(EXPECTED_TASKS, [task for task, _ in rows])
        self.assertEqual("DONE-CODE", rows[0][1])
        self.assertEqual("DONE-CODE", rows[1][1])
        self.assertEqual("DONE-CODE", rows[2][1])
        self.assertEqual("IN_PROGRESS", rows[3][1])
        self.assertTrue(all(status == "PLANNED" for _, status in rows[4:]))

    def test_low_skill_ai_instructions_are_complete(self) -> None:
        required = (
            "한 번에 여러 카드를 개발하지 않는다",
            "먼저 읽기",
            "수정 허용",
            "일부러 틀린 입력",
            "DONE-CODE",
            "DONE-VERIFIED",
            "작업 영수증",
            "전용 검사",
            "되돌리기",
            "실행하지 않은 검사는 빈 성공값 대신",
        )
        for phrase in required:
            self.assertIn(phrase, self.detail)

    def test_android_and_external_gates_are_honest(self) -> None:
        required = (
            "유휴 기기가 정확히 한 대",
            "0대 또는 2대 이상이면 변경 0",
            "기존 `ffvpn`은 삭제·덮어쓰기하지 않고",
            "실제 시험 거래",
            "운영자·법률/세무 확인",
            "독립 검토자 보고",
            "가상 사용자 증거가 아니다",
        )
        for phrase in required:
            self.assertIn(phrase, self.detail)

    def test_canonical_pointers_and_decision_agree(self) -> None:
        for path in (START, DASHBOARD, DECISIONS):
            text = read(path)
            self.assertIn("Gap-Compression v3", text)
        self.assertIn(DETAIL.name, read(START))
        self.assertIn(DETAIL.name, read(DASHBOARD))
        self.assertIn("D69", read(DECISIONS))

    def test_receipt_template_is_safe(self) -> None:
        data = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual("GCP-TASK-0-00", data["task_id"])
        self.assertEqual("ready", data["status"])
        self.assertTrue(data["non_regression"]["drive_b_unused"])
        text = RECEIPT.read_text(encoding="utf-8").lower()
        for forbidden in ("private_key", "public_key", "token", "cookie", "serial_number", "ip_address"):
            self.assertNotIn(forbidden, text)

    def test_completed_evidence_contract_receipt_is_linked(self) -> None:
        data = json.loads(RECEIPT_001.read_text(encoding="utf-8"))
        self.assertEqual("GCP-TASK-0-01", data["task_id"])
        self.assertEqual("done_code", data["status"])
        self.assertIn("20_SRC/app/evidence_contract.py", data["changed_paths"])
        self.assertEqual("GCP-TASK-0-02", data["next_task"])

    def test_completed_score_binding_receipt_is_linked(self) -> None:
        data = json.loads(RECEIPT_002.read_text(encoding="utf-8"))
        self.assertEqual("GCP-TASK-0-02", data["task_id"])
        self.assertEqual("done_code", data["status"])
        self.assertIn("20_SRC/app/readiness_99_gate.py", data["changed_paths"])
        self.assertEqual("GCP-TASK-1-01", data["next_task"])


if __name__ == "__main__":
    unittest.main()
