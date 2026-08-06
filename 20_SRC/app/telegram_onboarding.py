#!/usr/bin/env python3
"""개인정보를 최소화한 Telegram 가입·동의·일회용 수령권 상태 엔진."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import hmac
import json
import os
import pathlib
import ipaddress
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode, urlparse

from infra.quota_agent import validate_allowed_ip, validate_public_key

try:
    import fcntl
except ImportError:  # Windows 로컬 테스트용
    fcntl = None

SCHEMA_VERSION = 1
PRODUCT_NAME = "FreeFlexVPN"
DEFAULT_CLAIM_TTL_SECONDS = 600


class OnboardingError(RuntimeError):
    """동의·수령권·저장 계약을 지키지 못할 때 발생한다."""


def _utc(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "product": PRODUCT_NAME, "users": {}, "claims": {}, "updated_at": None}


def _validate_claim_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("수령 주소는 자격증명·fragment가 없는 HTTPS URL이어야 합니다")
    if parsed.query:
        raise ValueError("수령 주소 기본값에는 query를 넣을 수 없습니다")
    return value.rstrip("/")


class OnboardingLedger:
    def __init__(self, storage_path: str | pathlib.Path, identity_secret: bytes):
        if len(identity_secret) < 32:
            raise ValueError("Telegram 식별자 HMAC 키는 최소 32바이트여야 합니다")
        self.storage_path = pathlib.Path(storage_path)
        self.identity_secret = bytes(identity_secret)

    def _subject(self, telegram_user_id: int) -> str:
        if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
            raise ValueError("Telegram 사용자 ID가 올바르지 않습니다")
        return hmac.new(self.identity_secret, str(telegram_user_id).encode("ascii"), hashlib.sha256).hexdigest()

    def _read(self) -> dict[str, Any]:
        if not self.storage_path.exists():
            return _empty_state()
        try:
            state = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if state.get("schema_version") != SCHEMA_VERSION or state.get("product") != PRODUCT_NAME:
                raise ValueError("지원하지 않는 상태 스키마입니다")
            if not isinstance(state.get("users"), dict) or not isinstance(state.get("claims"), dict):
                raise ValueError("사용자·수령권 원장이 객체가 아닙니다")
            for subject in state["users"]:
                if len(subject) != 64 or any(ch not in "0123456789abcdef" for ch in subject):
                    raise ValueError("가명 식별자가 올바르지 않습니다")
            for digest, claim in state["claims"].items():
                if len(digest) != 64 or not {"subject", "expires_at", "used"}.issubset(claim):
                    raise ValueError("수령권 원장이 올바르지 않습니다")
            return state
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise OnboardingError(
                f"가입 상태를 읽지 못했습니다. 원본을 보존하고 발급·폐기를 중단합니다: {type(exc).__name__}"
            ) from exc

    def _write_atomic(self, state: dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        candidate = copy.deepcopy(state)
        candidate["updated_at"] = _utc().isoformat()
        fd, tmp_name = tempfile.mkstemp(prefix=".onboarding.", suffix=".json", dir=self.storage_path.parent)
        temp = pathlib.Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(candidate, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, self.storage_path)
        except OSError as exc:
            with contextlib.suppress(OSError):
                temp.unlink()
            raise OnboardingError(
                f"가입 상태 저장에 실패했습니다. 수령권을 반환하지 않았습니다: {type(exc).__name__}"
            ) from exc

    @contextlib.contextmanager
    def _lock(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.storage_path.parent / ".onboarding.lock"
        with lock_path.open("a+b") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def _change(self, mutate: Callable[[dict[str, Any]], Any]) -> Any:
        with self._lock():
            state = self._read()
            result = mutate(state)
            self._write_atomic(state)
            return result

    def accept(self, telegram_user_id: int, policy_version: str, *, now: datetime | None = None) -> dict[str, Any]:
        if not policy_version or len(policy_version) > 64:
            raise ValueError("정책 버전이 올바르지 않습니다")
        subject = self._subject(telegram_user_id)
        accepted_at = _utc(now).isoformat()

        def mutate(state):
            user = state["users"].get(subject, {})
            peer = user.get("peer")
            state["users"][subject] = {
                "consent": True,
                "policy_version": policy_version,
                "accepted_at": accepted_at,
                "peer": peer,
            }
            return {"status": "consented", "policy_version": policy_version}

        return self._change(mutate)

    def decline(self, telegram_user_id: int) -> dict[str, Any]:
        subject = self._subject(telegram_user_id)

        def mutate(state):
            user = state["users"].get(subject)
            for digest in [d for d, claim in state["claims"].items() if claim["subject"] == subject]:
                del state["claims"][digest]
            if not user or not user.get("peer"):
                state["users"].pop(subject, None)
                return {"status": "not_stored"}
            user["consent"] = False
            user["peer"]["status"] = "revoke_pending"
            return {"status": "revoke_pending"}

        return self._change(mutate)

    def issue_claim(
        self,
        telegram_user_id: int,
        claim_base_url: str,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
    ) -> dict[str, Any]:
        subject = self._subject(telegram_user_id)
        base_url = _validate_claim_base_url(claim_base_url)
        if not 60 <= ttl_seconds <= 3600:
            raise ValueError("수령권 유효시간은 60~3600초여야 합니다")
        issued = _utc(now)
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        expires_at = (issued + timedelta(seconds=ttl_seconds)).isoformat()

        def mutate(state):
            user = state["users"].get(subject)
            if not user or not user.get("consent"):
                raise OnboardingError("동의 완료 전에는 수령권을 발급할 수 없습니다")
            if user.get("peer") and user["peer"].get("status") in {"active", "revoke_pending"}:
                raise OnboardingError("활성 또는 폐기 처리 중인 피어가 이미 있습니다")
            for old_digest in [d for d, claim in state["claims"].items() if claim["subject"] == subject and not claim["used"]]:
                del state["claims"][old_digest]
            state["claims"][digest] = {
                "subject": subject,
                "issued_at": issued.isoformat(),
                "expires_at": expires_at,
                "used": False,
            }

        self._change(mutate)
        url = base_url + "?" + urlencode({"ticket": token})
        return {"status": "claim_issued", "claim_url": url, "expires_at": expires_at, "loggable": False}

    def consume_claim(
        self,
        token: str,
        client_public_key: str,
        allowed_ip: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not token or len(token) > 256:
            raise ValueError("수령권 형식이 올바르지 않습니다")
        validate_public_key(client_public_key)
        ip = validate_allowed_ip(allowed_ip)
        address = ipaddress.ip_address(ip)
        vpn_network = ipaddress.ip_network("10.66.0.0/24")
        if address not in vpn_network or address in {vpn_network.network_address, ipaddress.ip_address("10.66.0.1"), vpn_network.broadcast_address}:
            raise ValueError("수령 주소는 10.66.0.2~10.66.0.254의 /32여야 합니다")
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        current = _utc(now)

        def mutate(state):
            claim = state["claims"].get(digest)
            if not claim or claim["used"]:
                raise OnboardingError("수령권이 없거나 이미 사용됐습니다")
            if current >= datetime.fromisoformat(claim["expires_at"]):
                raise OnboardingError("수령권이 만료됐습니다")
            user = state["users"].get(claim["subject"])
            if not user or not user.get("consent"):
                raise OnboardingError("동의 상태를 확인할 수 없습니다")
            claim["used"] = True
            claim["used_at"] = current.isoformat()
            user["peer"] = {
                "public_key": client_public_key,
                "allowed_ip": ip,
                "status": "active",
                "activated_at": current.isoformat(),
            }
            return {
                "status": "claim_consumed",
                "client_public_key": client_public_key,
                "allowed_ip": ip + "/32",
            }

        return self._change(mutate)

    def request_revoke(self, telegram_user_id: int) -> dict[str, Any]:
        subject = self._subject(telegram_user_id)

        def mutate(state):
            user = state["users"].get(subject)
            peer = user.get("peer") if user else None
            if not peer or peer.get("status") not in {"active", "revoke_pending"}:
                raise OnboardingError("폐기할 활성 피어가 없습니다")
            peer["status"] = "revoke_pending"
            return {"status": "revoke_pending", "client_public_key": peer["public_key"]}

        return self._change(mutate)

    def confirm_revoke(self, client_public_key: str, *, now: datetime | None = None) -> dict[str, Any]:
        validate_public_key(client_public_key)
        revoked_at = _utc(now).isoformat()

        def mutate(state):
            for user in state["users"].values():
                peer = user.get("peer")
                if peer and peer.get("public_key") == client_public_key and peer.get("status") == "revoke_pending":
                    peer["status"] = "revoked"
                    peer["revoked_at"] = revoked_at
                    return {"status": "revoked"}
            raise OnboardingError("폐기 대기 피어를 찾지 못했습니다")

        return self._change(mutate)

    def status(self, telegram_user_id: int) -> dict[str, Any]:
        subject = self._subject(telegram_user_id)
        with self._lock():
            state = self._read()
        user = state["users"].get(subject)
        if not user:
            return {"status": "not_registered"}
        peer = user.get("peer")
        return {
            "status": "registered" if user.get("consent") else "consent_withdrawn",
            "peer_status": peer.get("status") if peer else "not_issued",
            "policy_version": user.get("policy_version"),
        }

    def audit_snapshot(self) -> dict[str, Any]:
        with self._lock():
            return copy.deepcopy(self._read())
