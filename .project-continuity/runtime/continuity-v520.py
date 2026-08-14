from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


VERSION = "5.2"
HOT_SCHEMA = "ai-continuity-hot/v520"
CONFIG_SCHEMA = "ai-continuity-config/v500"
STATE_SCHEMA = "ai-continuity-state/v500"
MANIFEST_SCHEMA = "ai-continuity-manifest/v500"
BACKUP_SCHEMA = "ai-continuity-backup/v500"
LOCATOR_SCHEMA = "ai-continuity-drive-locators/v500"
PLAN_SCHEMA = "ai-continuity-cleanup-plan/v500"
INSTALL_SCHEMA = "ai-continuity-install-receipt/v520"
INSTALL_RESULT_SCHEMA = "ai-continuity-install-result/v520"
GITHUB_BASELINE_SCHEMA = "ai-continuity-github-access-baseline/v520"
GITHUB_STATUS_SCHEMA = "ai-continuity-github-access-status/v520"
RUNTIME_NAME = "continuity-v520.py"
POLICY_NAME = "POLICY-v5.2.md"
GITHUB_PERMISSION_KEYS = ("admin", "maintain", "push", "triage", "pull")
MARKER_BEGIN = "<!-- AI-CONTINUITY-V5 BEGIN -->"
MARKER_END = "<!-- AI-CONTINUITY-V5 END -->"
MAX_HOT_BYTES = 1024
MAX_CONTEXT_BYTES = 4096
DEFAULT_CHUNK_BYTES = 1024 * 1024 * 1024
LEGACY_LEASE_NAME = re.compile(r"^(?:lease(?:[-_.].+)?|leases|mutation[-_.]?lease(?:[-_.].+)?)$", re.IGNORECASE)
INTERNAL_TEMP_NAME = re.compile(r"^\..+\.tmp-[0-9a-f]{32}$")
SENSITIVE_NAMES = re.compile(r"(?:^|/)(?:\.env(?:\..*)?|[^/]+\.(?:pem|p12|pfx|key)|credentials?\.json|service[-_]?account[^/]*\.json|[^/]*\.(?:db|sql|sqlite3?|dump))$", re.IGNORECASE)
TRANSIENT_GIT = {"index.lock", "HEAD.lock", "config.lock", "packed-refs.lock", "shallow.lock"}
SAFE_CLEANUP_DIRS = (".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__", "build", "dist", ".next/cache", "node_modules/.cache")
SITE_CAPABILITY_IDS = (
    "analytics_read", "backup_read", "backup_write", "branch_create", "ci_read", "ci_run", "commit_create",
    "deployment_status_read", "domain_config_read", "hosting_config_read", "hosting_config_write", "preview_deploy",
    "production_deploy", "pull_request_manage", "rollback", "runtime_logs_read", "source_read", "source_write",
)
SITE_SEED = {"capabilities": [{"evidence": None, "id": item, "status": "unknown"} for item in SITE_CAPABILITY_IDS], "excluded": ["account_recovery", "billing", "credential_export", "member_admin", "ownership_transfer"], "profile": "full_site_development", "schema": "ai-handoff-site-capabilities/v500", "status": "unknown"}
PERMISSION_SEED = {"capabilities": [], "created_epoch": 0, "expires_epoch": None, "principal_strategy": "unconfigured", "profile": "development_parity", "project_ref": "unbound", "schema": "ai-handoff-permission-baseline/v500", "source_evidence_sha256": None, "status": "incomplete"}
GITHUB_STATUS_SEED = {"repo_id": None, "role": "UNKNOWN", "schema": GITHUB_STATUS_SCHEMA, "status": "UNKNOWN"}
VOLATILE_CONTINUITY = {
    ".project-continuity/STATE.json",
    ".project-continuity/CONTEXT.md",
    ".project-continuity/EVENTS.jsonl",
    ".project-continuity/BACKUPS.jsonl",
    ".project-continuity/BACKUP_LATEST.json",
    ".project-continuity/MANIFEST-LATEST.json",
    ".project-continuity/CLEANUP-PLAN.json",
}


def jcs(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_new(path: Path, content: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_replace(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_replace_if_changed(path: Path, content: bytes) -> bool:
    if path.is_file() and path.read_bytes() == content:
        return False
    atomic_replace(path, content)
    return True


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    raw = jcs(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "ab") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def strict_json_bytes(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in items:
            if key in output:
                raise ValueError("duplicate json key")
            output[key] = value
        return output

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("json object required")
    return value


def strict_json(path: Path) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes())


def ensure_inside(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("path outside project")
    return resolved


def run_tool(root: Path, name: str, *args: str, allow_fail: bool = False) -> bytes:
    executable = shutil.which(name)
    if not executable:
        if allow_fail:
            return b""
        raise FileNotFoundError(name)
    path = Path(executable).resolve()
    if path == root or root in path.parents:
        raise RuntimeError(f"project-local {name}")
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["LC_ALL"] = "C"
    proc = subprocess.run([str(path), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if proc.returncode and not allow_fail:
        raise RuntimeError(f"{name}:{proc.returncode}:{proc.stderr[:160].decode('utf-8', 'replace')}")
    return proc.stdout if proc.returncode == 0 else b""


def git(root: Path, *args: str, allow_fail: bool = False) -> bytes:
    return run_tool(root, "git", "-C", str(root), *args, allow_fail=allow_fail)


def project_id(root: Path) -> str:
    remote = git(root, "config", "--get", "remote.origin.url", allow_fail=True).strip()
    basis = remote if remote else str(root).encode("utf-8")
    return sha256_bytes(b"AI-CONTINUITY-PROJECT/v500\0" + basis)[:24]


def default_config(root: Path) -> dict[str, Any]:
    return {
        "backup_changed_bytes": 500000000,
        "backup_interval_hours": 24,
        "chunk_max_bytes": DEFAULT_CHUNK_BYTES,
        "cleanup_level": "moderate",
        "context_max_bytes": MAX_CONTEXT_BYTES,
        "drive_history": "all_immutable",
        "full_checkpoint_days": 30,
        "minimum_verified_copies_for_cleanup": 2,
        "project_id": project_id(root),
        "project_name": root.name,
        "protected_paths": [],
        "schema": CONFIG_SCHEMA,
    }


def default_state() -> dict[str, Any]:
    return {
        "archive_sha256": None,
        "backup_id": None,
        "blocked_reason": "DRIVE_NOT_CONFIGURED",
        "manifest_sha256": None,
        "next_action": "Google Drive 두 비공개 원격을 구성하고 provider 권한을 확인한다.",
        "remote_status": "UNKNOWN",
        "restore_verified": False,
        "schema": STATE_SCHEMA,
        "stage": "INIT",
        "updated_at_utc": utc_now(),
    }


def policy_text() -> str:
    return """# AI 지속개발·Drive·GitHub 권한 정책 v5.2

- 계정·대화 기억은 정본이 아니다. AGENTS.md, 프로젝트 파일, Git 상태, 이 폴더의 검증 기록만 정본이다.
- 협업 LOCK/장기 lease를 만들지 않는다. SQLite·Git·OS의 순간적 내부 잠금은 개발 소유권 잠금이 아니다.
- 백업은 불변 backup_id로 추가하며 Drive의 기존 세대를 자동 삭제·덮어쓰기하지 않는다.
- Drive 업로드 뒤 독립 다운로드·해시·복원 검증 전에는 일반 프로젝트 파일을 정리하지 않는다.
- 예약 maintain은 백업·검증·정리계획만 수행하고 cleanup-apply를 호출하지 않는다.
- 비밀번호·토큰·쿠키·MFA·복구코드·복호화 키·계정 원문을 프로젝트나 로그에 기록하지 않는다.
- 현재 소스, 루트 .git, 사용자 변경, 연속성 정본, 보호 경로, 판단 불가 파일은 정리하지 않는다.

## 매 세션의 빠른 경로

1. `runtime/continuity-v520.py bootstrap --compact`의 JCS 한 줄과 `CONTEXT.md`만 먼저 읽는다.
2. 현재 사용자 요청이 있으면 그것을, 없으면 `다음 첫 행동`을 수행한다.
3. 무변경 HOT에서는 이 정책·전체 사건·백업 이력을 다시 읽지 않는다.
4. 종료 전 `checkpoint`를 실행한다. 의미 변화가 없고 최신 복구가 READY면 기록·업로드·검사를 반복하지 않는다.
5. 설치 영수증이나 정본 해시가 다를 때만 COLD로 전환해 필요한 파일을 선택적으로 읽는다.

## 승인과 권한

- 읽기, 프로젝트 내부 편집, 비파괴 검사와 로컬 연속성 기록은 현재 개발 요청 범위에서 자동 수행한다.
- push/merge, 공개·운영 배포, 비용, DNS·secret·production data, 공개범위 변경, 일반 프로젝트 파일 삭제는 실제 provider 권한과 현재 승인을 모두 확인한다.
- ChatGPT/AI 계정 이름은 권한이 아니다. 같은 OS 사용자·파일 권한·provider principal의 실제 capability readback으로 판단한다.
- 자격증명은 복사하지 않는다. 다른 PC에서는 승인된 인증과 신뢰 자료가 없으면 외부 작업만 HOLD하고 로컬 개발은 계속한다.
- 최초 준비 AI는 사용자가 승인한 GitHub 로그인 상태에서 `github-bind --confirm-owner-baseline`을 한 번 실행해 저장소 ID와 권한 booleans만 기준선으로 기록한다.
- 이후 AI는 GitHub 로그인 뒤 `github-verify`를 실행한다. 같은 GitHub principal은 GitHub가 부여한 동일 권한으로 통과하며, 다른 principal은 동일 저장소 권한이 기준선 이상일 때만 통과한다.
- GitHub login·PAT·쿠키·numeric user ID·login 이름은 저장하지 않는다. 로그인만으로 임의 계정에 권한을 부여하지 않으며 부족하면 조직 team/협업자 권한 또는 승인된 principal 재로그인이 필요하다.
- Admin 동등성이 확인돼도 저장소 삭제·이전·가시성 변경·멤버 관리·secret 변경은 별도 현재 승인을 요구한다.

## 백업과 PC 경량화

- Drive A/B에 full→delta→tombstone 불변 세대를 추가하고 COMPLETE를 마지막에 쓴다.
- 두 원격 각각 재다운로드·해시·임시 복원을 통과해야 READY다. 하나는 PARTIAL, 둘 실패는 BLOCKED다.
- 민감 파일은 프로젝트 밖 키를 쓰는 승인된 암호화 원격 두 개가 아니면 업로드하지 않는다.
- 로컬에는 활성 프로젝트, 최신 매니페스트 한 벌, 세대별 소형 영수증만 유지한다.
- 일반 정리는 대화형 plan hash, Drive A/B READY, 최신 복원 PASS, 후보 불변을 모두 확인한 뒤 격리→postcheck→제거한다. 예약 실행은 삭제하지 않는다.

## 충돌·복구·정직한 경계

- 다른 작업자의 현재 bytes를 덮지 않는다. 비중첩 변경은 병합하고 중첩 변경은 patch로 보존한다.
- COMPLETE 없는 준비물은 최신으로 승격하지 않는다. 손상·중단은 기존 성공 세대를 보존한 채 재시도한다.
- 실제 Drive privacy/readback, 다른 계정 수락, 예약 설치, macOS/Linux, provider 권한은 실행 증거가 없으면 NOT_RUN/UNKNOWN이다.
- 구조적 준비와 실제 외부 권한 상속을 구분하며, 전체 무오류나 권한 자동 복제를 주장하지 않는다.
"""


def agents_block() -> str:
    return f"""{MARKER_BEGIN}
시작: `python .project-continuity/runtime/continuity-v520.py bootstrap --project-path <workspace> --compact`; 출력+CONTEXT만 읽고 현재 요청(없으면 next)을 계속한다.
종료: 같은 실행기의 `checkpoint`. runtime/schema/복구/보안 이상 때만 POLICY-v5.2와 필요한 증거를 읽으며 원래 프롬프트는 다시 읽지 않는다.
정본은 사용자 요청>프로젝트·Git>STATE>검증 Drive>대화다. 협업 LOCK과 타인 bytes 덮어쓰기는 금지한다.
GitHub 작업 전 `github-verify`; 외부·파괴·비용 작업은 실제 권한+현재 승인이 필요하다. 예약은 `maintain --non-destructive`만 허용하며 삭제하지 않는다.
{MARKER_END}"""


def ensure_agents(root: Path) -> int:
    path = root / "AGENTS.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if MARKER_BEGIN in existing or MARKER_END in existing:
        if existing.count(MARKER_BEGIN) != 1 or existing.count(MARKER_END) != 1:
            raise RuntimeError("AGENTS marker conflict")
        start = existing.index(MARKER_BEGIN)
        end = existing.index(MARKER_END, start) + len(MARKER_END)
        expected = agents_block()
        if existing[start:end] == expected:
            return 0
        updated = existing[:start] + expected + existing[end:]
        atomic_replace(root / "AGENTS.md", updated.encode("utf-8"))
        return 1
    joined = existing.rstrip() + ("\n\n" if existing.strip() else "") + agents_block() + "\n"
    atomic_replace(path, joined.encode("utf-8"))
    return 1


def ensure_safe_layout(root: Path) -> None:
    continuity = root / ".project-continuity"
    if continuity.is_symlink() or (continuity.exists() and continuity.resolve() != continuity.absolute()):
        raise RuntimeError("redirected continuity")
    for relative in ("runtime", "runs", "local", "local/staging", "local/restore-tests"):
        path = continuity / relative
        if path.is_symlink() or (path.exists() and path.resolve() != path.absolute()):
            raise RuntimeError("redirected continuity child")


def install_receipt(runtime: bytes) -> dict[str, Any]:
    return {
        "agents_block_sha256": sha256_bytes(agents_block().encode("utf-8")),
        "policy_sha256": sha256_bytes(policy_text().encode("utf-8")),
        "runtime_bytes": len(runtime),
        "runtime_sha256": sha256_bytes(runtime),
        "schema": INSTALL_SCHEMA,
        "version": VERSION,
    }


def installed_fast(root: Path, runtime_source: Path) -> bool:
    continuity = root / ".project-continuity"
    receipt_path = continuity / "INSTALL-RECEIPT.json"
    runtime_path = continuity / "runtime" / RUNTIME_NAME
    policy_path = continuity / POLICY_NAME
    required = ("CONFIG.json", "STATE.json", "EVENTS.jsonl", "BACKUPS.jsonl", "SITE-CAPABILITIES.json", "PERMISSION-BASELINE.json", "GITHUB-ACCESS.json")
    if not receipt_path.is_file() or not runtime_path.is_file() or not policy_path.is_file() or any(not (continuity / name).is_file() for name in required):
        return False
    receipt = strict_json(receipt_path)
    source = runtime_source.read_bytes()
    expected = install_receipt(source)
    if receipt != expected or receipt_path.read_bytes() != jcs(expected):
        return False
    if runtime_path.read_bytes() != source or sha256_file(policy_path) != expected["policy_sha256"]:
        return False
    agents = (root / "AGENTS.md").read_text(encoding="utf-8") if (root / "AGENTS.md").is_file() else ""
    if agents.count(MARKER_BEGIN) != 1 or agents.count(MARKER_END) != 1 or agents_block() not in agents:
        return False
    if strict_json(continuity / "CONFIG.json").get("schema") != CONFIG_SCHEMA or strict_json(continuity / "STATE.json").get("schema") != STATE_SCHEMA:
        return False
    return True


def install(root: Path, runtime_source: Path | None = None) -> int:
    ensure_safe_layout(root)
    continuity = root / ".project-continuity"
    if runtime_source and runtime_source.is_file() and installed_fast(root, runtime_source):
        writes = retire_legacy(continuity)
        writes += int(render_context(root))
        return writes
    for relative in ("runtime", "runs", "local", "local/staging", "local/restore-tests", "local/legacy-locks"):
        (continuity / relative).mkdir(parents=True, exist_ok=True)
    writes = 0
    writes += int(atomic_new(continuity / POLICY_NAME, policy_text().encode("utf-8")))
    writes += int(atomic_new(continuity / "CONFIG.json", jcs(default_config(root))))
    writes += int(atomic_new(continuity / "STATE.json", jcs(default_state())))
    writes += int(atomic_new(continuity / "EVENTS.jsonl", b""))
    writes += int(atomic_new(continuity / "BACKUPS.jsonl", b""))
    writes += int(atomic_replace_if_changed(continuity / "SCHEMA_VERSION", b"5.2\n"))
    writes += int(atomic_new(continuity / "SITE-CAPABILITIES.json", jcs(SITE_SEED)))
    writes += int(atomic_new(continuity / "PERMISSION-BASELINE.json", jcs(PERMISSION_SEED)))
    writes += int(atomic_new(continuity / "GITHUB-ACCESS.json", jcs(GITHUB_STATUS_SEED)))
    if runtime_source and runtime_source.is_file():
        target = continuity / "runtime" / RUNTIME_NAME
        source = runtime_source.read_bytes()
        if target.exists() and target.read_bytes() != source:
            raise RuntimeError("runtime conflict")
        writes += int(atomic_new(target, source))
    writes += ensure_agents(root)
    writes += retire_legacy(continuity)
    writes += int(render_context(root))
    if runtime_source and runtime_source.is_file():
        receipt = install_receipt(runtime_source.read_bytes())
        writes += int(atomic_replace_if_changed(continuity / "INSTALL-RECEIPT.json", jcs(receipt)))
    return writes


def retire_legacy(continuity: Path) -> int:
    candidates = list(continuity.glob("LOCK*.json"))
    local = continuity / "local"
    if local.is_dir():
        candidates.extend(path for path in local.iterdir() if path.is_dir() and LEGACY_LEASE_NAME.fullmatch(path.name))
    moved = 0
    for source in candidates:
        target_dir = local / "legacy-locks"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{source.name}.retired-{uuid.uuid4().hex}"
        try:
            source.rename(target)
            moved += 1
        except OSError:
            if source.exists():
                raise
    return moved


def read_state(root: Path) -> dict[str, Any]:
    path = root / ".project-continuity" / "STATE.json"
    return strict_json(path) if path.is_file() else default_state()


def github_status(root: Path) -> dict[str, Any]:
    path = root / ".project-continuity" / "GITHUB-ACCESS.json"
    value = strict_json(path) if path.is_file() else dict(GITHUB_STATUS_SEED)
    if set(value) != {"repo_id", "role", "schema", "status"} or value.get("schema") != GITHUB_STATUS_SCHEMA:
        raise ValueError("github status schema")
    if value.get("status") not in ("UNKNOWN", "READY", "BLOCKED") or value.get("role") not in ("UNKNOWN", "READ", "TRIAGE", "WRITE", "MAINTAIN", "ADMIN"):
        raise ValueError("github status value")
    if value.get("repo_id") is not None and (not isinstance(value["repo_id"], int) or isinstance(value["repo_id"], bool) or value["repo_id"] <= 0):
        raise ValueError("github status repo")
    if value["status"] == "READY" and (value["repo_id"] is None or value["role"] == "UNKNOWN"):
        raise ValueError("github ready status evidence")
    if value["status"] == "UNKNOWN" and (value["repo_id"] is not None or value["role"] != "UNKNOWN"):
        raise ValueError("github unknown status evidence")
    return value


def github_role(permissions: dict[str, bool]) -> str:
    for key, role in (("admin", "ADMIN"), ("maintain", "MAINTAIN"), ("push", "WRITE"), ("triage", "TRIAGE"), ("pull", "READ")):
        if permissions.get(key) is True:
            return role
    return "UNKNOWN"


def github_snapshot(root: Path) -> dict[str, Any]:
    view = strict_json_bytes(run_tool(root, "gh", "repo", "view", "--json", "nameWithOwner"))
    if set(view) != {"nameWithOwner"} or not isinstance(view["nameWithOwner"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", view["nameWithOwner"]):
        raise ValueError("github repo view")
    repository = strict_json_bytes(run_tool(root, "gh", "api", f"repos/{view['nameWithOwner']}"))
    required = {"id", "full_name", "private", "permissions"}
    if not required.issubset(repository) or not isinstance(repository["id"], int) or isinstance(repository["id"], bool) or repository["id"] <= 0:
        raise ValueError("github repository identity")
    if not isinstance(repository["full_name"], str) or repository["full_name"].lower() != view["nameWithOwner"].lower() or not isinstance(repository["private"], bool):
        raise ValueError("github repository binding")
    raw_permissions = repository["permissions"]
    if not isinstance(raw_permissions, dict) or set(raw_permissions) != set(GITHUB_PERMISSION_KEYS) or any(not isinstance(raw_permissions[key], bool) for key in GITHUB_PERMISSION_KEYS):
        raise ValueError("github permissions")
    permissions = {key: raw_permissions[key] for key in GITHUB_PERMISSION_KEYS}
    return {
        "permissions": permissions,
        "private": repository["private"],
        "repo_id": repository["id"],
        "repo_name_sha256": sha256_bytes(repository["full_name"].lower().encode("utf-8")),
        "role": github_role(permissions),
    }


def validate_github_baseline(value: dict[str, Any], raw: bytes | None = None) -> dict[str, Any]:
    required = {"minimum_permissions", "private", "repo_id", "repo_name_sha256", "role", "schema"}
    if set(value) != required or value.get("schema") != GITHUB_BASELINE_SCHEMA or (raw is not None and raw != jcs(value)):
        raise ValueError("github baseline schema")
    if not isinstance(value["repo_id"], int) or isinstance(value["repo_id"], bool) or value["repo_id"] <= 0 or not isinstance(value["private"], bool):
        raise ValueError("github baseline repo")
    if not isinstance(value["repo_name_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["repo_name_sha256"]):
        raise ValueError("github baseline name")
    permissions = value["minimum_permissions"]
    if not isinstance(permissions, dict) or set(permissions) != set(GITHUB_PERMISSION_KEYS) or any(not isinstance(permissions[key], bool) for key in GITHUB_PERMISSION_KEYS):
        raise ValueError("github baseline permissions")
    if value["role"] != github_role(permissions) or value["role"] == "UNKNOWN":
        raise ValueError("github baseline role")
    return value


def github_bind(root: Path, confirmed: bool) -> tuple[dict[str, Any], int]:
    if not confirmed:
        return {"c": "HOLD", "g": "UNKNOWN", "n": "OWNER_BASELINE_CONFIRMATION_REQUIRED", "s": GITHUB_STATUS_SCHEMA, "w": 0}, 4
    snapshot = github_snapshot(root)
    if snapshot["role"] == "UNKNOWN":
        return {"c": "HOLD", "g": "BLOCKED", "n": "GITHUB_REPOSITORY_ACCESS_REQUIRED", "s": GITHUB_STATUS_SCHEMA, "w": 0}, 5
    baseline = {
        "minimum_permissions": snapshot["permissions"],
        "private": snapshot["private"],
        "repo_id": snapshot["repo_id"],
        "repo_name_sha256": snapshot["repo_name_sha256"],
        "role": snapshot["role"],
        "schema": GITHUB_BASELINE_SCHEMA,
    }
    path = root / ".project-continuity" / "GITHUB-ACCESS-BASELINE.json"
    if path.exists():
        current = validate_github_baseline(strict_json(path), path.read_bytes())
        if current != baseline:
            return {"c": "HOLD", "g": "BLOCKED", "n": "GITHUB_BASELINE_CONFLICT", "s": GITHUB_STATUS_SCHEMA, "w": 0}, 6
        return github_verify(root)
    writes = int(atomic_new(path, jcs(baseline)))
    if not writes:
        return github_verify(root)
    status = {"repo_id": snapshot["repo_id"], "role": snapshot["role"], "schema": GITHUB_STATUS_SCHEMA, "status": "READY"}
    writes += int(atomic_replace_if_changed(root / ".project-continuity" / "GITHUB-ACCESS.json", jcs(status)))
    return {"c": "READY", "g": "READY", "role": snapshot["role"], "s": GITHUB_STATUS_SCHEMA, "w": writes}, 0


def github_verify(root: Path) -> tuple[dict[str, Any], int]:
    path = root / ".project-continuity" / "GITHUB-ACCESS-BASELINE.json"
    if not path.is_file():
        return {"c": "HOLD", "g": "UNKNOWN", "n": "GITHUB_BASELINE_REQUIRED", "s": GITHUB_STATUS_SCHEMA, "w": 0}, 4
    baseline = validate_github_baseline(strict_json(path), path.read_bytes())
    snapshot = github_snapshot(root)
    same_repository = baseline["repo_id"] == snapshot["repo_id"] and baseline["repo_name_sha256"] == snapshot["repo_name_sha256"] and baseline["private"] == snapshot["private"]
    permission_superset = all(not baseline["minimum_permissions"][key] or snapshot["permissions"][key] for key in GITHUB_PERMISSION_KEYS)
    ready = same_repository and permission_superset
    status = {"repo_id": baseline["repo_id"], "role": snapshot["role"], "schema": GITHUB_STATUS_SCHEMA, "status": "READY" if ready else "BLOCKED"}
    writes = int(atomic_replace_if_changed(root / ".project-continuity" / "GITHUB-ACCESS.json", jcs(status)))
    result = {"c": "READY" if ready else "HOLD", "g": status["status"], "role": snapshot["role"], "s": GITHUB_STATUS_SCHEMA, "w": writes}
    if not ready:
        result["n"] = "LOGIN_APPROVED_GITHUB_PRINCIPAL_OR_GRANT_EQUIVALENT_ROLE"
    return result, 0 if ready else 7


def write_state(root: Path, **updates: Any) -> dict[str, Any]:
    state = read_state(root)
    state.update(updates)
    state["schema"] = STATE_SCHEMA
    state["updated_at_utc"] = utc_now()
    atomic_replace(root / ".project-continuity" / "STATE.json", jcs(state))
    render_context(root, state)
    return state


def render_context(root: Path, state: dict[str, Any] | None = None) -> bool:
    state = state or read_state(root)
    lines = [
        "# CONTEXT v5.2",
        f"stage={state.get('stage', 'INIT')}",
        f"backup={state.get('backup_id') or '-'}",
        f"drive={state.get('remote_status', 'UNKNOWN')}",
        f"github={github_status(root).get('status', 'UNKNOWN')}",
        f"block={state.get('blocked_reason') or '-'}",
        f"next={state.get('next_action') or '현재 사용자 요청 계속'}",
    ]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    if len(raw) > MAX_CONTEXT_BYTES:
        raise RuntimeError("context too large")
    return atomic_replace_if_changed(root / ".project-continuity" / "CONTEXT.md", raw)


def should_exclude(relative: str) -> bool:
    if relative in VOLATILE_CONTINUITY or relative.startswith(".project-continuity/local/") or relative.startswith(".project-continuity/runs/"):
        return True
    name = relative.rsplit("/", 1)[-1]
    if relative.startswith(".git/") and name in TRANSIENT_GIT:
        return True
    if relative.startswith(".project-continuity/") and INTERNAL_TEMP_NAME.fullmatch(name):
        return True
    return False


def file_record(root: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink():
        target = os.readlink(path)
        payload = target.encode("utf-8")
        return {"kind": "symlink", "mode": 0, "path": relative, "sha256": sha256_bytes(payload), "size": len(payload), "target": target}
    info = path.stat()
    return {"kind": "file", "mode": stat.S_IMODE(info.st_mode), "path": relative, "sha256": sha256_file(path), "size": info.st_size}


def scan_manifest(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(dirs):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if should_exclude(relative + "/placeholder"):
                continue
            if path.is_symlink():
                records.append(file_record(root, path))
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if should_exclude(relative):
                continue
            records.append(file_record(root, path))
    records.sort(key=lambda item: item["path"].encode("utf-8"))
    core = {"files": records, "project_id": project_id(root), "schema": MANIFEST_SCHEMA}
    core["manifest_sha256"] = sha256_bytes(jcs(core))
    core["total_bytes"] = sum(int(item["size"]) for item in records)
    return core


def manifest_map(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    return {item["path"]: item for item in manifest.get("files", [])}


def latest_manifest(root: Path) -> dict[str, Any] | None:
    path = root / ".project-continuity" / "MANIFEST-LATEST.json"
    return strict_json(path) if path.is_file() else None


def semantic_digest(root: Path) -> tuple[str, str | None]:
    if (root / ".git").exists():
        head_raw = git(root, "rev-parse", "HEAD", allow_fail=True).strip()
        branch = git(root, "symbolic-ref", "--short", "-q", "HEAD", allow_fail=True).strip()
        cached = git(root, "diff", "--cached", "--binary", "HEAD", "--", allow_fail=True) if head_raw else git(root, "diff", "--cached", "--binary", "--", allow_fail=True)
        unstaged = git(root, "diff", "--binary", "--", allow_fail=True)
        untracked = git(root, "ls-files", "-o", "--exclude-standard", "-z", allow_fail=True)
        digest = hashlib.sha256(b"AI-CONTINUITY-HOT/v500\0")
        for raw in (head_raw, branch, cached, unstaged):
            digest.update(len(raw).to_bytes(8, "big")); digest.update(raw)
        for raw_path in sorted(part for part in untracked.split(b"\0") if part and not part.startswith(b".project-continuity/local/")):
            path = root / raw_path.decode("utf-8", "strict")
            if path.is_file() or path.is_symlink():
                record = jcs(file_record(root, path)); digest.update(len(record).to_bytes(8, "big")); digest.update(record)
        return digest.hexdigest(), head_raw.decode("ascii") if head_raw else None
    manifest = scan_manifest(root)
    return str(manifest["manifest_sha256"]), None


def utf8_limit(value: str, maximum: int) -> str:
    output: list[str] = []
    used = 0
    for char in value:
        raw = char.encode("utf-8")
        if used + len(raw) > maximum:
            break
        output.append(char); used += len(raw)
    return "".join(output)


def hot_packet(root: Path, writes: int = 0) -> dict[str, Any]:
    state = read_state(root)
    digest, _head = semantic_digest(root)
    packet = {
        "c": "READY" if not state.get("blocked_reason") else "DEGRADED",
        "d": digest,
        "g": github_status(root).get("status", "UNKNOWN"),
        "n": utf8_limit(str(state.get("next_action") or "현재 사용자 요청 계속"), 160),
        "r": state.get("remote_status", "UNKNOWN"),
        "s": HOT_SCHEMA,
        "w": writes,
    }
    if len(jcs(packet)) + 1 > MAX_HOT_BYTES:
        raise RuntimeError("hot packet too large")
    return packet


def install_result(writes: int) -> dict[str, Any]:
    return {"c": "INSTALLED", "n": "RUN_BOOTSTRAP", "s": INSTALL_RESULT_SCHEMA, "w": writes}


def load_locators(root: Path) -> dict[str, Any] | None:
    path = root / ".project-continuity" / "local" / "DRIVE-LOCATORS.json"
    return strict_json(path) if path.is_file() else None


def validate_remote(remote: dict[str, Any], test_mode: bool) -> None:
    if set(remote) != {"id", "kind", "private_evidence_sha256", "root"}:
        raise ValueError("remote schema")
    if remote["id"] not in ("drive-a", "drive-b") or remote["kind"] not in ("rclone", "rclone_crypt", "file"):
        raise ValueError("remote kind")
    if remote["kind"] == "file" and not test_mode:
        raise ValueError("file remote is test-only")
    if not isinstance(remote["root"], str) or not remote["root"]:
        raise ValueError("remote root")
    if not isinstance(remote["private_evidence_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", remote["private_evidence_sha256"]):
        raise ValueError("privacy evidence")


def validate_privacy_receipt(path: Path, remote_id: str, expected_project_id: str) -> dict[str, Any]:
    receipt = strict_json(path)
    required = {"evidence_sha256", "private", "project_id", "provider", "public_links", "remote_id", "schema", "verified_at_utc"}
    if set(receipt) != required:
        raise ValueError("privacy receipt schema")
    if receipt["schema"] != "ai-continuity-drive-privacy/v500" or receipt["provider"] != "google-drive":
        raise ValueError("privacy receipt provider")
    if receipt["remote_id"] != remote_id or receipt["project_id"] != expected_project_id:
        raise ValueError("privacy receipt binding")
    if receipt["private"] is not True or receipt["public_links"] != 0:
        raise ValueError("Drive is not private")
    if not isinstance(receipt["verified_at_utc"], str) or not receipt["verified_at_utc"].endswith("Z"):
        raise ValueError("privacy receipt time")
    if not isinstance(receipt["evidence_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["evidence_sha256"]):
        raise ValueError("privacy evidence hash")
    return receipt


def configure(root: Path, args: argparse.Namespace) -> int:
    if not args.remote_a or not args.remote_b:
        raise ValueError("two Drive remotes required")
    config = strict_json(root / ".project-continuity" / "CONFIG.json")
    project_ref = str(config["project_id"])
    remotes = []
    privacy_receipts = []
    inputs = (
        ("drive-a", args.remote_a, args.privacy_evidence_a, args.privacy_receipt_a),
        ("drive-b", args.remote_b, args.privacy_evidence_b, args.privacy_receipt_b),
    )
    for remote_id, value, evidence, receipt_path in inputs:
        if args.test_mode:
            evidence_hash = evidence or ""
        else:
            if not receipt_path:
                raise ValueError("provider privacy receipt required")
            receipt = validate_privacy_receipt(Path(receipt_path), remote_id, project_ref)
            privacy_receipts.append(receipt)
            evidence_hash = sha256_bytes(jcs(receipt))
        suffix = "/" + project_ref
        bound_root = value.rstrip("/\\") if value.rstrip("/\\").endswith(project_ref) else value.rstrip("/\\") + suffix
        item = {"id": remote_id, "kind": args.remote_kind, "private_evidence_sha256": evidence_hash, "root": bound_root}
        validate_remote(item, args.test_mode)
        remotes.append(item)
    value = {"remotes": remotes, "schema": LOCATOR_SCHEMA, "test_mode": bool(args.test_mode)}
    path = root / ".project-continuity" / "local" / "DRIVE-LOCATORS.json"
    atomic_replace(path, jcs(value))
    if privacy_receipts:
        atomic_replace(root / ".project-continuity" / "DRIVE-PRIVACY.json", jcs({"receipts": privacy_receipts, "schema": "ai-continuity-drive-privacy-set/v500"}))
    write_state(root, blocked_reason=None, next_action="현재 사용자 요청을 계속하고 종료 전 checkpoint를 실행한다.", remote_status="CONFIGURED", stage="DISCOVERED")
    return 1


def remote_path(remote: dict[str, Any], relative: str) -> str:
    root = remote["root"].rstrip("/\\")
    return f"{root}/{relative}"


def put_remote(root: Path, remote: dict[str, Any], source: Path, relative: str, test_mode: bool) -> None:
    validate_remote(remote, test_mode)
    if remote["kind"] == "file":
        target = Path(remote["root"]) / PurePosixPath(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256_file(target) != sha256_file(source):
                raise RuntimeError("immutable remote conflict")
            return
        temporary = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex}"
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
        return
    run_tool(root, "rclone", "copyto", str(source), remote_path(remote, relative), "--immutable")


def get_remote(root: Path, remote: dict[str, Any], relative: str, target: Path, test_mode: bool) -> None:
    validate_remote(remote, test_mode)
    target.parent.mkdir(parents=True, exist_ok=True)
    if remote["kind"] == "file":
        shutil.copyfile(Path(remote["root"]) / PurePosixPath(relative), target)
        return
    run_tool(root, "rclone", "copyto", remote_path(remote, relative), str(target), "--immutable")


def zip_info(name: str, mode: int = 0o600) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    return info


def partition(records: list[dict[str, Any]], maximum: int) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    size = 0
    for record in records:
        item_size = int(record["size"])
        if item_size > maximum:
            raise RuntimeError("single file streaming adapter required")
        if current and size + item_size > maximum:
            groups.append(current); current = []; size = 0
        current.append(record); size += item_size
    if current or not groups:
        groups.append(current)
    return groups


def create_chunk(root: Path, records: list[dict[str, Any]], target: Path) -> None:
    with zipfile.ZipFile(target, "w", allowZip64=True) as archive:
        for record in records:
            path = root / PurePosixPath(record["path"])
            if record["kind"] == "symlink":
                payload = str(record["target"]).encode("utf-8")
                if sha256_bytes(payload) != record["sha256"]:
                    raise RuntimeError("source changed during backup")
                archive.writestr(zip_info(record["path"], int(record["mode"])), payload)
            else:
                if sha256_file(path) != record["sha256"]:
                    raise RuntimeError("source changed before backup")
                archive.write(path, record["path"], compress_type=zipfile.ZIP_DEFLATED)
                if sha256_file(path) != record["sha256"]:
                    raise RuntimeError("source changed during backup")


def verify_chunk(path: Path, records: list[dict[str, Any]]) -> None:
    expected = {item["path"]: item for item in records}
    with zipfile.ZipFile(path, "r") as archive:
        if set(archive.namelist()) != set(expected):
            raise RuntimeError("chunk entry set")
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or "\\" in info.filename:
                raise RuntimeError("unsafe chunk path")
            if info.file_size != int(expected[info.filename]["size"]):
                raise RuntimeError("chunk size")
            digest = hashlib.sha256()
            with archive.open(info, "r") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected[info.filename]["sha256"]:
                raise RuntimeError("chunk content hash")


def sensitive_paths(manifest: dict[str, Any]) -> list[str]:
    return [item["path"] for item in manifest["files"] if SENSITIVE_NAMES.search(item["path"])]


def read_backup_records(root: Path) -> list[dict[str, Any]]:
    runs = root / ".project-continuity" / "runs"
    run_records = []
    if runs.is_dir():
        for path in sorted(runs.glob("*.json"), key=lambda item: item.name.encode("utf-8")):
            value = strict_json(path)
            if value.get("schema") == BACKUP_SCHEMA:
                run_records.append(value)
    if run_records:
        return run_records
    path = root / ".project-continuity" / "BACKUPS.jsonl"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def backup_chain(records: list[dict[str, Any]], latest: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {item["backup_id"]: item for item in records}
    by_id[latest["backup_id"]] = latest
    chain: list[dict[str, Any]] = []
    current = latest
    seen: set[str] = set()
    while current:
        backup_id = current["backup_id"]
        if backup_id in seen:
            raise RuntimeError("backup cycle")
        seen.add(backup_id); chain.append(current)
        parent = current.get("parent_backup_id")
        if parent is None:
            break
        if parent not in by_id:
            raise RuntimeError("backup parent missing")
        current = by_id[parent]
    chain.reverse()
    if not chain or chain[0].get("kind") != "full":
        raise RuntimeError("full root missing")
    return chain


def download_file_checked(root: Path, remote: dict[str, Any], relative: str, expected_sha: str, temp: Path, test_mode: bool) -> Path:
    target = temp / Path(PurePosixPath(relative)).name
    get_remote(root, remote, relative, target, test_mode)
    if sha256_file(target) != expected_sha:
        raise RuntimeError("remote readback hash")
    return target


def restore_test(root: Path, latest: dict[str, Any], remote: dict[str, Any], test_mode: bool, extra_records: list[dict[str, Any]] | None = None) -> bool:
    records = read_backup_records(root)
    if extra_records:
        records.extend(extra_records)
    chain = backup_chain(records, latest)
    with tempfile.TemporaryDirectory(prefix="continuity-restore-") as temp_name:
        temp = Path(temp_name)
        restored = temp / "project"
        restored.mkdir()
        final_manifest: dict[str, Any] | None = None
        for record in chain:
            base = f"backups/{record['backup_id']}"
            complete_path = download_file_checked(root, remote, f"{base}/COMPLETE.json", record["complete_sha256"], temp, test_mode)
            complete = strict_json(complete_path)
            if complete.get("backup_id") != record["backup_id"] or complete.get("backup_json_sha256") != record["backup_json_sha256"] or complete.get("manifest_file_sha256") != record["manifest_file_sha256"]:
                raise RuntimeError("complete marker binding")
            metadata_path = download_file_checked(root, remote, f"{base}/BACKUP.json", record["backup_json_sha256"], temp, test_mode)
            metadata = strict_json(metadata_path)
            if metadata["backup_id"] != record["backup_id"] or metadata["manifest_sha256"] != record["manifest_sha256"]:
                raise RuntimeError("backup metadata binding")
            manifest_path = download_file_checked(root, remote, f"{base}/MANIFEST.json", record["manifest_file_sha256"], temp, test_mode)
            remote_manifest = strict_json(manifest_path)
            if remote_manifest.get("manifest_sha256") != record["manifest_sha256"]:
                raise RuntimeError("remote manifest binding")
            final_manifest = remote_manifest
            for relative in metadata.get("tombstones", []):
                target = ensure_inside(restored, restored / PurePosixPath(relative))
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                elif target.exists() or target.is_symlink():
                    target.unlink()
            for chunk in metadata["chunks"]:
                chunk_path = download_file_checked(root, remote, f"{base}/{chunk['name']}", chunk["sha256"], temp, test_mode)
                verify_chunk(chunk_path, chunk["records"])
                with zipfile.ZipFile(chunk_path, "r") as archive:
                    for info in archive.infolist():
                        target = ensure_inside(restored, restored / PurePosixPath(info.filename))
                        target.parent.mkdir(parents=True, exist_ok=True)
                        item = next(x for x in chunk["records"] if x["path"] == info.filename)
                        if item["kind"] == "symlink":
                            payload = archive.read(info)
                            link_target = payload.decode("utf-8")
                            resolved_link = (target.parent / link_target).resolve()
                            if resolved_link != restored.resolve() and restored.resolve() not in resolved_link.parents:
                                raise RuntimeError("external symlink restore")
                            if target.exists() or target.is_symlink():
                                target.unlink()
                            os.symlink(link_target, target, target_is_directory=False)
                        else:
                            digest = hashlib.sha256()
                            with archive.open(info, "r") as source, target.open("wb") as destination:
                                for block in iter(lambda: source.read(1024 * 1024), b""):
                                    digest.update(block); destination.write(block)
                            if digest.hexdigest() != item["sha256"]:
                                raise RuntimeError("restore stream hash")
                            try:
                                os.chmod(target, int(item["mode"]))
                            except OSError:
                                pass
        if final_manifest is None:
            raise RuntimeError("final manifest missing")
        final_map = manifest_map(final_manifest)
        for relative, expected in final_map.items():
            path = restored / PurePosixPath(relative)
            if expected["kind"] == "symlink":
                if not path.is_symlink() or sha256_bytes(os.readlink(path).encode("utf-8")) != expected["sha256"]:
                    return False
            elif not path.is_file() or sha256_file(path) != expected["sha256"]:
                return False
        actual = scan_manifest_for_restore(restored)
        if set(actual) != set(final_map):
            return False
        if (restored / ".git").exists():
            git(restored, "fsck", "--full")
            git(restored, "show-ref", "--head")
        return True


def scan_manifest_for_restore(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in dirs:
            path = current_path / name
            if path.is_symlink():
                output[path.relative_to(root).as_posix()] = file_record(root, path)
            else:
                kept.append(name)
        dirs[:] = kept
        for name in files:
            path = current_path / name
            output[path.relative_to(root).as_posix()] = file_record(root, path)
    return output


def checkpoint(root: Path, non_destructive: bool = False) -> tuple[dict[str, Any], int]:
    locators = load_locators(root)
    if not locators or locators.get("schema") != LOCATOR_SCHEMA or len(locators.get("remotes", [])) != 2:
        state = write_state(root, blocked_reason="DRIVE_ACCESS_REQUIRED", next_action="운영체제 사용자 범위의 Google Drive 원격 두 개를 구성한다.", remote_status="BLOCKED", stage="BLOCKED")
        return state, 4
    test_mode = bool(locators.get("test_mode"))
    remotes = locators["remotes"]
    for remote in remotes:
        validate_remote(remote, test_mode)
    before = scan_manifest(root)
    previous = latest_manifest(root)
    prior_state = read_state(root)
    if previous and previous.get("manifest_sha256") == before["manifest_sha256"] and prior_state.get("remote_status") == "READY" and prior_state.get("restore_verified") is True:
        return read_state(root), 0
    sensitive = sensitive_paths(before)
    if sensitive and not all(item["kind"] == "rclone_crypt" for item in remotes):
        state = write_state(root, blocked_reason="ENCRYPTED_REMOTE_REQUIRED", next_action="민감 파일 원문을 보존할 rclone crypt 원격 두 개를 구성한다.", remote_status="BLOCKED", stage="BLOCKED")
        return state, 5
    previous_map = manifest_map(previous)
    current_map = manifest_map(before)
    full_due = previous is None or prior_state.get("remote_status") != "READY" or prior_state.get("restore_verified") is not True
    if not full_due:
        latest_state = read_state(root)
        stamp = latest_state.get("last_full_epoch", 0)
        config = strict_json(root / ".project-continuity" / "CONFIG.json")
        full_due = int(time.time()) - int(stamp or 0) >= int(config["full_checkpoint_days"]) * 86400
    if full_due:
        changed = list(current_map.values()); tombstones: list[str] = []; kind = "full"; parent = None
    else:
        changed = [item for path, item in current_map.items() if previous_map.get(path) != item]
        tombstones = sorted(set(previous_map) - set(current_map), key=lambda value: value.encode("utf-8"))
        kind = "delta"; parent = read_state(root).get("backup_id")
    config = strict_json(root / ".project-continuity" / "CONFIG.json")
    groups = partition(changed, int(config["chunk_max_bytes"]))
    run_id = uuid.uuid4().hex
    backup_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + before["manifest_sha256"][:12] + "-" + run_id[:8]
    stage = root / ".project-continuity" / "local" / "staging" / backup_id
    stage.mkdir(parents=True, exist_ok=False)
    chunk_meta: list[dict[str, Any]] = []
    remote_ok = {item["id"]: True for item in remotes}
    try:
        for index, group in enumerate(groups):
            name = f"chunk-{index:05d}.zip"
            chunk = stage / name
            create_chunk(root, group, chunk)
            verify_chunk(chunk, group)
            chunk_sha = sha256_file(chunk)
            item = {"name": name, "records": group, "sha256": chunk_sha, "size": chunk.stat().st_size}
            chunk_meta.append(item)
            for remote in remotes:
                if not remote_ok[remote["id"]]:
                    continue
                try:
                    put_remote(root, remote, chunk, f"backups/{backup_id}/{name}", test_mode)
                    check = stage / f"readback-{remote['id']}-{name}"
                    get_remote(root, remote, f"backups/{backup_id}/{name}", check, test_mode)
                    if sha256_file(check) != chunk_sha:
                        raise RuntimeError("chunk readback mismatch")
                    check.unlink()
                except Exception:
                    remote_ok[remote["id"]] = False
            chunk.unlink()
        after = scan_manifest(root)
        if after["manifest_sha256"] != before["manifest_sha256"]:
            raise RuntimeError("project changed during backup")
        metadata = {
            "backup_id": backup_id,
            "chunks": chunk_meta,
            "created_at_utc": utc_now(),
            "kind": kind,
            "manifest_sha256": before["manifest_sha256"],
            "parent_backup_id": parent,
            "project_id": config["project_id"],
            "schema": BACKUP_SCHEMA,
            "tombstones": tombstones,
        }
        metadata_path = stage / "BACKUP.json"
        manifest_path = stage / "MANIFEST.json"
        atomic_replace(metadata_path, jcs(metadata))
        atomic_replace(manifest_path, jcs(before))
        metadata_sha = sha256_file(metadata_path)
        manifest_file_sha = sha256_file(manifest_path)
        for remote in remotes:
            if not remote_ok[remote["id"]]:
                continue
            try:
                for local, name, expected in ((metadata_path, "BACKUP.json", metadata_sha), (manifest_path, "MANIFEST.json", manifest_file_sha)):
                    put_remote(root, remote, local, f"backups/{backup_id}/{name}", test_mode)
                    check = stage / f"readback-{remote['id']}-{name}"
                    get_remote(root, remote, f"backups/{backup_id}/{name}", check, test_mode)
                    if sha256_file(check) != expected:
                        raise RuntimeError("metadata readback mismatch")
                    check.unlink()
            except Exception:
                remote_ok[remote["id"]] = False
        complete = {"backup_id": backup_id, "backup_json_sha256": metadata_sha, "chunks": [item["sha256"] for item in chunk_meta], "manifest_file_sha256": manifest_file_sha, "schema": "ai-continuity-complete/v500"}
        complete_path = stage / "COMPLETE.json"
        atomic_replace(complete_path, jcs(complete))
        complete_sha = sha256_file(complete_path)
        for remote in remotes:
            if not remote_ok[remote["id"]]:
                continue
            try:
                put_remote(root, remote, complete_path, f"backups/{backup_id}/COMPLETE.json", test_mode)
                check = stage / f"readback-{remote['id']}-COMPLETE.json"
                get_remote(root, remote, f"backups/{backup_id}/COMPLETE.json", check, test_mode)
                if sha256_file(check) != complete_sha:
                    raise RuntimeError("complete readback mismatch")
                check.unlink()
            except Exception:
                remote_ok[remote["id"]] = False
        verified = [item for item in remotes if remote_ok[item["id"]]]
        record = {
            "backup_id": backup_id,
            "backup_json_sha256": metadata_sha,
            "complete_sha256": complete_sha,
            "kind": kind,
            "manifest_file_sha256": manifest_file_sha,
            "manifest_sha256": before["manifest_sha256"],
            "parent_backup_id": parent,
            "remote_ids": [item["id"] for item in verified],
            "restore_verified": False,
            "schema": BACKUP_SCHEMA,
        }
        restored_remotes: list[dict[str, Any]] = []
        for remote in verified:
            try:
                if restore_test(root, record, remote, test_mode, [record]):
                    restored_remotes.append(remote)
            except Exception:
                pass
        restore_ok = bool(restored_remotes)
        record["remote_ids"] = [item["id"] for item in restored_remotes]
        record["restore_verified"] = len(restored_remotes) == 2
        status = "READY" if len(restored_remotes) == 2 else "PARTIAL" if restored_remotes else "BLOCKED"
        if not atomic_new(root / ".project-continuity" / "runs" / f"{backup_id}.json", jcs(record)):
            raise RuntimeError("duplicate immutable run")
        append_jsonl(root / ".project-continuity" / "BACKUPS.jsonl", record)
        append_jsonl(root / ".project-continuity" / "EVENTS.jsonl", {"backup_id": backup_id, "event": "checkpoint", "remote_status": status, "restore_verified": restore_ok, "time": utc_now()})
        atomic_replace(root / ".project-continuity" / "MANIFEST-LATEST.json", jcs(before))
        atomic_replace(root / ".project-continuity" / "BACKUP_LATEST.json", jcs(record))
        updates: dict[str, Any] = {
            "archive_sha256": sha256_bytes(jcs([item["sha256"] for item in chunk_meta])),
            "backup_id": backup_id,
            "blocked_reason": None if status == "READY" else "DRIVE_REDUNDANCY_OR_RESTORE_INCOMPLETE",
            "manifest_sha256": before["manifest_sha256"],
            "next_action": "현재 사용자 요청을 계속한다." if status == "READY" else "Drive 복제·재다운로드·복원 검증을 복구한다.",
            "remote_status": status,
            "restore_verified": len(restored_remotes) == 2,
            "stage": "COMPLETE" if status == "READY" else "BLOCKED",
        }
        if kind == "full":
            updates["last_full_epoch"] = int(time.time())
        state = write_state(root, **updates)
        return state, 0 if status == "READY" else 6
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def verify_latest(root: Path) -> tuple[dict[str, Any], int]:
    latest_path = root / ".project-continuity" / "BACKUP_LATEST.json"
    locators = load_locators(root)
    if not latest_path.is_file() or not locators:
        return write_state(root, blocked_reason="NO_VERIFIABLE_BACKUP", stage="BLOCKED"), 4
    latest = strict_json(latest_path)
    test_mode = bool(locators.get("test_mode"))
    passed = []
    for remote in locators["remotes"]:
        try:
            passed.append(remote["id"] if restore_test(root, latest, remote, test_mode) else None)
        except Exception:
            passed.append(None)
    count = sum(item is not None for item in passed)
    status = "READY" if count == 2 else "PARTIAL" if count else "BLOCKED"
    state = write_state(root, remote_status=status, restore_verified=count > 0, blocked_reason=None if status == "READY" else "VERIFY_FAILED", stage="COMPLETE" if status == "READY" else "BLOCKED")
    return state, 0 if status == "READY" else 6


def tree_fingerprint(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256(b"AI-CONTINUITY-CLEANUP/v500\0")
    total = 0
    for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        if any((current_path / name).is_symlink() for name in dirs):
            raise RuntimeError("cleanup symlink")
        for name in sorted(files):
            item = current_path / name
            if item.is_symlink():
                raise RuntimeError("cleanup symlink")
            relative = item.relative_to(path).as_posix().encode("utf-8")
            value = sha256_file(item).encode("ascii")
            digest.update(len(relative).to_bytes(4, "big") + relative + value)
            total += item.stat().st_size
    return digest.hexdigest(), total


def cleanup_plan(root: Path) -> tuple[dict[str, Any], int]:
    state = read_state(root)
    if state.get("remote_status") != "READY" or not state.get("restore_verified"):
        return write_state(root, blocked_reason="CLEANUP_REQUIRES_TWO_VERIFIED_COPIES", stage="BLOCKED"), 7
    config = strict_json(root / ".project-continuity" / "CONFIG.json")
    protected = {str(PurePosixPath(item)) for item in config.get("protected_paths", [])}
    candidates = []
    for relative in SAFE_CLEANUP_DIRS:
        path = root / PurePosixPath(relative)
        if not path.is_dir() or path.is_symlink() or any(relative == item or relative.startswith(item + "/") for item in protected):
            continue
        ensure_inside(root, path)
        tracked = git(root, "ls-files", "--", relative, allow_fail=True).strip() if (root / ".git").exists() else b""
        if tracked:
            continue
        fingerprint, size = tree_fingerprint(path)
        candidates.append({"fingerprint": fingerprint, "path": relative, "reason": "recreatable_cache_or_build", "size": size})
    current = scan_manifest(root)
    candidate_prefixes = tuple(item["path"] + "/" for item in candidates)
    keep_files = [item for item in current["files"] if item["path"] not in {candidate["path"] for candidate in candidates} and not item["path"].startswith(candidate_prefixes)]
    keep_fingerprint = sha256_bytes(jcs(keep_files))
    value = {"backup_id": state.get("backup_id"), "candidates": candidates, "created_at_utc": utc_now(), "keep_fingerprint": keep_fingerprint, "project_id": config["project_id"], "schema": PLAN_SCHEMA}
    value["plan_sha256"] = sha256_bytes(jcs(value))
    atomic_replace(root / ".project-continuity" / "CLEANUP-PLAN.json", jcs(value))
    write_state(root, cleanup_bytes=sum(item["size"] for item in candidates), cleanup_plan_sha256=value["plan_sha256"], next_action="필요하면 검증된 정리계획을 대화형으로 승인한다.", stage="CLEANUP_READY")
    return value, 0


def cleanup_apply(root: Path, confirmation: str | None, non_destructive: bool) -> tuple[dict[str, Any], int]:
    if non_destructive:
        return write_state(root, blocked_reason="SCHEDULED_DELETE_FORBIDDEN", stage="BLOCKED"), 7
    plan_path = root / ".project-continuity" / "CLEANUP-PLAN.json"
    if not plan_path.is_file():
        return write_state(root, blocked_reason="CLEANUP_PLAN_REQUIRED", stage="BLOCKED"), 7
    plan = strict_json(plan_path)
    if confirmation != plan.get("plan_sha256"):
        return write_state(root, blocked_reason="INTERACTIVE_CONFIRMATION_REQUIRED", stage="BLOCKED"), 7
    state = read_state(root)
    if state.get("remote_status") != "READY" or not state.get("restore_verified") or state.get("backup_id") != plan.get("backup_id"):
        return write_state(root, blocked_reason="CLEANUP_BACKUP_BINDING", stage="BLOCKED"), 7
    candidates = plan["candidates"]
    for item in candidates:
        path = root / PurePosixPath(item["path"])
        ensure_inside(root, path)
        if not path.is_dir() or path.is_symlink():
            return write_state(root, blocked_reason="CLEANUP_CANDIDATE_MISSING", stage="BLOCKED"), 7
        current, _ = tree_fingerprint(path)
        if current != item["fingerprint"]:
            return write_state(root, blocked_reason="CLEANUP_CANDIDATE_CHANGED", stage="BLOCKED"), 7
    trash = root / ".project-continuity" / "local" / "cleanup-trash" / str(plan["plan_sha256"])
    trash.mkdir(parents=True, exist_ok=False)
    moved: list[tuple[Path, Path, dict[str, Any]]] = []
    try:
        for item in candidates:
            source = root / PurePosixPath(item["path"])
            target = trash / PurePosixPath(item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            moved.append((source, target, item))
        current = scan_manifest(root)
        current_keep = sha256_bytes(jcs(current["files"]))
        locators = load_locators(root)
        test_failure = bool(locators and locators.get("test_mode") and os.environ.get("CONTINUITY_TEST_POSTCHECK_FAIL") == "1")
        if current_keep != plan.get("keep_fingerprint") or test_failure:
            raise RuntimeError("cleanup postcheck")
        removed = sum(int(item["size"]) for _, _, item in moved)
        shutil.rmtree(trash)
        for _, _, item in moved:
            append_jsonl(root / ".project-continuity" / "EVENTS.jsonl", {"event": "cleanup_item", "path": item["path"], "size": item["size"], "time": utc_now()})
        state = write_state(root, blocked_reason=None, cleanup_bytes=removed, next_action="현재 사용자 요청을 계속한다.", stage="POSTCHECKED")
        return state, 0
    except Exception:
        rollback_conflict = False
        for source, target, _ in reversed(moved):
            if source.exists() or source.is_symlink():
                rollback_conflict = True
                continue
            source.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                os.replace(target, source)
        if not rollback_conflict:
            shutil.rmtree(trash, ignore_errors=True)
        reason = "ROLLBACK_CONFLICT" if rollback_conflict else "POSTCHECK_FAILED_ROLLED_BACK"
        return write_state(root, blocked_reason=reason, next_action="정리 실패 증거를 확인하고 복구 상태를 검증한다.", stage="ROLLED_BACK" if not rollback_conflict else "BLOCKED"), 8


def status(root: Path) -> dict[str, Any]:
    return hot_packet(root, 0)


def schedule_spec(root: Path) -> dict[str, Any]:
    runtime = root / ".project-continuity" / "runtime" / RUNTIME_NAME
    return {
        "argv": [sys.executable, str(runtime), "maintain", "--project-path", str(root), "--non-destructive"],
        "destructive": False,
        "interval_hours": 24,
        "platform": sys.platform,
        "project_id": strict_json(root / ".project-continuity" / "CONFIG.json")["project_id"],
        "schema": "ai-continuity-schedule-spec/v500",
        "scope": "current_os_user",
    }


def simulate() -> dict[str, Any]:
    failures = []
    states = 0
    deletes = 0
    for bits in range(1 << 10):
        states += 1
        remote_a, remote_b, restore, interactive, confirm, inside, protected, unchanged, scheduled, private = [bool(bits & (1 << index)) for index in range(10)]
        delete = remote_a and remote_b and restore and interactive and confirm and inside and not protected and unchanged and not scheduled and private
        deletes += int(delete)
        if delete and not all((remote_a, remote_b, restore, interactive, confirm, inside, unchanged, private)):
            failures.append(bits)
        if delete and (protected or scheduled):
            failures.append(bits)
    return {"all_pass": not failures, "delete_states": deletes, "failures": failures, "schema": "ai-continuity-simulation/v500", "states": states}


def normalize_root(value: str) -> Path:
    supplied = Path(value)
    if not supplied.exists():
        raise FileNotFoundError("project path")
    root = supplied.resolve()
    return root.parent if root.is_file() else root


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("command", choices=("install", "configure", "bootstrap", "github-bind", "github-verify", "checkpoint", "backup", "verify", "restore-test", "cleanup-plan", "cleanup-apply", "maintain", "schedule-spec", "simulate", "status"))
    value.add_argument("--project-path", default=".")
    value.add_argument("--compact", action="store_true")
    value.add_argument("--non-destructive", action="store_true")
    value.add_argument("--remote-a")
    value.add_argument("--remote-b")
    value.add_argument("--remote-kind", choices=("rclone", "rclone_crypt", "file"), default="rclone")
    value.add_argument("--privacy-evidence-a")
    value.add_argument("--privacy-evidence-b")
    value.add_argument("--privacy-receipt-a")
    value.add_argument("--privacy-receipt-b")
    value.add_argument("--test-mode", action="store_true")
    value.add_argument("--confirm-plan-sha256")
    value.add_argument("--confirm-owner-baseline", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    if args.command == "simulate":
        print(jcs(simulate()).decode("utf-8")); return 0
    try:
        root = normalize_root(args.project_path)
        if args.command == "install":
            writes = install(root, Path(__file__).resolve())
            result, code = install_result(writes), 0
        elif args.command == "configure":
            install(root, Path(__file__).resolve())
            writes = configure(root, args)
            result, code = hot_packet(root, writes), 0
        elif args.command == "bootstrap":
            writes = install(root, Path(__file__).resolve())
            result, code = hot_packet(root, writes), 0
        elif args.command == "github-bind":
            install(root, Path(__file__).resolve())
            result, code = github_bind(root, args.confirm_owner_baseline)
        elif args.command == "github-verify":
            install(root, Path(__file__).resolve())
            result, code = github_verify(root)
        elif args.command in ("checkpoint", "backup"):
            install(root, Path(__file__).resolve())
            state, code = checkpoint(root, args.non_destructive)
            result = hot_packet(root, 0)
        elif args.command in ("verify", "restore-test"):
            install(root, Path(__file__).resolve())
            state, code = verify_latest(root)
            result = hot_packet(root, 0)
        elif args.command == "cleanup-plan":
            install(root, Path(__file__).resolve())
            plan, code = cleanup_plan(root)
            result = {"c": "READY" if code == 0 else "HOLD", "count": len(plan.get("candidates", [])), "s": PLAN_SCHEMA, "sha256": plan.get("plan_sha256"), "w": 1 if code == 0 else 0}
        elif args.command == "cleanup-apply":
            install(root, Path(__file__).resolve())
            state, code = cleanup_apply(root, args.confirm_plan_sha256, args.non_destructive)
            result = hot_packet(root, 0)
        elif args.command == "maintain":
            install(root, Path(__file__).resolve())
            state, code = checkpoint(root, True)
            if code == 0:
                cleanup_plan(root)
            result = hot_packet(root, 0)
        elif args.command == "schedule-spec":
            install(root, Path(__file__).resolve())
            result, code = schedule_spec(root), 0
        else:
            install(root, Path(__file__).resolve())
            result, code = status(root), 0
    except Exception as exc:
        result = {"c": "HOLD", "d": None, "g": "BLOCKED", "n": f"RUNTIME_ERROR:{type(exc).__name__}", "r": "BLOCKED", "s": HOT_SCHEMA, "w": -1}
        code = 3
        print(f"continuity runtime error: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(jcs(result).decode("utf-8"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
