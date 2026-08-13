#!/usr/bin/env python3
"""Server-side collaboration worktrees, GitHub PR broker, and signed Drive outbox."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from app.collaboration_workspace import SafeWorkspace, WorkspaceError


_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TITLE = re.compile(r"^[^\r\n\x00]{3,120}$")
_BRANCH = re.compile(r"^ai-session/[a-f0-9]{20}$")
_OPERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _run(command: Sequence[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=cwd, text=True, encoding="utf-8", errors="replace",
        capture_output=True, timeout=timeout, check=False,
    )


@dataclass(frozen=True)
class SessionWorktreeManager:
    """Creates one durable, non-shared Git worktree for each authenticated session."""

    source_repo: Path
    sessions_root: Path
    repository: str
    base_ref: str = "origin/shared-development"

    def __post_init__(self) -> None:
        source = self.source_repo.resolve()
        sessions = self.sessions_root.resolve()
        if not (source / ".git").exists():
            raise ValueError("원본은 Git 작업공간이어야 합니다")
        if not _REPOSITORY.fullmatch(self.repository):
            raise ValueError("GitHub 저장소 형식이 올바르지 않습니다")
        remote = _run(("git", "remote", "get-url", "origin"), cwd=source)
        expected = f"github.com/{self.repository}".casefold()
        normalized = remote.stdout.strip().removesuffix(".git").replace(":", "/").casefold()
        if remote.returncode or expected not in normalized:
            raise ValueError("원본 origin이 고정 GitHub 저장소와 일치하지 않습니다")
        verified = _run(("git", "rev-parse", "--verify", f"{self.base_ref}^{{commit}}"), cwd=source)
        if verified.returncode:
            raise ValueError("통합 기준 갈래를 로컬에서 확인할 수 없습니다")
        sessions.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "source_repo", source)
        object.__setattr__(self, "sessions_root", sessions)

    @staticmethod
    def identity(session_token: str) -> str:
        if not isinstance(session_token, str) or len(session_token) < 32:
            raise WorkspaceError(401, "AUTH_REQUIRED", "유효한 공동개발 세션이 필요합니다")
        return hashlib.sha256(session_token.encode("utf-8")).hexdigest()[:20]

    def workspace_for(self, session_token: str) -> SafeWorkspace:
        identity = self.identity(session_token)
        branch = f"ai-session/{identity}"
        target = self.sessions_root / identity
        if target.exists():
            current = _run(("git", "branch", "--show-current"), cwd=target)
            if current.returncode or current.stdout.strip() != branch:
                raise WorkspaceError(409, "WORKTREE_IDENTITY_MISMATCH", "세션 작업공간 정체성이 일치하지 않습니다")
            return SafeWorkspace(target, branch)
        branch_exists = _run(("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"), cwd=self.source_repo)
        command = ["git", "worktree", "add"]
        if branch_exists.returncode == 0:
            command.extend((str(target), branch))
        else:
            command.extend(("-b", branch, str(target), self.base_ref))
        created = _run(command, cwd=self.source_repo)
        if created.returncode:
            raise WorkspaceError(503, "WORKTREE_CREATE_FAILED", "격리 작업공간을 만들지 못했습니다")
        for key, value in (("user.name", "FreeFlexVPN Session"), ("user.email", "freeflexvpn-session")):
            configured = _run(("git", "config", key, value), cwd=target)
            if configured.returncode:
                raise WorkspaceError(503, "WORKTREE_CONFIG_FAILED", "격리 작업공간 설정을 완료하지 못했습니다")
        return SafeWorkspace(target, branch)


class SignedDriveOutbox:
    """Writes tamper-evident update requests and verifies relay readback receipts."""

    def __init__(self, root: str | Path, signing_key: bytes):
        if len(signing_key) < 32:
            raise ValueError("Drive 영수증 서명키는 32바이트 이상이어야 합니다")
        self.root = Path(root).resolve()
        self.pending = self.root / "pending"
        self.receipts = self.root / "receipts"
        self.pending.mkdir(parents=True, exist_ok=True)
        self.receipts.mkdir(parents=True, exist_ok=True)
        self._key = bytes(signing_key)

    def _signature(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(self._key, _canonical(payload), hashlib.sha256).hexdigest()

    def enqueue(self, operation_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not _OPERATION.fullmatch(operation_id):
            raise WorkspaceError(400, "INVALID_OPERATION_ID", "안전한 작업 식별자가 필요합니다")
        body = {"operation_id": operation_id, "payload": dict(payload)}
        envelope = {**body, "signature": self._signature(body)}
        destination = self.pending / f"{operation_id}.json"
        encoded = _canonical(envelope)
        if destination.exists():
            existing = destination.read_bytes()
            if not hmac.compare_digest(existing, encoded):
                raise WorkspaceError(409, "OUTBOX_OPERATION_CONFLICT", "같은 작업 식별자의 내용이 다릅니다")
            return {"operation_id": operation_id, "queued": True, "deduplicated": True}
        temporary = destination.with_suffix(".tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"operation_id": operation_id, "queued": True, "deduplicated": False}

    def verify_receipt(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        signature = str(receipt.get("signature", ""))
        body = {key: value for key, value in receipt.items() if key != "signature"}
        if not hmac.compare_digest(signature, self._signature(body)):
            raise WorkspaceError(400, "INVALID_DRIVE_RECEIPT", "Drive 읽기 확인 영수증 서명이 올바르지 않습니다")
        operation_id = str(body.get("operation_id", ""))
        if not _OPERATION.fullmatch(operation_id) or body.get("readback_verified") is not True:
            raise WorkspaceError(400, "INVALID_DRIVE_RECEIPT", "Drive 읽기 확인 증거가 불완전합니다")
        if not (self.pending / f"{operation_id}.json").is_file():
            raise WorkspaceError(404, "OUTBOX_OPERATION_NOT_FOUND", "대응하는 Drive 발신 작업이 없습니다")
        destination = self.receipts / f"{operation_id}.json"
        encoded = _canonical(dict(receipt))
        existed = destination.exists()
        if destination.exists() and not hmac.compare_digest(destination.read_bytes(), encoded):
            raise WorkspaceError(409, "DRIVE_RECEIPT_CONFLICT", "기존 Drive 영수증과 내용이 다릅니다")
        if not existed:
            temporary = destination.with_suffix(".tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
        return {"operation_id": operation_id, "drive_update_gate": "verified", "deduplicated": existed}


CommandRunner = Callable[[Sequence[str], Path, int], subprocess.CompletedProcess[str]]


class GitHubIntegrationBroker:
    """Pushes only the current session branch and opens a PR to one fixed integration branch."""

    def __init__(
        self, *, repository: str, integration_branch: str, gh_executable: str = "gh",
        outbox: SignedDriveOutbox | None = None, runner: CommandRunner | None = None,
    ):
        if not _REPOSITORY.fullmatch(repository) or integration_branch != "shared-development":
            raise ValueError("고정 저장소와 통합 갈래가 필요합니다")
        self.repository = repository
        self.integration_branch = integration_branch
        self.gh_executable = gh_executable
        self.outbox = outbox
        self.runner = runner or (lambda command, cwd, timeout: _run(command, cwd=cwd, timeout=timeout))

    def request(self, workspace: SafeWorkspace, *, operation_id: str, title: str, body: str = "") -> dict[str, Any]:
        if not _OPERATION.fullmatch(operation_id) or not _TITLE.fullmatch(title):
            raise WorkspaceError(400, "INVALID_INTEGRATION_REQUEST", "통합 요청 식별자와 제목을 확인하세요")
        if not isinstance(body, str) or len(body) > 2000 or "\x00" in body:
            raise WorkspaceError(400, "INVALID_INTEGRATION_REQUEST", "통합 요청 설명이 올바르지 않습니다")
        if not _BRANCH.fullmatch(workspace.session_branch):
            raise WorkspaceError(403, "SESSION_BRANCH_FORBIDDEN", "격리 세션 갈래만 통합 요청할 수 있습니다")
        status = self.runner(("git", "status", "--porcelain"), workspace.root, 30)
        if status.returncode or status.stdout.strip():
            raise WorkspaceError(409, "WORKTREE_NOT_CLEAN", "모든 변경을 저장 기록한 뒤 통합 요청하세요")
        head = self.runner(("git", "rev-parse", "HEAD"), workspace.root, 30)
        if head.returncode or not re.fullmatch(r"[a-f0-9]{40}", head.stdout.strip()):
            raise WorkspaceError(409, "INVALID_COMMIT", "통합할 저장 기록을 확인할 수 없습니다")
        pushed = self.runner(
            ("git", "push", "origin", f"HEAD:refs/heads/{workspace.session_branch}"), workspace.root, 120,
        )
        if pushed.returncode:
            raise WorkspaceError(502, "GITHUB_PUSH_FAILED", "세션 갈래를 GitHub에 올리지 못했습니다")
        created = self.runner((
            self.gh_executable, "pr", "create", "--repo", self.repository,
            "--base", self.integration_branch, "--head", workspace.session_branch,
            "--title", title, "--body", body,
        ), workspace.root, 120)
        output = (created.stdout + "\n" + created.stderr).strip()
        match = re.search(rf"https://github\.com/{re.escape(self.repository)}/pull/(\d+)", output)
        if created.returncode or match is None:
            raise WorkspaceError(502, "GITHUB_PR_FAILED", "GitHub Pull Request를 만들지 못했습니다")
        result: dict[str, Any] = {
            "status": "submitted", "repository": self.repository,
            "base_branch": self.integration_branch, "head_branch": workspace.session_branch,
            "commit_sha": head.stdout.strip(), "pull_request_number": int(match.group(1)),
            "pull_request_url": match.group(0), "force_push": False,
        }
        if self.outbox is not None:
            result["drive_outbox"] = self.outbox.enqueue(operation_id, {
                "event": "integration_requested", "repository": self.repository,
                "base_branch": self.integration_branch, "head_branch": workspace.session_branch,
                "commit_sha": result["commit_sha"], "pull_request_url": result["pull_request_url"],
            })
        return result
