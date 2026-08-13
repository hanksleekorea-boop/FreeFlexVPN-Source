#!/usr/bin/env python3
"""Password-gated collaboration and protected-release policy core.

The module deliberately contains no GitHub or hosting credential.  Provider
operations are injected through a server-side broker and fail closed when the
broker is absent.  Passwords, session tokens and CSRF tokens are never stored
in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol


SESSION_MINUTES = 15
PREPARE_MINUTES = 5
LOGIN_WINDOW_MINUTES = 5
LOGIN_BLOCK_MINUTES = 15
MAX_LOGIN_FAILURES = 5
_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_OPERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return utc_now()
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("시간에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ProjectContext:
    project_id: str
    project_name: str
    repository: str
    production_branch: str
    integration_branch: str
    production_environment: str
    production_url: str
    drive_state: str = "CONNECTED_PENDING_GATE"

    @property
    def fingerprint(self) -> str:
        return _digest(_canonical(asdict(self)))

    def public_card(self) -> dict[str, str]:
        return {**asdict(self), "context_fingerprint": self.fingerprint}


@dataclass(frozen=True)
class GatewayResult:
    status: int
    body: dict[str, Any]


class GatewayError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class ReleaseBroker(Protocol):
    def deploy(
        self,
        *,
        release_key: str,
        candidate_sha: str,
        artifact_digest: str,
        environment: str,
    ) -> Mapping[str, Any]: ...


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS collaboration_config (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  project_id TEXT NOT NULL,
  password_salt BLOB NOT NULL,
  password_verifier BLOB NOT NULL,
  client_pepper BLOB NOT NULL,
  policy_epoch INTEGER NOT NULL DEFAULT 1 CHECK(policy_epoch > 0),
  participant_deploy_enabled INTEGER NOT NULL DEFAULT 0 CHECK(participant_deploy_enabled IN (0,1)),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collaboration_sessions (
  session_hash TEXT PRIMARY KEY,
  csrf_hash TEXT NOT NULL,
  client_digest TEXT NOT NULL,
  policy_epoch INTEGER NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collaboration_login_attempts (
  client_digest TEXT PRIMARY KEY,
  window_started_at TEXT NOT NULL,
  failures INTEGER NOT NULL CHECK(failures >= 0),
  blocked_until TEXT
);
CREATE TABLE IF NOT EXISTS collaboration_operations (
  operation_id TEXT PRIMARY KEY,
  session_hash TEXT NOT NULL,
  action TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collaboration_deploy_preparations (
  deployment_id TEXT PRIMARY KEY,
  prepare_hash TEXT NOT NULL UNIQUE,
  session_hash TEXT NOT NULL,
  candidate_sha TEXT NOT NULL,
  artifact_digest TEXT NOT NULL,
  environment TEXT NOT NULL,
  context_fingerprint TEXT NOT NULL,
  config_revision TEXT NOT NULL,
  policy_epoch INTEGER NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT,
  status TEXT NOT NULL CHECK(status IN ('prepared','succeeded','unknown','failed')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collaboration_release_receipts (
  release_key TEXT PRIMARY KEY,
  deployment_id TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class CollaborationGateway:
    """Fail-closed collaboration authentication and release policy service."""

    def __init__(
        self,
        storage_path: str | Path,
        *,
        context: ProjectContext,
        bootstrap_password: str,
        release_broker: ReleaseBroker | None = None,
    ) -> None:
        if len(bootstrap_password) < 14:
            raise ValueError("공동개발 비밀번호는 14자 이상이어야 합니다")
        self.storage_path = Path(storage_path)
        self.context = context
        self.release_broker = release_broker
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(SCHEMA)
            row = connection.execute(
                "SELECT project_id,password_salt,password_verifier FROM collaboration_config WHERE singleton=1"
            ).fetchone()
            if row is None:
                salt = secrets.token_bytes(16)
                verifier = self._password_verifier(bootstrap_password, salt)
                connection.execute(
                    "INSERT INTO collaboration_config VALUES (1,?,?,?,?,1,0,?)",
                    (context.project_id, salt, verifier, secrets.token_bytes(32), utc_now().isoformat()),
                )
            elif str(row["project_id"]) != context.project_id:
                raise ValueError("저장소의 프로젝트 ID가 현재 대상과 다릅니다")
            elif not hmac.compare_digest(
                bytes(row["password_verifier"]),
                self._password_verifier(bootstrap_password, bytes(row["password_salt"])),
            ):
                raise ValueError("기존 게이트웨이 비밀번호와 일치하지 않습니다")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _password_verifier(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)

    def _client_digest(self, client_hint: str) -> str:
        with closing(self._connect()) as connection:
            pepper = bytes(connection.execute(
                "SELECT client_pepper FROM collaboration_config WHERE singleton=1"
            ).fetchone()[0])
        return hmac.new(pepper, client_hint.encode("utf-8"), hashlib.sha256).hexdigest()

    def _config(self) -> sqlite3.Row:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM collaboration_config WHERE singleton=1").fetchone()
        if row is None:
            raise RuntimeError("게이트웨이 설정이 없습니다")
        return row

    def login(
        self,
        password: str,
        *,
        client_hint: str,
        now: datetime | str | None = None,
    ) -> GatewayResult:
        current = _as_utc(now)
        client_digest = self._client_digest(client_hint)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            attempt = connection.execute(
                "SELECT * FROM collaboration_login_attempts WHERE client_digest=?", (client_digest,)
            ).fetchone()
            if attempt is not None and attempt["blocked_until"]:
                if _as_utc(str(attempt["blocked_until"])) > current:
                    connection.rollback()
                    raise GatewayError(429, "LOGIN_RATE_LIMITED", "잠시 후 다시 시도하세요")
            config = connection.execute(
                "SELECT * FROM collaboration_config WHERE singleton=1"
            ).fetchone()
            assert config is not None
            valid = isinstance(password, str) and hmac.compare_digest(
                bytes(config["password_verifier"]),
                self._password_verifier(password, bytes(config["password_salt"])),
            )
            if not valid:
                window_start = current
                failures = 1
                if attempt is not None and current - _as_utc(str(attempt["window_started_at"])) < timedelta(minutes=LOGIN_WINDOW_MINUTES):
                    window_start = _as_utc(str(attempt["window_started_at"]))
                    failures = int(attempt["failures"]) + 1
                blocked_until = (
                    current + timedelta(minutes=LOGIN_BLOCK_MINUTES)
                    if failures >= MAX_LOGIN_FAILURES else None
                )
                connection.execute(
                    """INSERT INTO collaboration_login_attempts VALUES (?,?,?,?)
                       ON CONFLICT(client_digest) DO UPDATE SET
                       window_started_at=excluded.window_started_at,
                       failures=excluded.failures,blocked_until=excluded.blocked_until""",
                    (client_digest, window_start.isoformat(), failures,
                     blocked_until.isoformat() if blocked_until else None),
                )
                connection.commit()
                raise GatewayError(401, "LOGIN_FAILED", "비밀번호가 올바르지 않습니다")
            connection.execute(
                "DELETE FROM collaboration_login_attempts WHERE client_digest=?", (client_digest,)
            )
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(24)
            expires = current + timedelta(minutes=SESSION_MINUTES)
            connection.execute(
                "INSERT INTO collaboration_sessions VALUES (?,?,?,?,?,?,?)",
                (_digest(token), _digest(csrf), client_digest, int(config["policy_epoch"]),
                 expires.isoformat(), None, current.isoformat()),
            )
            connection.commit()
        return GatewayResult(200, {
            "session_token": token,
            "csrf_token": csrf,
            "expires_at": expires.isoformat(),
            "role": "participant",
            "project": self.context.public_card(),
        })

    def _authorize(
        self,
        token: str,
        *,
        csrf_token: str | None = None,
        write: bool = False,
        now: datetime | str | None = None,
    ) -> sqlite3.Row:
        current = _as_utc(now)
        if not isinstance(token, str) or len(token) < 32:
            raise GatewayError(401, "AUTH_REQUIRED", "유효한 공동개발 세션이 필요합니다")
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT s.*,c.policy_epoch AS current_policy_epoch FROM collaboration_sessions s
                   JOIN collaboration_config c ON c.singleton=1 WHERE s.session_hash=?""",
                (_digest(token),),
            ).fetchone()
        if (
            row is None or row["revoked_at"] is not None
            or _as_utc(str(row["expires_at"])) <= current
            or int(row["policy_epoch"]) != int(row["current_policy_epoch"])
        ):
            raise GatewayError(401, "AUTH_REQUIRED", "세션이 만료됐거나 철회됐습니다")
        if write and (
            not isinstance(csrf_token, str)
            or not hmac.compare_digest(str(row["csrf_hash"]), _digest(csrf_token))
        ):
            raise GatewayError(403, "CSRF_REQUIRED", "쓰기 요청의 보호 토큰이 필요합니다")
        return row

    def status(self, token: str, *, now: datetime | str | None = None) -> GatewayResult:
        self._authorize(token, now=now)
        config = self._config()
        return GatewayResult(200, {
            "project": self.context.public_card(),
            "password_gateway": "configured",
            "session_max_minutes": SESSION_MINUTES,
            "participant_deploy": (
                "ready" if bool(config["participant_deploy_enabled"]) and self.release_broker
                else "policy_only"
            ),
            "release_broker": "connected" if self.release_broker else "not_connected",
            "drive_update_gate": "pending" if self.context.drive_state.startswith("CONNECTED") else "not_applicable",
            "source_credentials_exposed": False,
        })

    @staticmethod
    def _validate_operation_id(operation_id: str) -> None:
        if not isinstance(operation_id, str) or not _OPERATION.fullmatch(operation_id):
            raise GatewayError(400, "INVALID_OPERATION_ID", "operation_id 형식이 올바르지 않습니다")

    def _existing_operation(
        self, operation_id: str, *, session_hash: str, action: str, request_digest: str
    ) -> GatewayResult | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM collaboration_operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
        if row is None:
            return None
        if (
            str(row["session_hash"]) != session_hash or str(row["action"]) != action
            or str(row["request_digest"]) != request_digest
        ):
            raise GatewayError(409, "OPERATION_CONFLICT", "같은 operation_id의 내용이 다릅니다")
        payload = json.loads(str(row["response_json"]))
        return GatewayResult(int(payload["status"]), dict(payload["body"]))

    def _save_operation(
        self, operation_id: str, *, session_hash: str, action: str,
        request_digest: str, result: GatewayResult, now: datetime,
    ) -> None:
        payload = _canonical({"status": result.status, "body": result.body})
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO collaboration_operations VALUES (?,?,?,?,?,?)",
                (operation_id, session_hash, action, request_digest, payload, now.isoformat()),
            )

    def prepare_deployment(
        self,
        token: str,
        csrf_token: str,
        body: Mapping[str, Any],
        *,
        now: datetime | str | None = None,
    ) -> GatewayResult:
        current = _as_utc(now)
        session = self._authorize(token, csrf_token=csrf_token, write=True, now=current)
        operation_id = str(body.get("operation_id", ""))
        self._validate_operation_id(operation_id)
        request_digest = _digest(_canonical(dict(body)))
        existing = self._existing_operation(
            operation_id, session_hash=str(session["session_hash"]),
            action="deploy.prepare", request_digest=request_digest,
        )
        if existing:
            return existing
        candidate = str(body.get("candidate_sha", ""))
        head = str(body.get("production_head", ""))
        artifact = str(body.get("artifact_digest", ""))
        environment = str(body.get("environment", ""))
        context_fingerprint = str(body.get("context_fingerprint", ""))
        config_revision = str(body.get("config_revision", ""))
        side_effect_class = str(body.get("side_effect_class", ""))
        if not _SHA.fullmatch(candidate) or candidate != head:
            raise GatewayError(409, "UNVERIFIED_MAIN_SHA", "검증된 운영 기준 SHA만 배포할 수 있습니다")
        if not _DIGEST.fullmatch(artifact):
            raise GatewayError(400, "INVALID_ARTIFACT_DIGEST", "서명된 결과물 지문이 필요합니다")
        if body.get("ci_status") != "success" or body.get("artifact_signature_valid") is not True:
            raise GatewayError(409, "RELEASE_GATES_FAILED", "CI와 결과물 서명 검증이 필요합니다")
        if environment != self.context.production_environment:
            raise GatewayError(409, "ENVIRONMENT_MISMATCH", "승인된 기존 운영 환경이 아닙니다")
        if context_fingerprint != self.context.fingerprint:
            raise GatewayError(409, "CONTEXT_MISMATCH", "프로젝트 대상 지문이 다릅니다")
        if not config_revision or len(config_revision) > 128:
            raise GatewayError(400, "CONFIG_REVISION_REQUIRED", "운영 설정 판번호가 필요합니다")
        if side_effect_class == "PRIVILEGED":
            raise GatewayError(403, "OWNER_SPECIAL_RELEASE_ONLY", "권한·결제·데이터 변경 배포는 소유자 전용입니다")
        if side_effect_class not in {"NONE", "REVERSIBLE"}:
            raise GatewayError(400, "SIDE_EFFECT_CLASS_REQUIRED", "배포 부작용 등급이 필요합니다")
        if side_effect_class == "REVERSIBLE" and body.get("rollback_compatible") is not True:
            raise GatewayError(409, "ROLLBACK_COMPATIBILITY_REQUIRED", "되돌리기 호환성 검증이 필요합니다")
        config = self._config()
        if not bool(config["participant_deploy_enabled"]) or self.release_broker is None:
            raise GatewayError(503, "DEPLOY_BROKER_UNAVAILABLE", "보호된 운영 배포 중계가 아직 연결되지 않았습니다")
        deployment_id = "dep_" + secrets.token_hex(12)
        prepare_token = secrets.token_urlsafe(32)
        expires = current + timedelta(minutes=PREPARE_MINUTES)
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO collaboration_deploy_preparations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (deployment_id, _digest(prepare_token), str(session["session_hash"]), candidate,
                 artifact, environment, context_fingerprint, config_revision,
                 int(config["policy_epoch"]), expires.isoformat(), None, "prepared", current.isoformat()),
            )
        result = GatewayResult(201, {
            "deployment_id": deployment_id,
            "prepare_token": prepare_token,
            "expires_at": expires.isoformat(),
            "candidate_sha": candidate,
            "environment": environment,
            "context_fingerprint": context_fingerprint,
            "side_effect_class": side_effect_class,
        })
        self._save_operation(
            operation_id, session_hash=str(session["session_hash"]), action="deploy.prepare",
            request_digest=request_digest, result=result, now=current,
        )
        return result

    def perform_workspace_operation(
        self,
        token: str,
        csrf_token: str,
        *,
        operation_id: str,
        action: str,
        request: Mapping[str, Any],
        callback: Callable[[], GatewayResult],
        now: datetime | str | None = None,
    ) -> GatewayResult:
        """Run one constrained workspace mutation with a durable idempotency receipt."""
        current = _as_utc(now)
        session = self._authorize(token, csrf_token=csrf_token, write=True, now=current)
        self._validate_operation_id(operation_id)
        if action not in {"workspace.write", "workspace.commit", "workspace.check", "workspace.integration"}:
            raise GatewayError(403, "ACTION_FORBIDDEN", "허용되지 않은 작업 종류입니다")
        request_digest = _digest(_canonical(dict(request)))
        existing = self._existing_operation(
            operation_id, session_hash=str(session["session_hash"]),
            action=action, request_digest=request_digest,
        )
        if existing:
            return existing
        result = callback()
        self._save_operation(
            operation_id, session_hash=str(session["session_hash"]), action=action,
            request_digest=request_digest, result=result, now=current,
        )
        return result

    def set_participant_deploy_enabled(self, enabled: bool) -> None:
        """Owner-side configuration hook; never exposed on participant HTTP routes."""
        if enabled and self.release_broker is None:
            raise ValueError("release broker 연결 없이 참여자 배포를 켤 수 없습니다")
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE collaboration_config SET participant_deploy_enabled=? WHERE singleton=1",
                (int(enabled),),
            )

    def execute_deployment(
        self,
        token: str,
        csrf_token: str,
        deployment_id: str,
        body: Mapping[str, Any],
        *,
        now: datetime | str | None = None,
    ) -> GatewayResult:
        current = _as_utc(now)
        session = self._authorize(token, csrf_token=csrf_token, write=True, now=current)
        operation_id = str(body.get("operation_id", ""))
        self._validate_operation_id(operation_id)
        request_digest = _digest(_canonical({"deployment_id": deployment_id, **dict(body)}))
        existing = self._existing_operation(
            operation_id, session_hash=str(session["session_hash"]),
            action="deploy.execute", request_digest=request_digest,
        )
        if existing:
            return existing
        prepare_token = body.get("prepare_token")
        if not isinstance(prepare_token, str) or len(prepare_token) < 32:
            raise GatewayError(401, "PREPARE_TOKEN_REQUIRED", "유효한 배포 준비 토큰이 필요합니다")
        with closing(self._connect()) as connection:
            prepared = connection.execute(
                "SELECT * FROM collaboration_deploy_preparations WHERE deployment_id=? AND prepare_hash=?",
                (deployment_id, _digest(prepare_token)),
            ).fetchone()
        if prepared is None or str(prepared["session_hash"]) != str(session["session_hash"]):
            raise GatewayError(401, "PREPARE_TOKEN_REQUIRED", "유효한 배포 준비 토큰이 필요합니다")
        if prepared["used_at"] is not None or _as_utc(str(prepared["expires_at"])) <= current:
            raise GatewayError(409, "PREPARATION_STALE", "배포 준비가 만료됐거나 이미 사용됐습니다")
        config = self._config()
        if (
            not bool(config["participant_deploy_enabled"]) or self.release_broker is None
            or int(prepared["policy_epoch"]) != int(config["policy_epoch"])
        ):
            raise GatewayError(409, "DEPLOY_POLICY_CHANGED", "배포 정책이 바뀌었거나 중계가 중지됐습니다")
        comparisons = {
            "current_production_head": "candidate_sha",
            "current_artifact_digest": "artifact_digest",
            "current_config_revision": "config_revision",
            "context_fingerprint": "context_fingerprint",
            "environment": "environment",
        }
        for request_field, stored_field in comparisons.items():
            if str(body.get(request_field, "")) != str(prepared[stored_field]):
                raise GatewayError(409, "PREPARATION_STALE", "준비 뒤 운영 대상 또는 결과물이 바뀌었습니다")
        release_key = _digest(_canonical({
            "project": self.context.project_id,
            "environment": str(prepared["environment"]),
            "sha": str(prepared["candidate_sha"]),
            "artifact": str(prepared["artifact_digest"]),
            "config": str(prepared["config_revision"]),
        }))
        with closing(self._connect()) as connection:
            receipt = connection.execute(
                "SELECT response_json FROM collaboration_release_receipts WHERE release_key=?",
                (release_key,),
            ).fetchone()
        if receipt is not None:
            payload = json.loads(str(receipt["response_json"]))
            result = GatewayResult(200, {**payload, "deduplicated": True})
        else:
            provider = dict(self.release_broker.deploy(
                release_key=release_key,
                candidate_sha=str(prepared["candidate_sha"]),
                artifact_digest=str(prepared["artifact_digest"]),
                environment=str(prepared["environment"]),
            ))
            if provider.get("status") == "unknown":
                with closing(self._connect()) as connection:
                    connection.execute(
                        "UPDATE collaboration_deploy_preparations SET used_at=?,status='unknown' WHERE deployment_id=?",
                        (current.isoformat(), deployment_id),
                    )
                raise GatewayError(503, "DEPLOYMENT_UNKNOWN", "공급자 결과가 불명확해 새 배포를 동결했습니다")
            required = (
                provider.get("status") == "succeeded"
                and isinstance(provider.get("provider_deployment_id"), str)
                and isinstance(provider.get("release_revision"), str)
                and provider.get("served_identity_verified") is True
                and provider.get("critical_probes_passed") is True
            )
            if not required:
                with closing(self._connect()) as connection:
                    connection.execute(
                        "UPDATE collaboration_deploy_preparations SET used_at=?,status='failed' WHERE deployment_id=?",
                        (current.isoformat(), deployment_id),
                    )
                raise GatewayError(502, "POST_DEPLOY_VERIFICATION_FAILED", "운영판 식별 또는 핵심 검사가 실패했습니다")
            payload = {
                "status": "succeeded",
                "deployment_id": deployment_id,
                "provider_deployment_id": provider["provider_deployment_id"],
                "release_revision": provider["release_revision"],
                "served_identity_verified": True,
                "critical_probes_passed": True,
                "release_key": release_key,
                "deduplicated": False,
            }
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO collaboration_release_receipts VALUES (?,?,?,?)",
                    (release_key, deployment_id, _canonical(payload), current.isoformat()),
                )
                connection.execute(
                    "UPDATE collaboration_deploy_preparations SET used_at=?,status='succeeded' WHERE deployment_id=?",
                    (current.isoformat(), deployment_id),
                )
                connection.commit()
            result = GatewayResult(200, payload)
        self._save_operation(
            operation_id, session_hash=str(session["session_hash"]), action="deploy.execute",
            request_digest=request_digest, result=result, now=current,
        )
        return result

    def revoke_all(self, *, context_fingerprint: str, confirmation: str, now: datetime | str | None = None) -> dict[str, Any]:
        if context_fingerprint != self.context.fingerprint:
            raise GatewayError(409, "CONTEXT_MISMATCH", "프로젝트 대상 지문이 다릅니다")
        expected = f"REVOKE ALL {self.context.project_id}"
        if confirmation != expected:
            raise GatewayError(400, "CONFIRMATION_MISMATCH", f"확인 문구는 {expected} 입니다")
        current = _as_utc(now)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE collaboration_sessions SET revoked_at=? WHERE revoked_at IS NULL",
                (current.isoformat(),),
            ).rowcount
            connection.execute(
                """UPDATE collaboration_config SET policy_epoch=policy_epoch+1,
                   participant_deploy_enabled=0 WHERE singleton=1"""
            )
            epoch = int(connection.execute(
                "SELECT policy_epoch FROM collaboration_config WHERE singleton=1"
            ).fetchone()[0])
            connection.commit()
        return {"revoked_sessions": changed, "policy_epoch": epoch, "owner_access_preserved": True}


def as_error(exc: GatewayError) -> GatewayResult:
    return GatewayResult(exc.status, {"error": exc.code, "message": exc.message})
