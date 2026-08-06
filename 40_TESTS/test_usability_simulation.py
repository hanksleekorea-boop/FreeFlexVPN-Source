"""Contract checks for the transparent synthetic usability study."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "70_TOOLS" / "run_usability_simulation.py"
SPEC = importlib.util.spec_from_file_location("usability_simulation", TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def check(label: str, condition: bool) -> int:
    if not condition:
        raise AssertionError(label)
    print(f"PASS  {label}")
    return 1


def main() -> None:
    total = 0
    study = MODULE.build_study(1000)
    personas = study["personas"]
    total += check("가상 사용자 1,000명", study["persona_count"] == 1000 and len(personas) == 1000)
    total += check("실제 고객으로 표기하지 않음", study["participants_are_real"] is False)
    total += check("고유 사용자 식별자", len({persona["id"] for persona in personas}) == 1000)
    total += check("국적·현재 국가·목적·행태·기기·숙련도 포함", all(all(persona[key] for key in ("nationality", "current_country", "purpose", "behaviour", "device", "skill")) for persona in personas))
    total += check("모든 사용자 여정과 불편·요청 기능 포함", all(persona["journey"] and persona["observed_frictions"] and persona["requested_features"] for persona in personas))
    total += check("기기 다양성", set(study["distribution"]["device"]) == {"Android", "iPhone", "PC 웹"})
    total += check("필수 P0 신호", {"live_connection_check", "self_service_config", "recovery_flow"}.issubset(study["feature_signals"]))
    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = Path(temp_dir) / "study.json"
        report_path = Path(temp_dir) / "report.md"
        json_path.write_text(json.dumps(study, ensure_ascii=False), encoding="utf-8")
        report_path.write_text(MODULE._markdown(study), encoding="utf-8")
        report = report_path.read_text(encoding="utf-8")
        total += check("보고서가 실제 설문이 아님을 명시", "실제 고객 설문" in report and "실제 사람 0명" in report)
        total += check("보고서가 iPhone·실시간 한계를 명시", "iPhone" in report and "실시간" in report)
        total += check("JSON이 1,000명을 보존", len(json.loads(json_path.read_text(encoding="utf-8"))["personas"]) == 1000)
    print(f"사용성 모의 관찰 {total}/{total}")


if __name__ == "__main__":
    main()
