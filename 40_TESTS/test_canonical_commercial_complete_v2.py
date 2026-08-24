from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "10_PLAN" / "CURRENT_SERVICE_PLAN.md"
DEVELOPMENT = ROOT / "10_PLAN" / "CURRENT_DEVELOPMENT_EXECUTION_PLAN.md"
CONTRACT = ROOT / "20_SRC" / "app" / "commercial_complete_contract.py"
RECEIPT = ROOT / "10_STATE" / "CC_TASK_RECEIPT_TEMPLATE_v2.json"


class CommercialCompleteV2CanonicalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = SERVICE.read_text(encoding="utf-8")
        cls.development = DEVELOPMENT.read_text(encoding="utf-8")

    def test_product_contract_is_complete_and_adopted(self) -> None:
        for index in range(1, 11):
            self.assertIn(f"CC-BASE-{index:02d}", self.service)
        for index in range(1, 25):
            self.assertRegex(self.service, rf"\| CC-{index:02d} \|")
        self.assertIn("CC-GATE-1", self.service)
        self.assertIn("최신 제품 계약으로 채택", self.service)
        self.assertIn("Android 실제 VPN + 모바일·PC 관리 웹", self.service)

    def test_stage_one_is_commercially_complete_but_scope_honest(self) -> None:
        required = (
            "1단계 — 완전 상용판",
            "Android 실제 VPN과 모바일·PC 관리 웹",
            "iPhone·Windows·Kakao Connect는 지원 밖",
            "실제 가격·세금·자동 갱신 없음·환불 규칙 확정",
            "시험 결제 성공·실패·중복·취소·환불·구매 복원 통과",
            "운영자 신원·문의 채널·지원 시간·상태판 공개",
            "치명·높음 결함 0",
        )
        for phrase in required:
            self.assertIn(phrase, self.service)

    def test_three_stage_task_cards_are_unique_and_complete(self) -> None:
        task_ids = re.findall(r"^#### (CC-TASK-[123]-\d{2})\b", self.development, re.MULTILINE)
        self.assertEqual(29, len(task_ids))
        self.assertEqual(29, len(set(task_ids)))
        self.assertEqual(17, sum(task.startswith("CC-TASK-1-") for task in task_ids))
        self.assertEqual(7, sum(task.startswith("CC-TASK-2-") for task in task_ids))
        self.assertEqual(5, sum(task.startswith("CC-TASK-3-") for task in task_ids))
        self.assertIn("CC-TASK-1-16 1단계 완전 상용 판정", self.development)
        self.assertIn("CC-TASK-2-07 2단계 선두권 판정", self.development)
        self.assertIn("CC-TASK-3-05 3단계 세계 최고 후보 판정", self.development)

    def test_task_table_dependencies_exist_and_only_point_backward(self) -> None:
        rows = re.findall(
            r"^\| ([123]-\d{2}) \| [^|]+ \| [^|]+ \| ([^|]+) \| ([^|]+) \| [^|]+ \|$",
            self.development,
            re.MULTILINE,
        )
        self.assertEqual(29, len(rows))
        order = [task for task, _, _ in rows]
        self.assertEqual(len(order), len(set(order)))
        position = {task: index for index, task in enumerate(order)}
        for task, dependency_text, status in rows:
            self.assertNotIn("DONE", status)
            if "없음" in dependency_text:
                self.assertEqual("1-00", task)
                continue
            dependencies: list[str] = []
            for start, end in re.findall(r"([123]-\d{2})(?:~([123]-\d{2}))?", dependency_text):
                if not end:
                    dependencies.append(start)
                    continue
                start_stage, start_number = start.split("-")
                end_stage, end_number = end.split("-")
                self.assertEqual(start_stage, end_stage)
                dependencies.extend(
                    f"{start_stage}-{number:02d}"
                    for number in range(int(start_number), int(end_number) + 1)
                )
            self.assertTrue(dependencies, f"{task} 선행 작업을 읽을 수 없음")
            for dependency in dependencies:
                self.assertIn(dependency, position, f"{task}의 없는 선행 작업 {dependency}")
                self.assertLess(position[dependency], position[task], f"{task}의 역방향 선행 {dependency}")

    def test_low_skill_ai_safety_contract_is_explicit(self) -> None:
        required = (
            "한 번에 한 작업만 수행",
            "읽을 파일",
            "정상 검사와 일부러 틀린 값을 넣어 실패를 잡는 검사",
            "WAITING-EXTERNAL",
            "DONE-CODE",
            "DONE-VERIFIED",
            "작업 완료 영수증 형식",
            "되돌리기",
            "기존 `ffvpn`",
            "Drive B",
        )
        for phrase in required:
            self.assertIn(phrase, self.development)

    def test_first_real_android_point_is_explicit(self) -> None:
        self.assertIn("`CC-TASK-1-04`부터 실제 Android가 필요", self.development)
        self.assertIn("유휴한 한 대만 선택", self.development)
        self.assertIn("다른 폰·기존 `ffvpn`·Drive B는 건드리지 않는다", self.development)

    def test_machine_contract_and_receipt_template_exist(self) -> None:
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(RECEIPT.is_file())
        source = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("validate_canonical_documents", source)
        self.assertIn("validate_task_receipt", source)


if __name__ == "__main__":
    unittest.main()
