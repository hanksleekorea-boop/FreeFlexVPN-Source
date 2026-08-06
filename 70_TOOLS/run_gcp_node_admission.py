#!/usr/bin/env python3
"""첫 GCP exit 노드를 검증하고 R6 미완료 경계가 고정된 새 증거를 남긴다."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.control_runtime import build_runtime, load_runtime_settings  # noqa: E402
from app.gcp_node_admission import evaluate_gcp_admission, evaluate_gcp_configuration  # noqa: E402
from app.preflight_evidence import CANDIDATE_ID, sha256_file, validate_preflight_evidence  # noqa: E402


CONFIG_SCHEMA = "FreeFlexVPNGCPNodeConfigurationPreflightV1"


def _write_new(path: pathlib.Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(f"기존 증거 파일은 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="프로젝트 밖 단일 GCP nodes.json 절대 경로")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", help="새 증거 JSON 경로")
    parser.add_argument("--config-only", action="store_true", help="네트워크 요청 0건 설정검사")
    parser.add_argument("--config-evidence", help="실서버 모드가 요구하는 CONFIG READY 증거 절대 경로")
    args = parser.parse_args()
    if not CANDIDATE_ID.fullmatch(args.candidate_id):
        parser.error("candidate-id 형식이 올바르지 않습니다")
    if args.config_only and args.config_evidence:
        parser.error("--config-only에서는 --config-evidence를 사용하지 않습니다")
    if not args.config_only and not args.config_evidence:
        parser.error("실서버 admission은 --config-evidence 절대 경로가 필요합니다")

    config_path = pathlib.Path(args.config)
    settings = load_runtime_settings(config_path)
    config_sha256 = sha256_file(config_path)
    checked_at = datetime.now(timezone.utc)
    stamp = checked_at.strftime("%Y%m%dT%H%M%SZ")
    prefix = "GCP_NODE_CONFIG" if args.config_only else "GCP_NODE_ADMISSION"
    output = pathlib.Path(args.output) if args.output else ROOT / "60_OUTPUTS" / "checks" / f"{prefix}_{stamp}.json"
    if not output.is_absolute():
        output = (pathlib.Path.cwd() / output).resolve()

    if args.config_only:
        report = evaluate_gcp_configuration(settings.nodes, checked_at=checked_at)
    else:
        try:
            config_evidence_sha256 = validate_preflight_evidence(
                pathlib.Path(args.config_evidence),
                schema=CONFIG_SCHEMA,
                candidate_id=args.candidate_id,
                config_sha256=config_sha256,
                extra_required={"provider": "gcp", "r6_ready": False},
            )
        except ValueError as exc:
            parser.error(str(exc))
        with tempfile.TemporaryDirectory(prefix="ffvpn_gcp_admission_") as temp_dir:
            api, _adapter, poller = build_runtime(pathlib.Path(temp_dir) / "control.sqlite3", config_path)
            runtime_result = poller.run_once()
            catalog = api.catalog.public_catalog(now=checked_at)
            report = evaluate_gcp_admission(settings.nodes, runtime_result, catalog, checked_at=checked_at)
        report["configuration_evidence_sha256"] = config_evidence_sha256

    report["candidate_id"] = args.candidate_id
    report["config_sha256"] = config_sha256
    report["contains_secrets"] = False
    _write_new(output, report)
    if args.config_only:
        print(f"GCP 설정검사: {'CONFIGURATION READY' if report['configuration_ready'] else 'BLOCKED'} · 네트워크 요청 0")
        passed = report["configuration_ready"]
    else:
        print(f"GCP 첫 노드: {'ADMITTED' if report['admission_ready'] else 'BLOCKED'} · R6 READY=false")
        passed = report["admission_ready"]
    print(f"증거: {output}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
