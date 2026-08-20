#!/usr/bin/env python3
"""실제 검사 전, 프로젝트 밖에 안전한 증거 영수증 초안을 만든다.

이 도구는 통과 증거를 만들지 않는다. 모든 관찰값은 ``not_run``으로 시작하고,
운영자 또는 검사자가 실제 검사 뒤 비식별 원본을 추가해야만 95% 게이트가
통과할 수 있다. 따라서 경로·키·IP·계정·기기 식별값을 코드 보관소에 남기지
않으면서도 Android/PC/운영 점검의 같은 형식을 반복해서 사용할 수 있다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.platform_evidence import OBSERVATION_IDS, SCHEMA as PLATFORM_SCHEMA  # noqa: E402
from app.release_95_gate import OPERATIONS_GATES, SCHEMA as RELEASE_SCHEMA  # noqa: E402
from app.readiness_99_gate import DEVELOPMENT_GATES, SCHEMA as READINESS_99_SCHEMA  # noqa: E402


def _is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    return path == parent or parent in path.parents


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_directory(raw: str) -> pathlib.Path:
    destination = pathlib.Path(raw).expanduser()
    if destination.exists() and destination.is_symlink():
        raise ValueError("출력 폴더는 심볼릭 링크일 수 없습니다")
    destination = destination.resolve()
    if _is_within(destination, ROOT):
        raise ValueError("증거 묶음은 프로젝트 밖의 새 빈 폴더에만 만들 수 있습니다")
    if destination.exists() and not destination.is_dir():
        raise ValueError("출력 경로는 폴더여야 합니다")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("출력 폴더는 비어 있어야 하며 기존 파일을 덮어쓰지 않습니다")
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _write(destination: pathlib.Path, name: str, text: str) -> tuple[str, str]:
    target = destination / name
    target.write_text(text, encoding="utf-8", newline="\n")
    return name, _sha256(target)


def _platform_guide(platform: str) -> str:
    return "\n".join((
        "FreeFlexVPN 비식별 실제 플랫폼 증거 수집 안내", "",
        f"대상: {platform}",
        "이 파일은 검사 계획이며 통과 증거가 아닙니다.",
        "기록 금지: 개인키, 사전공유키, 설정 전문, 계정, 이메일, 기기 ID, 실제 IP·주소, 토큰.",
        "실제 검사 뒤 각 통과 항목에는 별도의 비식별 로그·화면·측정 원본을 추가합니다.",
        "관찰 순서: 공식 클라이언트 설치 → 새 후보 프로필 가져오기 → 실제 터널 연결 →",
        "DNS 확인 → 웹 확인 → 서버 최신 연결 확인 → 해제 뒤 인터넷 복구 → 최종 안전 상태.",
        "기존 Android ffvpn 프로필은 삭제·덮어쓰기·수정하지 않습니다.",
        "영수증의 상태를 pass로 바꾸기 전에는 해당 원본의 SHA-256과 관찰 항목을 artifacts에 추가합니다.",
        "완료 후 evaluate_platform_evidence.py로 검증합니다.",
        "",
    ))


def _operations_guide() -> str:
    return "\n".join((
        "FreeFlexVPN 95% 출시 후보 운영 증거 수집 안내", "",
        "이 파일은 검사 계획이며 상업 운영 통과 선언이 아닙니다.",
        "기록 금지: 계정·이메일·토큰·비밀번호·개인키·실제 IP·결제수단·고객 식별값.",
        "실제 원본은 접근성, 개인정보/보안, 지원/복구, 결제, 환불, 법무, 감시, 제한 공개별로",
        "비식별화해 추가하고, 해당 gate_ids와 SHA-256을 operations-evidence.json에 결속합니다.",
        "LIMITED_RELEASE는 95점 후보에는 not_run일 수 있으나 100점 상업 운영 판정에는 pass가 필요합니다.",
        "완료 후 evaluate_release_95.py로 모바일·PC 영수증과 함께 검증합니다.",
        "",
    ))


def _development_guide() -> str:
    return "\n".join((
        "FreeFlexVPN 99% 목표 개발 증거 수집 안내", "",
        "이 파일은 검사 계획이며 개발 완료 선언이 아닙니다.",
        "기록 금지: 계정·이메일·토큰·비밀번호·개인키·실제 IP·기기 식별값.",
        "REGRESSION, MANIFEST, SECRET_SCAN, PUBLIC_BUILD의 실제 결과를 비식별 원본으로 추가하고,",
        "각 통과 항목의 SHA-256과 gate_ids를 development-evidence.json에 결속합니다.",
        "모바일·PC·상용 운영 증거는 별도 영수증으로 계속 검증해야 합니다.",
        "완료 후 evaluate_readiness_99.py로 네 증거 묶음을 함께 검증합니다.", "",
    ))


def build_platform(destination: pathlib.Path, platform: str) -> dict[str, Any]:
    guide_name, guide_sha = _write(destination, "capture-guide.txt", _platform_guide(platform))
    payload = {
        "schema": PLATFORM_SCHEMA,
        "platform": platform,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "observations": {item: "not_run" for item in OBSERVATION_IDS},
        "artifacts": [{
            "artifact_id": "capture-guide-001",
            "kind": "log",
            "observation_ids": ["CLIENT_INSTALLED"],
            "contains_secret": False,
            "contains_identifier": False,
            "path": guide_name,
            "sha256": guide_sha,
        }],
    }
    (destination / "platform-evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {"kind": "platform", "platform": platform, "ready": False, "status": "template_created"}


def build_operations(destination: pathlib.Path) -> dict[str, Any]:
    guide_name, guide_sha = _write(destination, "capture-guide.txt", _operations_guide())
    payload = {
        "schema": RELEASE_SCHEMA,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "gates": {item: "not_run" for item in OPERATIONS_GATES},
        "artifacts": [{
            "artifact_id": "capture-guide-001",
            "kind": "document",
            "gate_ids": ["ACCESSIBILITY"],
            "contains_secret": False,
            "contains_identifier": False,
            "path": guide_name,
            "sha256": guide_sha,
        }],
    }
    (destination / "operations-evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {"kind": "operations", "ready": False, "status": "template_created"}


def build_development(destination: pathlib.Path) -> dict[str, Any]:
    guide_name, guide_sha = _write(destination, "capture-guide.txt", _development_guide())
    payload = {
        "schema": READINESS_99_SCHEMA,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "gates": {item: "not_run" for item in DEVELOPMENT_GATES},
        "artifacts": [{
            "artifact_id": "capture-guide-001", "kind": "document", "gate_ids": ["REGRESSION"],
            "contains_secret": False, "contains_identifier": False, "path": guide_name, "sha256": guide_sha,
        }],
    }
    (destination / "development-evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {"kind": "development", "ready": False, "status": "template_created"}


def main() -> int:
    parser = argparse.ArgumentParser(description="프로젝트 밖 비식별 출시 증거 초안 생성")
    parser.add_argument("kind", choices=("platform", "operations", "development"))
    parser.add_argument("--output-dir", required=True, help="프로젝트 밖의 새 빈 폴더")
    parser.add_argument("--platform", choices=("android", "ios", "windows", "macos", "linux"))
    args = parser.parse_args()
    if args.kind == "platform" and not args.platform:
        parser.error("platform에는 --platform이 필요합니다")
    if args.kind in {"operations", "development"} and args.platform:
        parser.error("operations/development에는 --platform을 함께 쓸 수 없습니다")
    try:
        destination = _prepare_directory(args.output_dir)
        if args.kind == "platform":
            result = build_platform(destination, args.platform)
        elif args.kind == "operations":
            result = build_operations(destination)
        else:
            result = build_development(destination)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
