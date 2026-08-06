#!/usr/bin/env python3
"""Generate an evidence-bound, self-contained progress dashboard from JSON."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SCHEMA = "FreeFlexVPNProgressDashboardConfigV1"
AREA_COLORS_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
AREA_COLORS_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
STATUS_COLORS = {"critical": "#d03b3b", "warning": "#fab219", "normal": "#ec835a", "good": "#0ca30c"}
MILESTONE_STATUSES = {"complete", "pending", "blocked"}
BLOCK_CLASSES = {"permission", "tool_unresponsive", "physical_absence"}
CAUSE_LAYERS = {"one_time", "structural", "undetermined"}
ROADMAP_STATUSES = {"progress", "pending", "blocked", "complete"}
CAUSE_LAYER_LABELS = {"one_time": "이번만", "structural": "구조적", "undetermined": "아직 판정 못 함"}
ROADMAP_STATUS_LABELS = {"progress": "진행 중", "pending": "대기", "blocked": "차단", "complete": "완료"}


class DashboardError(ValueError):
    """A configuration error that must stop rendering."""


def _day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise DashboardError(f"{field} must be YYYY-MM-DD") from exc


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _project_file(project_root: Path, relative: str, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise DashboardError(f"{field} must be a project-relative file path")
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as exc:
        raise DashboardError(f"{field} escapes project root: {relative}") from exc
    if not candidate.is_file():
        raise DashboardError(f"{field} is missing: {relative}")
    return candidate


def _linear(day_value: date, start: date, end: date) -> float:
    if end < start:
        raise DashboardError("plan end precedes plan start")
    if start == end:
        return 100.0 if day_value >= end else 0.0
    if day_value <= start:
        return 0.0
    if day_value >= end:
        return 100.0
    return (day_value - start).days * 100.0 / (end - start).days


def _continuous_linear(position: float, start: float, end: float) -> float:
    if start == end:
        return 100.0 if position >= end else 0.0
    if position <= start:
        return 0.0
    if position >= end:
        return 100.0
    return (position - start) * 100.0 / (end - start)


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardError(f"cannot read config: {exc}") from exc
    if not isinstance(value, dict):
        raise DashboardError("config root must be an object")
    return value


def build_model(config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    if config.get("schema") != SCHEMA:
        raise DashboardError(f"schema must be {SCHEMA}")
    project = config.get("project")
    if not isinstance(project, dict) or not project.get("name") or not project.get("candidate"):
        raise DashboardError("project.name and project.candidate are required")
    start = _day(project.get("start_date"), "project.start_date")
    end = _day(project.get("target_date"), "project.target_date")
    report = _day(project.get("report_date"), "project.report_date")
    if end < start or not start <= report <= end:
        raise DashboardError("report_date must be inside the project plan range")
    columns = (end - start).days + 1
    if columns > 40:
        raise DashboardError("Gantt would exceed 40 columns; switch the config to weekly units")

    areas = config.get("areas")
    if not isinstance(areas, list) or not 2 <= len(areas) <= 8:
        raise DashboardError("areas must contain 2 to 8 entries")
    if abs(sum(float(item.get("weight", -1)) for item in areas) - 100.0) > 0.001:
        raise DashboardError("area weights must sum to 100")
    area_ids = [item.get("id") for item in areas]
    if any(not item for item in area_ids) or len(area_ids) != len(set(area_ids)):
        raise DashboardError("area ids must be non-empty and unique")

    normalized_areas: list[dict[str, Any]] = []
    for index, raw in enumerate(areas):
        weight = float(raw["weight"])
        if weight <= 0:
            raise DashboardError("area weights must be positive")
        area_start = _day(raw.get("plan_start"), f"areas[{index}].plan_start")
        area_end = _day(raw.get("plan_end"), f"areas[{index}].plan_end")
        if not start <= area_start <= area_end <= end:
            raise DashboardError("area plan dates must be inside the project range")
        normalized_areas.append({
            **raw,
            "weight": weight,
            "plan_start_date": area_start,
            "plan_end_date": area_end,
            "light": AREA_COLORS_LIGHT[index],
            "dark": AREA_COLORS_DARK[index],
        })

    milestones = config.get("milestones")
    if not isinstance(milestones, list) or not milestones:
        raise DashboardError("at least one milestone is required")
    milestone_ids = [item.get("id") for item in milestones]
    if any(not item for item in milestone_ids) or len(milestone_ids) != len(set(milestone_ids)):
        raise DashboardError("milestone ids must be non-empty and unique")
    for index, item in enumerate(milestones):
        if item.get("area") not in area_ids:
            raise DashboardError(f"milestones[{index}] references an unknown area")
        if item.get("status") not in MILESTONE_STATUSES:
            raise DashboardError(f"milestones[{index}] has an invalid status")
        evidence = item.get("evidence", [])
        if item["status"] == "complete" and (not isinstance(evidence, list) or not evidence):
            raise DashboardError(f"completed milestone {item['id']} has no evidence")
        for relative in evidence:
            _project_file(project_root, relative, "evidence file")

    for area in normalized_areas:
        assigned = [item for item in milestones if item["area"] == area["id"]]
        if not assigned:
            raise DashboardError(f"area {area['id']} has no milestones")
        complete = [item for item in assigned if item["status"] == "complete"]
        area["milestone_total"] = len(assigned)
        area["milestone_complete"] = len(complete)
        area["actual"] = len(complete) * 100.0 / len(assigned)
        area["planned"] = _linear(report, area["plan_start_date"], area["plan_end_date"])
        area["contribution"] = area["weight"] * area["actual"] / 100.0
        area["done"] = [item["label"] for item in complete]
        area["remaining"] = [item["label"] for item in assigned if item["status"] != "complete"]

    actual = sum(area["contribution"] for area in normalized_areas)
    planned = sum(area["weight"] * area["planned"] / 100.0 for area in normalized_areas)
    start_ordinal = start.toordinal()
    offsets = [
        (area["plan_start_date"].toordinal() - start_ordinal, area["plan_end_date"].toordinal() - start_ordinal)
        for area in normalized_areas
    ]

    def curve(position: float) -> float:
        return sum(
            area["weight"] * _continuous_linear(position, offsets[index][0], offsets[index][1]) / 100.0
            for index, area in enumerate(normalized_areas)
        )

    lo, hi = 0.0, float((end - start).days)
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if curve(mid) < actual:
            lo = mid
        else:
            hi = mid
    equivalent_offset = (lo + hi) / 2.0
    today_offset = float((report - start).days)
    schedule_delta = equivalent_offset - today_offset
    if abs(actual - planned) < 0.0001:
        schedule_delta = 0.0

    progress_history = config.get("progress_history", [])
    if not isinstance(progress_history, list):
        raise DashboardError("progress_history must be a list")
    normalized_history: list[dict[str, Any]] = []
    for index, item in enumerate(progress_history):
        if not isinstance(item, dict):
            raise DashboardError(f"progress_history[{index}] must be an object")
        measured_on = _day(item.get("date"), f"progress_history[{index}].date")
        try:
            percent = float(item.get("actual_percent"))
        except (TypeError, ValueError) as exc:
            raise DashboardError(f"progress_history[{index}].actual_percent must be numeric") from exc
        if not 0.0 <= percent <= 100.0:
            raise DashboardError("progress history percentages must be between 0 and 100")
        if measured_on > report:
            raise DashboardError("progress history cannot be in the future")
        if normalized_history:
            if measured_on <= normalized_history[-1]["date_value"]:
                raise DashboardError("progress history dates must be strictly increasing")
            if percent < normalized_history[-1]["actual_percent"]:
                raise DashboardError("progress history cannot move backwards")
        normalized_history.append({**item, "date_value": measured_on, "actual_percent": percent})
    if normalized_history:
        latest = normalized_history[-1]
        if latest["date_value"] != report or abs(latest["actual_percent"] - actual) > 0.05:
            raise DashboardError("latest progress history point must match report date and actual progress")

    eta: dict[str, Any] = {
        "initial_date": end.isoformat(),
        "current_date": None,
        "status": "insufficient_sample",
        "speed_percent_per_day": None,
        "remaining_days": None,
        "deviation_days": None,
        "sample_start": None,
        "sample_end": None,
    }
    if actual >= 99.999:
        eta.update({"current_date": report.isoformat(), "status": "complete", "speed_percent_per_day": 0.0, "remaining_days": 0, "deviation_days": (report - end).days})
    elif len(normalized_history) >= 2:
        previous, latest = normalized_history[-2], normalized_history[-1]
        elapsed_days = (latest["date_value"] - previous["date_value"]).days
        speed = (latest["actual_percent"] - previous["actual_percent"]) / elapsed_days
        eta.update({
            "speed_percent_per_day": round(speed, 3),
            "sample_start": previous["date_value"].isoformat(),
            "sample_end": latest["date_value"].isoformat(),
        })
        if speed > 0:
            remaining_days = math.ceil((100.0 - actual) / speed)
            current_date = report + timedelta(days=remaining_days)
            eta.update({
                "current_date": current_date.isoformat(),
                "status": "projected",
                "remaining_days": remaining_days,
                "deviation_days": (current_date - end).days,
            })
        else:
            eta["status"] = "blocked_zero_velocity"

    bottlenecks = config.get("bottlenecks", [])
    if not isinstance(bottlenecks, list):
        raise DashboardError("bottlenecks must be a list")
    normalized_bottlenecks = []
    for item in bottlenecks:
        if item.get("severity") not in STATUS_COLORS:
            raise DashboardError("invalid bottleneck severity")
        if item.get("classification") not in BLOCK_CLASSES:
            raise DashboardError("invalid bottleneck classification")
        for required in ("title", "measured", "works", "blocked", "solution", "queue"):
            if not item.get(required):
                raise DashboardError(f"bottleneck {item.get('id', '?')} lacks {required}")
        cause_layer = item.get("cause_layer", "undetermined")
        if cause_layer not in CAUSE_LAYERS:
            raise DashboardError("invalid bottleneck cause_layer")
        consecutive_reports = int(item.get("consecutive_reports", 1))
        if consecutive_reports < 1:
            raise DashboardError("consecutive_reports must be positive")
        severity = item["severity"]
        if consecutive_reports >= 2 and severity == "warning":
            severity = "critical"
        normalized_bottlenecks.append({
            **item,
            "severity": severity,
            "cause_layer": cause_layer,
            "consecutive_reports": consecutive_reports,
            "waiting_days": int(item.get("waiting_days", 0)),
            "owner_action": item.get("owner_action", item["solution"]),
            "user_action": item.get("user_action", "없음"),
            "eta_impact_days": item.get("eta_impact_days"),
            "impact_note": item.get("impact_note", "영향 측정 없음"),
        })

    public_app = config.get("public_app")
    normalized_public_app = None
    if public_app is not None:
        if not isinstance(public_app, dict):
            raise DashboardError("public_app must be an object")
        for required in ("url", "public_version", "candidate_label", "candidate_status", "qr_path", "qr_evidence_path", "download_path", "verified_at"):
            if not public_app.get(required):
                raise DashboardError(f"public_app.{required} is required")
        qr_path = _project_file(project_root, public_app["qr_path"], "public_app.qr_path")
        evidence_path = _project_file(project_root, public_app["qr_evidence_path"], "public_app.qr_evidence_path")
        _project_file(project_root, public_app["download_path"], "public_app.download_path")
        try:
            qr_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DashboardError(f"cannot read QR evidence: {exc}") from exc
        qr_bytes = qr_path.read_bytes()
        actual_qr_sha = _sha256(qr_bytes)
        expected_url = public_app["url"]
        if qr_evidence.get("target_url") != expected_url or qr_evidence.get("decoded_payload") != expected_url:
            raise DashboardError("QR decoded payload does not exactly match the public app URL")
        if str(qr_evidence.get("sha256", "")).upper() != actual_qr_sha or qr_evidence.get("bytes") != len(qr_bytes):
            raise DashboardError("QR file does not match its decoder evidence")
        normalized_public_app = {
            **public_app,
            "qr_sha256": actual_qr_sha,
            "qr_bytes": len(qr_bytes),
            "qr_data_uri": "data:image/png;base64," + base64.b64encode(qr_bytes).decode("ascii"),
            "qr_verification": "decoded_exact_match",
        }

    roadmap = config.get("roadmap", [])
    if not isinstance(roadmap, list):
        raise DashboardError("roadmap must be a list")
    if roadmap and not 2 <= len(roadmap) <= 3:
        raise DashboardError("roadmap must contain 2 to 3 releases")
    for index, item in enumerate(roadmap):
        if not isinstance(item, dict) or not item.get("version") or not item.get("visible_change"):
            raise DashboardError(f"roadmap[{index}] needs version and visible_change")
        if item.get("status") not in ROADMAP_STATUSES:
            raise DashboardError(f"roadmap[{index}] has an invalid status")

    glossary = config.get("glossary", [])
    if not isinstance(glossary, list):
        raise DashboardError("glossary must be a list")
    for index, item in enumerate(glossary):
        if not isinstance(item, dict) or not item.get("term") or not item.get("meaning"):
            raise DashboardError(f"glossary[{index}] needs term and meaning")

    return {
        "schema": "FreeFlexVPNGeneratedProgressV1",
        "project": project,
        "config_sha256": _sha256(_canonical_bytes(config)),
        "areas": normalized_areas,
        "milestones": milestones,
        "bottlenecks": normalized_bottlenecks,
        "eta": eta,
        "public_app": normalized_public_app,
        "roadmap": roadmap,
        "glossary": glossary,
        "actual_percent": round(actual, 1),
        "planned_percent": round(planned, 1),
        "schedule_delta_days": round(schedule_delta, 1),
        "remaining_milestones": sum(item["status"] != "complete" for item in milestones),
        "completed_milestones": sum(item["status"] == "complete" for item in milestones),
        "total_milestones": len(milestones),
        "gantt_columns": columns,
        "baseline_note": config.get("baseline_note", ""),
        "method_note": config.get("method_note", ""),
    }


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_html(model: dict[str, Any]) -> str:
    project = model["project"]
    eta = model["eta"]
    eta_delta = eta["deviation_days"]
    delta_class = "ahead" if eta_delta is not None and eta_delta < 0 else "behind" if eta_delta is not None and eta_delta > 0 else "even"
    if eta["current_date"]:
        current_eta_text = eta["current_date"]
        eta_delta_text = f"{eta_delta:+d}일" if eta_delta else "0일"
    else:
        current_eta_text = "측정 불가"
        eta_delta_text = "편차 측정 불가"
    area_css = "\n".join(
        f":root{{--area-{i}:{a['light']}}}html[data-theme='dark']{{--area-{i}:{a['dark']}}}"
        for i, a in enumerate(model["areas"])
    )
    bars = []
    gantt_rows = []
    table_rows = []
    start = _day(project["start_date"], "start")
    initial_target = _day(project["target_date"], "end")
    report_day = _day(project["report_date"], "report")
    current_target = _day(eta["current_date"], "eta.current_date") if eta["current_date"] else None
    visual_end = max(day for day in (initial_target, report_day, current_target) if day is not None)
    total_span = max(1, (visual_end - start).days)
    for index, area in enumerate(model["areas"]):
        done = ", ".join(area["done"]) or "없음"
        remaining = ", ".join(area["remaining"]) or "없음"
        tip = _e(f"{area['name']} · 가중치 {area['weight']:.1f}% · 실제 {_pct(area['actual'])} / 계획 {_pct(area['planned'])} · 완료: {done} · 남음: {remaining}")
        bars.append(
            f"<div class='area-row' tabindex='0' aria-label='{tip}'><div class='area-name'><i style='background:var(--area-{index})'></i>{_e(area['name'])}</div>"
            f"<div class='track'><span class='actual' style='width:{area['actual']:.3f}%;background:var(--area-{index})'></span>"
            f"<b class='plan-mark' style='left:{area['planned']:.3f}%' aria-hidden='true'></b><div class='tip'>{tip}</div></div>"
            f"<strong>{_pct(area['actual'])} / {_pct(area['planned'])} <small>{area['actual']-area['planned']:+.1f}%p</small></strong></div>"
        )
        left = (area["plan_start_date"] - start).days * 100.0 / total_span
        width = max(1.4, (area["plan_end_date"] - area["plan_start_date"]).days * 100.0 / total_span)
        actual_width = width * area["actual"] / 100.0
        value_left = min(92.0, left + actual_width + 0.6)
        gantt_rows.append(
            f"<div class='gantt-label'>{_e(area['name'])}</div><div class='gantt-track'><span class='gantt-plan' style='left:{left:.3f}%;width:{width:.3f}%'></span>"
            f"<span class='gantt-actual' style='left:{left:.3f}%;width:{actual_width:.3f}%;background:var(--area-{index})'></span>"
            f"<b class='gantt-value' style='left:{value_left:.3f}%;color:var(--area-{index})'>{_pct(area['actual'])}</b></div>"
        )
        table_rows.append(
            f"<tr><th>{_e(area['name'])}</th><td>{area['weight']:.1f}%</td><td>{area['plan_start_date']}~{area['plan_end_date']}</td>"
            f"<td>{_pct(area['planned'])}</td><td>{_pct(area['actual'])}</td><td>{area['actual']-area['planned']:+.1f}%p</td><td>{area['contribution']:.1f}%p</td></tr>"
        )
    today_left = (report_day - start).days * 100.0 / total_span
    initial_left = (initial_target - start).days * 100.0 / total_span
    current_left = (current_target - start).days * 100.0 / total_span if current_target else None
    blockers = "".join(
        f"<article class='blocker' style='border-left-color:{STATUS_COLORS[item['severity']]}'><div class='block-head'><b>{_e(item['title'])}</b>"
        f"<span>{_e(CAUSE_LAYER_LABELS[item['cause_layer']])} · 연속 {item['consecutive_reports']}회 · 대기 {item['waiting_days']}일</span></div>"
        f"<p><strong>막힌 것:</strong> {_e(item['blocked'])} · {_e(item['measured'])}</p>"
        f"<p><strong>원인 계층:</strong> {_e(CAUSE_LAYER_LABELS[item['cause_layer']])}</p>"
        f"<p><strong>풀리는 조건:</strong> Codex — {_e(item['owner_action'])} / 사용자 — {_e(item['user_action'])}</p>"
        f"<p><strong>방치 시 영향:</strong> {_e(item['impact_note'])}</p>"
        f"<p class='fine'><strong>현재 가능한 것:</strong> {_e(item['works'])} · <strong>대기열:</strong> {_e(item['queue'])}</p></article>" for item in model["bottlenecks"]
    )
    if not blockers:
        blockers = "<p class='ok'>병목: 없음</p>"
    roadmap = "".join(
        f"<article class='roadmap-item roadmap-{_e(item['status'])}'><b>{_e(item['version'])}</b><span>{_e(item['visible_change'])}</span><small>{_e(ROADMAP_STATUS_LABELS[item['status']])}</small></article>"
        for item in model["roadmap"]
    ) or "<p class='note'>다음 출시 정보 없음</p>"
    public_app = model["public_app"]
    if public_app:
        qr_block = (
            f"<section class='panel qr-panel'><div><h2>📱 최신 검증 앱</h2>"
            f"<p><a href='{_e(public_app['url'])}'>{_e(public_app['url'])}</a></p>"
            f"<p><strong>다운로드:</strong> <code>{_e(public_app['download_path'])}</code></p>"
            f"<p>{_e(public_app['public_version'])} | {_e(public_app['candidate_label'])}({_e(public_app['candidate_status'])}) | QR 검증: 디코드 완전 일치 · {_e(public_app['verified_at'])}</p></div>"
            f"<img src='{public_app['qr_data_uri']}' width='164' height='164' alt='검증된 공개 앱 QR'></section>"
        )
    else:
        qr_block = "<section class='panel'><h2>📱 최신 검증 앱</h2><p>QR: 차단 — 검증 가능한 공개 진입점이 설정되지 않았습니다.</p></section>"
    glossary = "".join(
        f"<dt>{_e(item['term'])}</dt><dd>{_e(item['meaning'])}</dd>" for item in model["glossary"]
    ) or "<dt>등록 없음</dt><dd>이번 보고에 별도 기술 용어가 없습니다.</dd>"
    current_line = (
        f"<i class='current-eta' style='--current-left:{current_left/100:.6f};left:calc(190px + 14px + (100% - 204px)*{current_left/100:.6f})' aria-label='현재 예상 완료'></i>"
        if current_left is not None else ""
    )
    if eta["speed_percent_per_day"] is None:
        eta_method = "최근 실측 표본이 2개보다 적어 현재 예상일을 만들지 않았습니다."
    elif eta["speed_percent_per_day"] <= 0:
        eta_method = f"최근 {eta['sample_start']}~{eta['sample_end']} 실측 속도가 0.0%/일이어서 유한한 완료일을 만들 수 없습니다."
    else:
        eta_method = f"최근 실측 속도 {eta['speed_percent_per_day']:.3f}%/일과 남은 진척에서 {eta['remaining_days']}일을 계산했습니다."
    embedded = json.dumps({
        "config_sha256": model["config_sha256"],
        "actual_percent": model["actual_percent"],
        "planned_percent": model["planned_percent"],
        "schedule_delta_days": model["schedule_delta_days"],
        "eta": model["eta"],
    }, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{_e(project['name'])} {_e(project['candidate'])} 진척 대시보드</title>
<style>
:root{{--bg:#f4f7fa;--card:#fff;--text:#13202a;--muted:#63717c;--line:#d8e0e6;--plan:#7c8791;--shadow:0 12px 35px #15354b12;--ahead:#0ca30c;--behind:#d03b3b;--even:#596670}}
@media(prefers-color-scheme:dark){{:root{{--bg:#071318;--card:#0d2029;--text:#f4f8fa;--muted:#a8bbc4;--line:#1d3c49;--plan:#84939d;--shadow:none;--ahead:#35c56c;--behind:#ff7979;--even:#a8bbc4}}}}
html[data-theme='light']{{--bg:#f4f7fa;--card:#fff;--text:#13202a;--muted:#63717c;--line:#d8e0e6;--plan:#7c8791;--shadow:0 12px 35px #15354b12;--ahead:#0ca30c;--behind:#d03b3b;--even:#596670}}
html[data-theme='dark']{{--bg:#071318;--card:#0d2029;--text:#f4f8fa;--muted:#a8bbc4;--line:#1d3c49;--plan:#84939d;--shadow:none;--ahead:#35c56c;--behind:#ff7979;--even:#a8bbc4}}
{area_css}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif}}button{{font:inherit}}.wrap{{width:min(1120px,calc(100% - 28px));margin:auto;padding:28px 0 58px}}header{{display:flex;justify-content:space-between;gap:18px;align-items:start}}h1{{margin:0;font-size:clamp(26px,4vw,38px)}}h2{{margin:0 0 16px;font-size:20px}}.sub,.fine{{color:var(--muted)}}.theme{{border:1px solid var(--line);background:var(--card);color:var(--text);padding:9px 12px;border-radius:12px;cursor:pointer}}.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:24px 0}}.card,.panel{{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}}.card{{padding:17px}}.card span{{display:block;color:var(--muted);font-size:12px}}.card b{{display:block;font-size:26px;font-variant-numeric:tabular-nums;margin-top:5px}}.card small{{display:block;color:var(--muted)}}.card b.ahead{{color:var(--ahead)}}.card b.behind{{color:var(--behind)}}.card b.even{{color:var(--even)}}.panel{{padding:21px;margin-top:14px}}.area-row{{display:grid;grid-template-columns:190px 1fr 215px;gap:14px;align-items:center;margin:14px 0;position:relative}}.area-name{{font-weight:700}}.area-name i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px}}.track{{height:16px;border-radius:999px;background:var(--line);position:relative}}.actual{{position:absolute;inset:0 auto 0 0;border-radius:999px}}.plan-mark{{position:absolute;top:-5px;width:3px;height:26px;background:var(--plan);transform:translateX(-1px)}}.area-row>strong{{text-align:right;font-variant-numeric:tabular-nums}}.area-row small{{color:var(--muted)}}.tip{{display:none;position:absolute;z-index:4;left:20px;right:20px;bottom:26px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);box-shadow:var(--shadow);font-size:12px}}.area-row:hover .tip,.area-row:focus .tip{{display:block}}.gantt{{display:grid;grid-template-columns:190px 1fr;gap:12px 14px;position:relative}}.gantt-label{{font-weight:700}}.gantt-track{{height:28px;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(7.692% - 1px),var(--line) calc(7.692% - 1px),var(--line) 7.692%);position:relative}}.gantt-plan,.gantt-actual{{position:absolute;top:6px;height:16px;border-radius:5px}}.gantt-plan{{background:#aab2b8}}.gantt-value{{position:absolute;top:5px;font-size:10px;white-space:nowrap;font-variant-numeric:tabular-nums}}.today,.initial-target,.current-eta{{position:absolute;top:0;bottom:0;width:2px;z-index:2}}.today{{background:#d03b3b;left:calc(190px + 14px + (100% - 204px)*{today_left/100:.6f})}}.initial-target{{background:#7c8791;left:calc(190px + 14px + (100% - 204px)*{initial_left/100:.6f})}}.current-eta{{border-left:3px dashed #ed8b00;width:0}}.legend{{display:flex;gap:14px;flex-wrap:wrap}}.legend b{{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:5px}}.blockers{{display:grid;gap:10px}}.blocker{{border:1px solid var(--line);border-left:6px solid;border-radius:12px;padding:13px 15px}}.blocker p{{margin:6px 0}}.block-head{{display:flex;justify-content:space-between;gap:12px}}.block-head span{{color:var(--muted);font-size:12px}}.roadmap{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.roadmap-item{{display:grid;gap:7px;border:1px solid var(--line);border-top:7px solid var(--plan);border-radius:12px;padding:14px}}.roadmap-item small{{color:var(--muted)}}.roadmap-progress{{border-top-color:#ed8b00}}.roadmap-blocked{{border-top-color:#d03b3b}}.roadmap-complete{{border-top-color:#0ca30c}}.qr-panel{{display:flex;justify-content:space-between;align-items:center;gap:20px}}.qr-panel img{{border:8px solid #fff;border-radius:10px}}.terms{{display:grid;grid-template-columns:max-content 1fr;gap:7px 15px}}.terms dt{{font-weight:800}}.terms dd{{margin:0}}.ok{{color:var(--ahead);font-weight:800}}table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}tfoot{{font-weight:800}}.scroll{{overflow:auto}}.note{{font-size:13px;color:var(--muted)}}code{{word-break:break-all}}@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}.roadmap{{grid-template-columns:1fr}}}}@media(max-width:760px){{.area-row{{grid-template-columns:1fr}}.area-row>strong{{text-align:left}}.gantt{{grid-template-columns:100px 1fr}}.today{{left:calc(100px + 14px + (100% - 114px)*{today_left/100:.6f})}}.initial-target{{left:calc(100px + 14px + (100% - 114px)*{initial_left/100:.6f})}}.current-eta{{left:calc(100px + 14px + (100% - 114px)*var(--current-left))!important}}.qr-panel{{display:block}}header{{display:block}}.theme{{margin-top:10px}}}}
</style></head><body><main class='wrap'>
<header><div><h1>{_e(project['name'])} 진척 대시보드</h1><div class='sub'>{_e(project['candidate'])} · 기준일 {_e(project['report_date'])} · 설정 SHA-256 <code>{model['config_sha256'][:16]}…</code></div></div><button class='theme' id='theme' type='button'>화면 테마 전환</button></header>
<section class='cards'><article class='card'><span>실제 달성률</span><b>{_pct(model['actual_percent'])}</b></article><article class='card'><span>오늘 계획 달성률</span><b>{_pct(model['planned_percent'])}</b></article><article class='card'><span>당초 예정일</span><b>{_e(eta['initial_date'])}</b><small>최초 계획에서 동결</small></article><article class='card'><span>현재 예상일</span><b class='{delta_class}'>{_e(current_eta_text)}</b><small>{_e(eta_delta_text)}</small></article><article class='card'><span>남은 큰 단계</span><b>{model['remaining_milestones']}개</b></article></section>
{qr_block}
<section class='panel'><h2>영역별 실제와 계획</h2>{''.join(bars)}<p class='note'>색 막대=실제 · 회색 세로선=오늘 계획. 막대를 가리키거나 선택하면 증거 기반 완료·남은 항목을 봅니다.</p></section>
<section class='panel'><h2>일정 전망</h2><div class='gantt'>{''.join(gantt_rows)}<i class='today' aria-label='오늘'></i><i class='initial-target' aria-label='당초 예정일'></i>{current_line}</div><p class='legend'><span><b style='background:#d03b3b'></b>오늘</span><span><b style='background:#7c8791'></b>당초 예정일</span><span><b style='border-top:3px dashed #ed8b00'></b>현재 예상 완료</span></p><p class='note'>{_e(eta_method)} 현재 예상선: {'표시' if current_target else '측정 없음'}.</p></section>
<section class='panel'><h2>다음 출시 로드맵</h2><div class='roadmap'>{roadmap}</div></section>
<section class='panel'><h2>병목 경보</h2><div class='blockers'>{blockers}</div></section>
<section class='panel'><h2>계산표</h2><div class='scroll'><table><thead><tr><th>영역</th><th>가중치</th><th>계획 일정</th><th>오늘 계획</th><th>실제</th><th>차이</th><th>기여도</th></tr></thead><tbody>{''.join(table_rows)}</tbody><tfoot><tr><th>합계</th><td>100.0%</td><td>{_e(project['start_date'])}~{_e(project['target_date'])}</td><td>{_pct(model['planned_percent'])}</td><td>{_pct(model['actual_percent'])}</td><td>{model['actual_percent']-model['planned_percent']:+.1f}%p</td><td>{_pct(model['actual_percent'])}</td></tr></tfoot></table></div></section>
<section class='panel'><details open><summary><strong>용어 원장 — 어려운 말의 쉬운 뜻</strong></summary><dl class='terms'>{glossary}</dl></details></section>
<section class='panel note'><p><strong>기준선:</strong> {_e(model['baseline_note'])}</p><p><strong>산정 방식:</strong> {_e(model['method_note'])}</p><p><strong>현재 예상일 계산:</strong> {_e(eta_method)}</p><p>자기평가는 관대해지기 쉬워 근거 파일이 존재하는 완료 단계만 완료로 잡았습니다.</p></section>
<script id='dashboard-data' type='application/json'>{embedded}</script><script>(()=>{{const root=document.documentElement;document.getElementById('theme').addEventListener('click',()=>{{const dark=root.dataset.theme==='dark'||(!root.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);root.dataset.theme=dark?'light':'dark';}});}})();</script>
</main></body></html>"""


def _write_new(path: Path, data: bytes) -> None:
    path = path.resolve()
    if path.exists():
        raise DashboardError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_bytes(data)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def generated_summary(model: dict[str, Any], html_bytes: bytes) -> dict[str, Any]:
    return {
        "schema": model["schema"],
        "project": model["project"],
        "config_sha256": model["config_sha256"],
        "html_sha256": _sha256(html_bytes),
        "actual_percent": model["actual_percent"],
        "planned_percent": model["planned_percent"],
        "schedule_delta_days": model["schedule_delta_days"],
        "completed_milestones": model["completed_milestones"],
        "total_milestones": model["total_milestones"],
        "remaining_milestones": model["remaining_milestones"],
        "gantt_columns": model["gantt_columns"],
        "evidence_gate": "PASS",
        "eta": model["eta"],
        "public_app": None if model["public_app"] is None else {
            key: value for key, value in model["public_app"].items() if key != "qr_data_uri"
        },
        "roadmap": model["roadmap"],
        "bottleneck_matrix": model["bottlenecks"],
        "claims": {"implementation": True, "local": True, "public": False, "server": False, "device": False, "independent_user": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        config_path = args.config.resolve()
        config = load_config(config_path)
        project_root = config_path.parent.parent
        model = build_model(config, project_root)
        html_bytes = render_html(model).encode("utf-8")
        summary_bytes = (json.dumps(generated_summary(model, html_bytes), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if args.output.resolve() == args.summary_output.resolve():
            raise DashboardError("HTML and summary outputs must be different")
        if args.output.exists() or args.summary_output.exists():
            raise DashboardError("refusing to overwrite an existing output")
        _write_new(args.output, html_bytes)
        try:
            _write_new(args.summary_output, summary_bytes)
        except Exception:
            args.output.unlink(missing_ok=True)
            raise
    except DashboardError as exc:
        print(f"progress dashboard ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(generated_summary(model, html_bytes), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
