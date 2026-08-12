"""Create a reproducible, explicitly synthetic usability-risk study.

This is not a survey and it never represents simulated people as real customers.
It models task journeys against the documented public service surface so that a
small team can prioritise validation and product work before recruiting users.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


STUDY_VERSION = "1.0"
PERSONA_COUNT = 1000

# These are deliberately broad market contexts, never statements about an
# individual or a nationality.  Scenario characteristics drive the findings.
NATIONALITIES = [
    "대한민국", "태국", "일본", "베트남", "인도", "인도네시아", "미국", "독일", "브라질", "터키"
]
CURRENT_COUNTRIES = [
    "태국", "대한민국", "일본", "베트남", "싱가포르", "미국", "독일", "브라질", "인도", "터키"
]
PURPOSES = [
    "여행 중 공용 Wi-Fi 보호", "해외 체류 중 업무", "개인 정보 보호", "느린 공용망에서 안정적 접속",
    "합법적 서비스의 지역별 이용", "가족에게 안전한 연결 안내", "은행·결제 전 추가 보호", "원격 업무 도구 이용",
    "국경 이동 중 뉴스·연락", "비용을 아끼는 가벼운 일상 사용",
]
BEHAVIOURS = [
    "처음 QR 설정", "설정 후 매일 자동 연결 기대", "데이터 사용량을 자주 확인", "연결이 끊기면 즉시 재시도",
    "기술 용어를 피하고 싶음", "여러 기기를 번갈아 사용", "저사양·느린 망 사용", "접근성 보조 기능 사용",
    "가격·한도를 먼저 확인", "짧은 여행에서만 사용", "공개 장소에서 급히 연결", "가족·지인에게 설정을 설명",
]
DEVICES = ["Android", "iPhone", "PC 웹"]
SKILLS = ["처음 사용", "보통", "익숙함"]

# Publicly visible/currently verified service surface.  A feature is marked
# available only when it is visibly reachable, not merely planned.
CURRENT_SURFACE = {
    "public_service_dashboard": "공개 첫 화면과 진행 대시보드",
    "android_setup_guide": "Android WireGuard 설정 안내",
    "qr_handoff_guide": "QR 기반 설정 안내",
    "pc_responsive_ui": "PC·모바일 반응형 화면",
    "support_pages": "사용량·위치·도움말 공개 페이지",
    "connection_reconnect_note": "Android 실제 재연결 사용자 보고",
}

FEATURE_LABELS = {
    "live_connection_check": "지금 보호 중인지 한 번에 확인하는 실제 연결 검사",
    "self_service_config": "기기별 설정 발급·재발급·폐기 센터",
    "ios_verified_onboarding": "iPhone 실제 검증을 마친 단계별 시작 안내",
    "server_health_failover": "서버 상태·혼잡·장애 전환 화면",
    "usage_live_meter": "실시간 사용량·예상 소진·알림",
    "auto_connect_kill_switch": "공용망 자동 연결·차단 스위치 안내와 검증",
    "recovery_flow": "연결 실패 1분 복구 흐름과 도움 요청",
    "privacy_policy_detail": "정보 처리·기록 범위·관할을 쉬운 말로 설명",
    "pricing_fair_use": "비용·한도·공정 사용을 비교 가능한 표로 제시",
    "accessibility_language": "글자 크기·명암·화면 읽기·언어 선택",
    "multi_device_management": "여러 기기 상태·이름·접속 해제 관리",
    "travel_readiness": "출발 전 설치·도착 후 확인·비상 안내 묶음",
    "location_availability": "지역별 이용 가능성·합법적 이용 안내",
}


@dataclass(frozen=True)
class Persona:
    id: str
    nationality: str
    current_country: str
    purpose: str
    behaviour: str
    device: str
    skill: str
    journey: list[str]
    observed_frictions: list[str]
    requested_features: list[str]


def _pick(values: list[str], index: int, multiplier: int, offset: int = 0) -> str:
    return values[(index * multiplier + offset) % len(values)]


def _journey(persona: dict[str, str]) -> list[str]:
    steps = ["발견", "신뢰·비용 이해", "기기 선택", "설정 가져오기", "연결", "보호 확인", "사용량 관리", "문제 복구"]
    if "여행" in persona["purpose"] or "국경" in persona["purpose"] or "여행" in persona["behaviour"]:
        steps.insert(0, "출발 전 준비")
    if "가족" in persona["purpose"] or "가족" in persona["behaviour"]:
        steps.append("다른 사람에게 안내")
    return steps


def _needs(persona: dict[str, str]) -> tuple[list[str], list[str]]:
    features = {"live_connection_check", "self_service_config", "recovery_flow"}
    frictions = ["연결이 된 것과 실제로 보호되는 것을 구분하기 어렵다", "설정값을 어디서 다시 받는지 한눈에 알기 어렵다"]
    purpose = persona["purpose"]
    behaviour = persona["behaviour"]
    device = persona["device"]
    skill = persona["skill"]

    if device == "iPhone":
        features.add("ios_verified_onboarding")
        frictions.append("iPhone에서 같은 과정을 끝까지 따라갈 수 있는 실제 확인이 필요하다")
    if device == "PC 웹":
        features.add("multi_device_management")
        frictions.append("PC에서 본 설정과 휴대폰의 연결 상태를 함께 관리할 방법이 필요하다")
    if "공용 Wi-Fi" in purpose or "공개 장소" in behaviour or "은행" in purpose:
        features.add("auto_connect_kill_switch")
        frictions.append("급한 상황에서 자동 보호와 연결이 끊겼을 때의 안전 상태가 분명하지 않다")
    if "여행" in purpose or "국경" in purpose or "짧은 여행" in behaviour:
        features.update({"travel_readiness", "location_availability", "server_health_failover"})
        frictions.append("도착한 나라에서 쓸 수 있는지와 대체 경로를 미리 알기 어렵다")
    if "업무" in purpose or "원격" in purpose or "느린" in purpose or "느린" in behaviour:
        features.add("server_health_failover")
        frictions.append("업무 중 느려짐·끊김에서 어느 서버로 바꿔야 하는지 알기 어렵다")
    if "사용량" in behaviour or "비용" in purpose or "가격" in behaviour:
        features.update({"usage_live_meter", "pricing_fair_use"})
        frictions.append("현재 사용량과 다음 소진 시점을 실제 값으로 볼 수 없다")
    if "개인 정보" in purpose or "은행" in purpose:
        features.add("privacy_policy_detail")
        frictions.append("어떤 정보가 남는지와 보호 범위를 빠르게 확인하기 어렵다")
    if "접근성" in behaviour or skill == "처음 사용":
        features.add("accessibility_language")
        frictions.append("처음 하는 사람도 전문 용어 없이 실패를 해결할 안내가 더 필요하다")
    if "여러 기기" in behaviour:
        features.add("multi_device_management")
        frictions.append("기기별 설정의 이름·남은 연결·폐기 상태를 관리하기 어렵다")
    if "지역별" in purpose or persona["current_country"] != persona["nationality"]:
        features.add("location_availability")
        frictions.append("지역별 서비스 가능 범위와 합법적 이용 안내가 더 분명해야 한다")
    return sorted(frictions), sorted(features)


def generate_personas(count: int = PERSONA_COUNT) -> list[Persona]:
    personas: list[Persona] = []
    for index in range(count):
        raw = {
            "nationality": _pick(NATIONALITIES, index, 3, 1),
            "current_country": _pick(CURRENT_COUNTRIES, index, 7, 2),
            "purpose": _pick(PURPOSES, index, 9, 3),
            "behaviour": _pick(BEHAVIOURS, index, 11, 5),
            "device": _pick(DEVICES, index, 2),
            "skill": _pick(SKILLS, index, 2, 1),
        }
        frictions, features = _needs(raw)
        personas.append(Persona(
            id=f"SIM-{index + 1:04d}", journey=_journey(raw), observed_frictions=frictions,
            requested_features=features, **raw,
        ))
    return personas


def _counts(personas: Iterable[Persona], field: str) -> dict[str, int]:
    counter = Counter()
    for persona in personas:
        values = getattr(persona, field)
        counter.update(values if isinstance(values, list) else [values])
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def build_study(count: int = PERSONA_COUNT) -> dict:
    personas = generate_personas(count)
    return {
        "study_version": STUDY_VERSION,
        "generated_on": date.today().isoformat(),
        "method": "deterministic synthetic journey simulation",
        "participants_are_real": False,
        "persona_count": len(personas),
        "current_surface_inventory": CURRENT_SURFACE,
        "distribution": {
            "nationality": _counts(personas, "nationality"),
            "current_country": _counts(personas, "current_country"),
            "purpose": _counts(personas, "purpose"),
            "behaviour": _counts(personas, "behaviour"),
            "device": _counts(personas, "device"),
            "skill": _counts(personas, "skill"),
        },
        "friction_signals": _counts(personas, "observed_frictions"),
        "feature_signals": _counts(personas, "requested_features"),
        "personas": [asdict(persona) for persona in personas],
    }


def _markdown(study: dict) -> str:
    top_features = list(study["feature_signals"].items())[:10]
    top_frictions = list(study["friction_signals"].items())[:8]
    lines = [
        f"# FreeFlexVPN — 가상 사용자 {study['persona_count']:,}명 사용성 관찰 보고서",
        "",
        "## 먼저 읽을 점",
        "",
        f"이 문서는 실제 고객 설문이나 실제 접속 기록이 아닙니다. 나라·현재 위치·목적·사용 습관·기기·숙련도를 조합한 **재현 가능한 가상 여정 {study['persona_count']:,}개**입니다. 아래 숫자는 고객 비율이 아니라, 현재 화면과 안내에서 같은 불편이 몇 개의 가상 여정에 나타났는지 보여 주는 위험 신호입니다.",
        "",
        f"- 생성 수: {study['persona_count']}명 (실제 사람 0명)",
        "- 확인한 현재 화면 범위: 공개 첫 화면, 진행 대시보드, Android 설정 안내, QR 설정 안내, PC·모바일 화면, 도움말·사용량·위치 페이지",
        "- 확인하지 못한 것: 실제 서버의 현재 속도·가용성, iPhone 실기기 연결, 개인별 요금·사용량 실시간 값, 실제 고객의 감정·선호",
        "",
        "## 가장 큰 불편 신호",
        "",
    ]
    for text, count in top_frictions:
        lines.append(f"- {count}개 여정 — {text}")
    lines.extend([
        "",
        "## 우선 개선 기능",
        "",
        "|우선|가상 여정 신호|추가할 기능|사용자에게 바뀌는 점|",
        "|---|---:|---|---|",
    ])
    priorities = [
        ("P0", "live_connection_check", "연결 버튼 뒤에 ‘지금 보호 중/확인 불가/문제 있음’을 실제 검사로 보여 준다."),
        ("P0", "self_service_config", "QR·설정 파일을 기기별로 새로 만들고, 잃어버린 것은 폐기할 수 있게 한다."),
        ("P0", "recovery_flow", "끊김·가져오기 실패 때 1분 안에 다음 행동 하나를 안내한다."),
        ("P1", "ios_verified_onboarding", "iPhone에서 실제로 끝까지 검증한 화면과 버튼 이름으로 안내한다."),
        ("P1", "server_health_failover", "서버의 사용 가능·혼잡·장애와 대체 선택을 정직하게 보여 준다."),
        ("P1", "usage_live_meter", "남은 양, 예상 소진일, 알림을 실제 값으로 보여 준다."),
        ("P1", "auto_connect_kill_switch", "공용망 자동 연결과 끊겼을 때의 보호 방식을 설정·검증한다."),
        ("P2", "privacy_policy_detail", "기록 범위·개인 정보·법적 제한을 쉬운 말로 설명한다."),
        ("P2", "pricing_fair_use", "가격·한도·공정 사용 조건을 한 화면에서 비교한다."),
        ("P2", "accessibility_language", "언어, 큰 글자, 높은 명암, 화면 읽기 지원을 제공한다."),
        ("P2", "multi_device_management", "PC와 휴대폰의 기기 목록·상태·폐기를 한 곳에서 관리한다."),
        ("P2", "travel_readiness", "출발 전 설치, 현지 확인, 비상 복구를 한 장으로 묶는다."),
        ("P2", "location_availability", "지역별 이용 가능성 및 합법적 사용 안내를 별도로 둔다."),
    ]
    signals = study["feature_signals"]
    for priority, key, outcome in priorities:
        lines.append(f"|{priority}|{signals.get(key, 0)}|{FEATURE_LABELS[key]}|{outcome}|")
    lines.extend([
        "",
        "## 현재 UI·UX의 강점과 한계",
        "",
        "- 강점: 공개 첫 화면과 진행 상태가 보이고, Android 설정·QR 안내·PC/모바일 화면의 시작점이 있다.",
        "- 한계: 안내 화면은 있어도 ‘이 사용자가 지금 실제로 보호되었는가’를 서비스가 스스로 확인해 주지는 못한다.",
        "- 한계: 설정을 받는 흐름은 있으나, 기기별 재발급·폐기·여러 기기 관리가 사용자용 화면으로 완결되어 있지 않다.",
        "- 한계: 서버의 현재 상태, 실제 사용량, 소진 예상, 지역별 이용 가능성을 정직한 실시간 값으로 보여 주는 기반이 없다.",
        "- 한계: Android는 실제 사용자 연결 보고가 있지만, iPhone은 같은 수준의 실기기 검증이 아직 없다.",
        "",
        "## 다음 검증 순서",
        "",
        "1. 실제 Android와 iPhone 각각에서 설치 → 연결 → 외부 사이트 열기 → 끊김 후 재연결을 관찰한다.",
        "2. P0 세 항목을 화면 시제품으로 만든 뒤, 처음 사용하는 실제 사용자 5명 이상에게 과제를 맡긴다.",
        "3. 실제 사용량·서버 상태를 넣기 전에는 ‘실시간’, ‘안전 보장’ 같은 표현을 쓰지 않는다.",
        "4. 지역별 법률·서비스 이용 가능성은 출시 전 대상 국가별로 별도 확인한다.",
        "",
        "## 재현 방법",
        "",
        "`python 70_TOOLS/run_usability_simulation.py --count 1000 --output-json 10_STATE/USABILITY_SIMULATION_1000_2026-08-05.json --output-report 10_STATE/USABILITY_SIMULATION_1000_REPORT_2026-08-05.md`",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a transparent synthetic usability study")
    parser.add_argument("--count", type=int, default=PERSONA_COUNT)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    study = build_study(args.count)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(study, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_report.write_text(_markdown(study), encoding="utf-8")
    print(f"가상 사용자 {study['persona_count']}명 생성")
    print(f"JSON: {args.output_json}")
    print(f"보고서: {args.output_report}")


if __name__ == "__main__":
    main()
