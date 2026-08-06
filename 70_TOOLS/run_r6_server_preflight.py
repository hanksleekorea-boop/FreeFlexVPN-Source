#!/usr/bin/env python3
"""외부 nodes.json의 R6 실서버 준비도를 검사하고 비밀값 없는 증거 JSON을 남긴다."""
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
from app.preflight_evidence import (  # noqa: E402
    CANDIDATE_ID,
    MAX_EVIDENCE_BYTES,
    sha256_file,
    validate_preflight_evidence,
)
from app.r6_preflight import evaluate_configuration_preflight, evaluate_r6_preflight  # noqa: E402


CONFIG_EVIDENCE_SCHEMA = "FreeFlexVPNR6ConfigurationPreflightV1"


def _sha256(path: pathlib.Path) -> str:
    return sha256_file(path)


def validate_configuration_evidence(
    path: pathlib.Path, *, candidate_id: str, config_sha256: str
) -> str:
    """실서버 연결 전에 설정검사 증거가 같은 후보·같은 설정인지 확인한다."""
    return validate_preflight_evidence(
        path,
        schema=CONFIG_EVIDENCE_SCHEMA,
        candidate_id=candidate_id,
        config_sha256=config_sha256,
    )


def _atomic_write_new(path: pathlib.Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(f"기존 증거 파일은 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="프로젝트 밖 nodes.json 절대 경로")
    parser.add_argument("--candidate-id", required=True, help="예: R6-candidate-20260802-01")
    parser.add_argument("--output", help="새 증거 JSON 경로. 생략 시 버전 파일을 자동 생성")
    parser.add_argument(
        "--config-only", action="store_true",
        help="SSH 네트워크 요청 없이 설정 구조·2공급자 분산만 검사",
    )
    parser.add_argument(
        "--config-evidence",
        help="실서버 모드가 요구하는 직전 CONFIG READY 증거 JSON 절대 경로",
    )
    args = parser.parse_args()
    if not CANDIDATE_ID.fullmatch(args.candidate_id):
        parser.error("candidate-id는 영문·숫자로 시작하는 6~80자의 영문·숫자·점·밑줄·하이픈이어야 합니다")
    if args.config_only and args.config_evidence:
        parser.error("--config-only에서는 --config-evidence를 사용하지 않습니다")
    if not args.config_only and not args.config_evidence:
        parser.error("실서버 모드는 --config-evidence 절대 경로가 필요합니다")

    config_path = pathlib.Path(args.config)
    settings = load_runtime_settings(config_path)
    config_sha256 = _sha256(config_path)
    checked_at = datetime.now(timezone.utc)
    stamp = checked_at.strftime("%Y%m%dT%H%M%SZ")
    prefix = "R6_CONFIG_PREFLIGHT" if args.config_only else "R6_SERVER_PREFLIGHT"
    output = pathlib.Path(args.output) if args.output else ROOT / "60_OUTPUTS" / "checks" / f"{prefix}_{stamp}.json"
    if not output.is_absolute():
        output = (pathlib.Path.cwd() / output).resolve()

    if args.config_only:
        report = evaluate_configuration_preflight(settings.nodes, checked_at=checked_at)
    else:
        evidence_path = pathlib.Path(args.config_evidence)
        try:
            configuration_evidence_sha256 = validate_configuration_evidence(
                evidence_path,
                candidate_id=args.candidate_id,
                config_sha256=config_sha256,
            )
        except ValueError as exc:
            parser.error(str(exc))
        with tempfile.TemporaryDirectory(prefix="ffvpn_r6_preflight_") as temp_dir:
            db_path = pathlib.Path(temp_dir) / "control.sqlite3"
            api, _adapter, poller = build_runtime(db_path, config_path)
            runtime_result = poller.run_once()
            catalog = api.catalog.public_catalog(now=checked_at)
            report = evaluate_r6_preflight(settings.nodes, runtime_result, catalog, checked_at=checked_at)
        report["configuration_evidence_sha256"] = configuration_evidence_sha256

    report["candidate_id"] = args.candidate_id
    report["config_sha256"] = config_sha256
    report["contains_secrets"] = False
    _atomic_write_new(output, report)
    if args.config_only:
        print(f"R6 설정 사전점검: {'CONFIGURATION READY' if report['configuration_ready'] else 'BLOCKED'}")
        print(f"노드: configured={report['configured_nodes']} providers={report['distinct_providers']} · 네트워크 요청 0")
    else:
        print(f"R6 실서버 사전점검: {'PASS' if report['ready'] else 'BLOCKED'}")
        print(f"노드: configured={report['configured_nodes']} healthy={report['healthy_nodes']} public={report['public_nodes']}")
    print(f"증거: {output}")
    passed = report["configuration_ready"] if args.config_only else report["ready"]
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
