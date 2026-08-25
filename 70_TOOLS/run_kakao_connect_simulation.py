#!/usr/bin/env python3
"""Run a deterministic 1,000-person synthetic comprehension review for Kakao Connect."""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from collections import Counter
from datetime import date


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.kakao_connect_policy import evaluate_candidate, private_preview_model  # noqa: E402


SEED = 20260819
PERSONA_COUNT = 1_000


def _weighted(rng: random.Random, values: list[tuple[str, int]]) -> str:
    return rng.choices([value for value, _ in values], weights=[weight for _, weight in values], k=1)[0]


def build_personas(count: int = PERSONA_COUNT, seed: int = SEED) -> list[dict[str, object]]:
    rng = random.Random(seed)
    preview = private_preview_model()
    badges = set(preview["badges"])
    personas: list[dict[str, object]] = []
    for index in range(count):
        literacy = _weighted(rng, [("low", 28), ("medium", 52), ("high", 20)])
        purpose = _weighted(rng, [
            ("text_message", 38), ("photo_message", 25), ("voice_call", 23),
            ("video_4k", 6), ("bulk_download", 5), ("p2p", 3),
        ])
        price_sensitivity = _weighted(rng, [("high", 47), ("medium", 38), ("low", 15)])
        warning_read_rate = {"low": 0.79, "medium": 0.91, "high": 0.97}[literacy]
        if "비공개 후보" in badges:
            warning_read_rate = min(0.995, warning_read_rate + 0.08)
        price_read_rate = warning_read_rate + (0.05 if "가격 미결정" in badges else 0.0)
        price_read_rate -= 0.04 if price_sensitivity == "low" else 0.0
        profile_read_rate = warning_read_rate + (0.05 if "기존 설정 보존" in badges else 0.0)
        profile_read_rate -= 0.08 if literacy == "low" else 0.02
        decision = evaluate_candidate(current_country="CN", purpose=purpose)
        personas.append({
            "persona_id": f"synthetic-kc-{index + 1:04d}",
            "synthetic": True,
            "device": _weighted(rng, [("android_phone", 82), ("windows_pc", 13), ("other", 5)]),
            "digital_literacy": literacy,
            "stay_length": _weighted(rng, [("under_1_week", 27), ("1_to_4_weeks", 43), ("over_1_month", 30)]),
            "primary_purpose": purpose,
            "price_sensitivity": price_sensitivity,
            "understands_private_candidate": rng.random() < warning_read_rate,
            "understands_pricing_unresolved": rng.random() < max(0.0, price_read_rate),
            "understands_existing_profile_preserved": rng.random() < max(0.0, profile_read_rate),
            "unavailable_action_attempted": False,
            "policy_status": decision.status,
            "policy_reason": decision.reason,
            "can_charge": decision.can_charge,
            "can_offer_publicly": decision.can_offer_publicly,
        })
    return personas


def summarize(personas: list[dict[str, object]]) -> dict[str, object]:
    total = len(personas)
    if total != PERSONA_COUNT:
        raise ValueError(f"expected {PERSONA_COUNT} personas")
    preview = private_preview_model()
    metrics = {}
    for key in (
        "understands_private_candidate",
        "understands_pricing_unresolved",
        "understands_existing_profile_preserved",
    ):
        count = sum(1 for persona in personas if persona[key] is True)
        metrics[key] = {"modeled_count": count, "modeled_percent": round(count * 100 / total, 1)}
    unsupported = {"video_4k", "bulk_download", "p2p"}
    unsupported_personas = [p for p in personas if p["primary_purpose"] in unsupported]
    metrics["unsupported_intent_blocked"] = {
        "modeled_count": sum(1 for p in unsupported_personas if p["policy_reason"] == "unsupported_purpose"),
        "modeled_total": len(unsupported_personas),
    }
    metrics["unavailable_action_attempted"] = {
        "modeled_count": sum(1 for p in personas if p["unavailable_action_attempted"] is True),
        "modeled_percent": 0.0,
    }
    comprehension_keys = (
        "understands_private_candidate",
        "understands_pricing_unresolved",
        "understands_existing_profile_preserved",
    )
    weak = [key for key in comprehension_keys if metrics[key]["modeled_percent"] < 90]
    recommendations = []
    if "understands_pricing_unresolved" in weak:
        recommendations.append("가격 미결정 문구를 제목 바로 아래와 비활성 버튼 위에 반복한다.")
    if "understands_existing_profile_preserved" in weak:
        recommendations.append("기존 FreeFlexVPN·ffvpn을 바꾸지 않는다는 문구를 별도 보존 배지로 분리한다.")
    if "understands_private_candidate" in weak:
        recommendations.append("비공개 후보 상태를 제목·상태 배지·버튼의 세 위치에서 같은 표현으로 유지한다.")
    return {
        "schema": "FreeFlexKakaoSyntheticReviewV1",
        "generated_for": str(date(2026, 8, 19)),
        "seed": SEED,
        "persona_count": total,
        "evidence_grade": "modeled_not_actual_users",
        "network_test_performed": False,
        "android_test_performed": False,
        "pricing_status": "unresolved",
        "public_release": False,
        "preview_action_enabled": bool(preview["primary_action"]["enabled"]),
        "purpose_distribution": dict(sorted(Counter(str(p["primary_purpose"]) for p in personas).items())),
        "literacy_distribution": dict(sorted(Counter(str(p["digital_literacy"]) for p in personas).items())),
        "metrics": metrics,
        "recommendations": recommendations,
        "personas": personas,
    }


def render_report(result: dict[str, object]) -> str:
    metrics = result["metrics"]
    lines = [
        "# Kakao Connect 가상 사용자 1,000명 검토",
        "",
        "> 이 결과는 결정론적 모의 모델이며 실제 고객·중국망·Android·카카오톡·LINE·통화 증거가 아니다.",
        "",
        f"- 인원: {result['persona_count']}명 모두 가상",
        f"- 근거 등급: [추정] `{result['evidence_grade']}`",
        "- 가격: 미결정 / 결제·공개 신청 비활성",
        "- 실제 네트워크·Android 검사: 0건",
        "",
        "## 이해 가설",
        "",
    ]
    labels = {
        "understands_private_candidate": "비공개 후보 상태 이해",
        "understands_pricing_unresolved": "가격 미결정 이해",
        "understands_existing_profile_preserved": "기존 프로필 보존 이해",
    }
    for key, label in labels.items():
        value = metrics[key]
        lines.append(f"- [추정] {label}: {value['modeled_count']}/1,000 ({value['modeled_percent']}%)")
    blocked = metrics["unsupported_intent_blocked"]
    lines += [
        f"- [확인] 모의 입력의 비지원 목적 차단: {blocked['modeled_count']}/{blocked['modeled_total']}",
        "",
        "## 다음 문구 개선",
        "",
    ]
    recommendations = result["recommendations"]
    lines += [f"{index}. {value}" for index, value in enumerate(recommendations, 1)] or ["1. 현재 모형에서 90% 미만 항목 없음."]
    lines += [
        "",
        "## 해석 제한",
        "",
        "- 실제 연결 성공률·지연·통화 품질·유지율·구매율을 추정하지 않는다.",
        "- K5 실제 Android와 K6 제한 파일럿을 대체하지 않는다.",
        "- 각 가상 페르소나에는 실제 이름·계정·주소·IP·메시지 내용이 없다.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=pathlib.Path, required=True)
    parser.add_argument("--report-output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = summarize(build_personas())
    for output in (args.json_output, args.report_output):
        resolved = output.resolve()
        if ROOT.resolve() not in resolved.parents:
            raise SystemExit("outputs must stay inside the project")
        resolved.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    args.report_output.write_text(render_report(result), encoding="utf-8", newline="\n")
    print(f"Kakao Connect synthetic review: {result['persona_count']} personas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
