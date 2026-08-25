#!/usr/bin/env python3
"""Constrained server-side workspace for password collaboration sessions."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


MAX_FILE_BYTES = 512 * 1024
MAX_SEARCH_RESULTS = 100
WRITE_PREFIXES = ("20_SRC/", "40_TESTS/", "00_START/")
READ_BLOCKED_PARTS = {".git", ".test-venv", ".chrome-ci", ".chrome-ci2", ".project-continuity", "60_OUTPUTS"}
WRITE_BLOCKED_PREFIXES = (".github/", ".project-continuity/", "70_TOOLS/", "30_DEPLOY/", "90_ARCHIVE/")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
    re.compile(r"gh[opusr]_[A-Za-z0-9]{20,}"),
)
_QUERY = re.compile(r"^[^\x00-\x1f]{1,120}$")
_MESSAGE = re.compile(r"^[^\r\n\x00]{3,100}$")


class WorkspaceError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class SafeWorkspace:
    root: Path
    session_branch: str

    def __post_init__(self) -> None:
        resolved = self.root.resolve()
        if not (resolved / ".git").exists():
            raise ValueError("세션 작업공간은 Git worktree 또는 clone이어야 합니다")
        object.__setattr__(self, "root", resolved)
        if not self.session_branch.startswith("ai-session/"):
            raise ValueError("세션 브랜치는 ai-session/ 아래여야 합니다")

    def _path(self, value: str, *, write: bool = False) -> tuple[str, Path]:
        if not isinstance(value, str) or "\\" in value:
            raise WorkspaceError(400, "INVALID_PATH", "POSIX 상대경로가 필요합니다")
        pure = PurePosixPath(value)
        if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
            raise WorkspaceError(400, "INVALID_PATH", "안전한 프로젝트 상대경로가 필요합니다")
        normalized = pure.as_posix()
        if any(part in READ_BLOCKED_PARTS for part in pure.parts):
            raise WorkspaceError(403, "PATH_FORBIDDEN", "이 경로는 참여자 작업공간에 공개되지 않습니다")
        if write and (
            normalized.startswith(WRITE_BLOCKED_PREFIXES)
            or not normalized.startswith(WRITE_PREFIXES)
        ):
            raise WorkspaceError(403, "PATH_FORBIDDEN", "이 경로는 소유자 검토 전용입니다")
        target = (self.root / Path(*pure.parts)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(403, "PATH_FORBIDDEN", "프로젝트 밖 경로는 사용할 수 없습니다") from exc
        return normalized, target

    def context(self) -> dict[str, Any]:
        return {
            "session_branch": self.session_branch,
            "write_prefixes": list(WRITE_PREFIXES),
            "blocked_prefixes": list(WRITE_BLOCKED_PREFIXES),
            "arbitrary_shell": False,
            "owner_paths_mutable": False,
        }

    def read(self, relative_path: str) -> dict[str, Any]:
        normalized, path = self._path(relative_path)
        if not path.is_file():
            raise WorkspaceError(404, "FILE_NOT_FOUND", "파일을 찾을 수 없습니다")
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES or b"\x00" in raw:
            raise WorkspaceError(415, "FILE_NOT_TEXT", "작은 텍스트 파일만 읽을 수 있습니다")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(415, "FILE_NOT_UTF8", "UTF-8 텍스트 파일만 읽을 수 있습니다") from exc
        return {"path": normalized, "content": content, "revision": digest_bytes(raw), "bytes": len(raw)}

    def search(self, query: str, *, prefix: str = "") -> dict[str, Any]:
        if not isinstance(query, str) or not _QUERY.fullmatch(query):
            raise WorkspaceError(400, "INVALID_QUERY", "검색어 형식이 올바르지 않습니다")
        start = self.root
        normalized_prefix = ""
        if prefix:
            normalized_prefix, start = self._path(prefix)
            if not start.is_dir():
                raise WorkspaceError(404, "PATH_NOT_FOUND", "검색 폴더를 찾을 수 없습니다")
        matches: list[dict[str, Any]] = []
        folded = query.casefold()
        for path in start.rglob("*"):
            if len(matches) >= MAX_SEARCH_RESULTS:
                break
            relative = path.relative_to(self.root)
            if not path.is_file() or any(part in READ_BLOCKED_PARTS for part in relative.parts):
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if len(raw) > MAX_FILE_BYTES or b"\x00" in raw:
                continue
            try:
                lines = raw.decode("utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, 1):
                if folded in line.casefold():
                    matches.append({
                        "path": relative.as_posix(), "line": line_number,
                        "preview": line[:240],
                    })
                    if len(matches) >= MAX_SEARCH_RESULTS:
                        break
        return {"query": query, "prefix": normalized_prefix, "matches": matches, "truncated": len(matches) >= MAX_SEARCH_RESULTS}

    def write(self, relative_path: str, content: str, *, expected_revision: str, operation_id: str) -> dict[str, Any]:
        normalized, path = self._path(relative_path, write=True)
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE_BYTES:
            raise WorkspaceError(413, "FILE_TOO_LARGE", "파일은 512KB 이하여야 합니다")
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise WorkspaceError(400, "SECRET_INPUT_BLOCKED", "비밀로 보이는 문자열은 저장할 수 없습니다")
        current = path.read_bytes() if path.is_file() else b""
        current_revision = digest_bytes(current)
        if expected_revision != current_revision:
            raise WorkspaceError(409, "STALE_REVISION", "파일이 바뀌었습니다. 최신판을 다시 읽으세요")
        encoded = content.encode("utf-8")
        if encoded == current:
            return {"path": normalized, "revision": current_revision, "saved": True, "changed": False, "operation_id": operation_id}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{operation_id}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
            temporary.replace(path)
        except FileExistsError as exc:
            raise WorkspaceError(409, "OPERATION_IN_PROGRESS", "같은 저장 작업이 이미 진행 중입니다") from exc
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"path": normalized, "revision": digest_bytes(encoded), "saved": True, "changed": True, "operation_id": operation_id}

    def _git(self, arguments: Iterable[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", *arguments], cwd=self.root, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=timeout, check=False,
        )
        if completed.returncode != 0:
            raise WorkspaceError(409, "GIT_OPERATION_FAILED", "Git 작업이 안전하게 완료되지 않았습니다")
        return completed

    def diff(self) -> dict[str, Any]:
        completed = self._git(("diff", "--", *WRITE_PREFIXES))
        return {"diff": completed.stdout, "session_branch": self.session_branch}

    def commit(self, message: str, paths: list[str]) -> dict[str, Any]:
        if not isinstance(message, str) or not _MESSAGE.fullmatch(message):
            raise WorkspaceError(400, "INVALID_COMMIT_MESSAGE", "한 줄 커밋 설명이 필요합니다")
        if not isinstance(paths, list) or not paths or len(paths) > 50:
            raise WorkspaceError(400, "INVALID_PATHS", "변경 파일 1~50개가 필요합니다")
        normalized = [self._path(path, write=True)[0] for path in paths]
        self._git(("add", "--", *normalized))
        staged = self._git(("diff", "--cached", "--name-only", "--", *normalized)).stdout.splitlines()
        if sorted(staged) != sorted(normalized):
            raise WorkspaceError(409, "STAGED_SCOPE_MISMATCH", "요청한 파일만 저장 기록에 포함해야 합니다")
        self._git(("commit", "-m", message, "--", *normalized))
        sha = self._git(("rev-parse", "HEAD")).stdout.strip()
        return {"commit_sha": sha, "session_branch": self.session_branch, "paths": normalized}

    def run_check(self, check_id: str, *, python_executable: str) -> dict[str, Any]:
        allowlist = {
            "collaboration-gateway": (python_executable, "-X", "utf8", "40_TESTS/test_collaboration_gateway.py"),
            "collaboration-http": (python_executable, "-X", "utf8", "40_TESTS/test_collaboration_http.py"),
        }
        command = allowlist.get(check_id)
        if command is None:
            raise WorkspaceError(403, "CHECK_NOT_ALLOWED", "허용된 검사만 실행할 수 있습니다")
        completed = subprocess.run(
            list(command), cwd=self.root, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=120, check=False,
        )
        return {
            "check_id": check_id, "status": "passed" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "summary": (completed.stdout + completed.stderr)[-4000:],
        }
