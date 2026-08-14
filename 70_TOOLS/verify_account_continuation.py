#!/usr/bin/env python3
"""다른 Codex 계정의 같은-PC 인수를 비밀값 없이 읽기 전용 검증한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_HELPER = pathlib.Path.home() / ".codex" / "shared-continuity" / "account-independent-begin-v414.py"
EXPECTED_HELPER_BYTES = 11_497
EXPECTED_HELPER_SHA256 = "02fb55391fdb021e114a2457c68ef26b1a4056166b6f546b7314e50dd78de921"
EXPECTED_ORIGIN = "https://github.com/hanksleekorea-boop/FreeFlexVPN-Source.git"
REQUIRED_CONTINUITY = (
    "STATE.md",
    "HISTORY.md",
    "TEST_EVIDENCE.md",
    "SITE-CAPABILITIES.json",
    "PERMISSION-BASELINE.json",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def helper_identity(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "reason": "missing"}
    size = path.stat().st_size
    digest = sha256(path)
    return {
        "ok": size == EXPECTED_HELPER_BYTES and digest == EXPECTED_HELPER_SHA256,
        "bytes": size,
        "sha256": digest,
    }


def read_json(path: pathlib.Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def run(command: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )


def git_value(project: pathlib.Path, *args: str) -> tuple[bool, str]:
    result = run(["git", *args], project)
    return result.returncode == 0, result.stdout.strip()


def evaluate_permission(path: pathlib.Path, now: int | None = None) -> dict[str, Any]:
    current = int(time.time()) if now is None else now
    try:
        payload = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"status": "invalid", "capability_count": 0}
    expires = payload.get("expires_epoch")
    expired = not isinstance(expires, int) or expires <= current
    status = str(payload.get("status", "incomplete"))
    capabilities = payload.get("capabilities")
    count = len(capabilities) if isinstance(capabilities, list) else 0
    if expired:
        status = "expired"
    elif status != "complete":
        status = "incomplete"
    return {"status": status, "capability_count": count, "expires_epoch": expires}


def latest_valid_run(runs_dir: pathlib.Path) -> pathlib.Path | None:
    candidates = sorted(runs_dir.glob("RUN-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for candidate in candidates:
        try:
            if read_json(candidate).get("schema") == "ai-handoff-run/v414":
                return candidate
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return None


def verify(project: pathlib.Path, helper: pathlib.Path) -> dict[str, Any]:
    project = project.resolve()
    continuity = project / ".project-continuity"
    checks: list[dict[str, Any]] = []

    identity = helper_identity(helper)
    checks.append({"id": "helper_identity", **identity})

    missing = [name for name in REQUIRED_CONTINUITY if not (continuity / name).is_file()]
    checks.append({"id": "continuity_files", "ok": not missing, "missing": missing})

    locks = sorted(path.name for path in continuity.glob("LOCK*.json")) if continuity.is_dir() else []
    checks.append({"id": "collaboration_locks", "ok": not locks, "count": len(locks)})

    valid_run = latest_valid_run(continuity / "runs") if continuity.is_dir() else None
    checks.append({"id": "v414_run", "ok": valid_run is not None, "present": valid_run is not None})

    git_ok, before_status = git_value(project, "status", "--porcelain=v1")
    branch_ok, branch = git_value(project, "branch", "--show-current")
    head_ok, head = git_value(project, "rev-parse", "HEAD")
    origin_ok, origin = git_value(project, "remote", "get-url", "origin")
    checks.append({"id": "git_repository", "ok": git_ok and branch_ok and head_ok})
    checks.append({"id": "git_clean", "ok": git_ok and before_status == "", "changed_path_count": len(before_status.splitlines()) if before_status else 0})
    checks.append({"id": "origin", "ok": origin_ok and origin == EXPECTED_ORIGIN, "matches_expected": origin == EXPECTED_ORIGIN})

    helper_packet: dict[str, Any] = {}
    helper_ok = False
    if identity.get("ok"):
        helper_result = run(
            [sys.executable, "-X", "utf8", str(helper), "--project-path", str(project), "--mode", "ReadOnly"],
            project,
        )
        try:
            helper_packet = json.loads(helper_result.stdout.strip())
        except (json.JSONDecodeError, ValueError):
            helper_packet = {}
        helper_ok = (
            helper_result.returncode == 0
            and helper_packet.get("s") == "ai-handoff-hot-begin/v414"
            and helper_packet.get("c") == "READY"
            and helper_packet.get("w") == 0
        )
    checks.append({"id": "helper_readonly", "ok": helper_ok, "ready": helper_packet.get("c") == "READY", "writes": helper_packet.get("w")})

    after_ok, after_status = git_value(project, "status", "--porcelain=v1")
    checks.append({"id": "zero_write", "ok": after_ok and after_status == before_status})

    permission = evaluate_permission(continuity / "PERMISSION-BASELINE.json")
    site_status = "invalid"
    try:
        site = read_json(continuity / "SITE-CAPABILITIES.json")
        capabilities = site.get("capabilities", [])
        full_pass = isinstance(capabilities, list) and len(capabilities) == 18 and all(
            isinstance(item, dict) and item.get("status") == "pass" for item in capabilities
        )
        site_status = "complete" if site.get("status") == "complete" and full_pass else "incomplete"
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    provider_ready = permission["status"] == "complete" and site_status == "complete"

    local_ready = all(bool(item.get("ok")) for item in checks)
    return {
        "schema": "freeflexvpn-account-continuation/v1",
        "local_continuation": "ready" if local_ready else "hold",
        "full_site_development": "ready" if provider_ready else "hold",
        "provider_permission_parity": "complete" if provider_ready else permission["status"],
        "git": {"branch": branch if branch_ok else None, "head": head if head_ok else None},
        "checks": checks,
        "next_action": (
            "STATE.md의 다음 첫 행동부터 개발 계속; 외부 쓰기는 서비스별 readback 후 실행"
            if local_ready
            else "실패한 로컬 검사를 복구하고 다른 작업자의 변경은 보존"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-path", type=pathlib.Path, default=ROOT)
    parser.add_argument("--helper", type=pathlib.Path, default=DEFAULT_HELPER)
    parser.add_argument("--json", action="store_true", help="기계 판독용 JSON 한 줄 출력")
    args = parser.parse_args()
    result = verify(args.project_path, args.helper)
    output = json.dumps(result, ensure_ascii=False, separators=(",", ":") if args.json else None, indent=None if args.json else 2)
    print(output)
    return 0 if result["local_continuation"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
