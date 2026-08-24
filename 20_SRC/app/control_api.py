#!/usr/bin/env python3
"""FreeFlexVPN v2 제어 API의 프레임워크 독립 계약 구현."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import secrets
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from app.connection_check import evaluate_connection
from app.referral_ledger import ReferralLedger, ReferralRejected
from app.server_catalog import ServerCatalog
from app.usage_meter import UsageMeter
from app.wallet_ledger import WalletLedger


CLAIM_TTL_MINUTES = 10
SESSION_TTL_MINUTES = 30
MAX_ACTIVE_DEVICES = 2
SAFETY_MAX_AGE_HOURS = 24
_ACCOUNT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")


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


def _valid_wg_key(value: str) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except (ValueError, base64.binascii.Error):
        return False


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str] = field(
        default_factory=lambda: {
            "Cache-Control": "no-store",
            "Content-Type": "application/json; charset=utf-8",
            "X-Content-Type-Options": "nosniff",
        }
    )


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


PeerProvisioner = Callable[[str, str, str, dict[str, Any]], dict[str, Any]]
PeerRevoker = Callable[[str, str], bool]


class ControlAPI:
    """HTTP 프레임워크에서 호출할 수 있는 순수 request dispatcher.

    claim과 session 원문은 반환 시점에만 존재하고 DB에는 SHA-256 해시만 저장한다.
    실제 피어 생성·폐기는 주입된 어댑터가 없으면 503/202로 정직하게 멈춘다.
    """

    def __init__(
        self,
        storage_path: str | Path,
        *,
        share_base_url: str = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
        peer_provisioner: PeerProvisioner | None = None,
        peer_revoker: PeerRevoker | None = None,
    ):
        self.storage_path = Path(storage_path)
        self.share_base_url = share_base_url.rstrip("?")
        self.peer_provisioner = peer_provisioner
        self.peer_revoker = peer_revoker
        self.persistence_status = "persistent"
        self.warning: str | None = None
        self._available = True
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
        self.catalog = ServerCatalog(self.storage_path)
        self.wallet = WalletLedger(self.storage_path)
        self.referrals = ReferralLedger(self.storage_path)
        self.usage_meter = UsageMeter(self.storage_path, self.wallet)
        if any(
            service.persistence_status != "persistent"
            for service in (self.catalog, self.wallet, self.referrals)
        ):
            self._mark_unavailable(RuntimeError("dependent storage unavailable"))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path, timeout=5, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA foreign_keys=ON")
        except BaseException:
            connection.close()
            raise
        return connection

    def _initialize(self) -> None:
        migration = Path(__file__).with_name("db_migrations") / "001_v2_alpha.sql"
        script = migration.read_text(encoding="utf-8")
        with closing(self._connect()) as connection:
            connection.executescript(script)

    def _mark_unavailable(self, exc: BaseException) -> None:
        self._available = False
        self.persistence_status = "unavailable"
        self.warning = (
            "제어 저장소를 사용할 수 없습니다. 변경을 적용하지 않았습니다: "
            f"{type(exc).__name__}"
        )

    @staticmethod
    def _validate_account_id(account_id: str) -> None:
        if not _ACCOUNT_ID.fullmatch(account_id):
            raise ValueError("account_id 형식이 올바르지 않습니다")

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str | None:
        wanted = name.casefold()
        return next((value for key, value in headers.items() if key.casefold() == wanted), None)

    @staticmethod
    def _require_body(body: Mapping[str, Any] | None) -> Mapping[str, Any]:
        if body is None:
            raise ApiError(400, "BODY_REQUIRED", "JSON 요청 본문이 필요합니다")
        return body

    def provision_claim(
        self,
        account_id: str,
        *,
        now: datetime | str | None = None,
        ttl_minutes: int = CLAIM_TTL_MINUTES,
    ) -> dict[str, Any]:
        """Telegram/운영 어댑터가 한 번만 전달할 claim을 만든다."""
        self._validate_account_id(account_id)
        if not self._available:
            return {"applied": False, "warning": self.warning}
        if ttl_minutes < 1 or ttl_minutes > 60:
            raise ValueError("claim TTL은 1..60분이어야 합니다")
        current = _as_utc(now)
        expires = current + timedelta(minutes=ttl_minutes)
        claim = secrets.token_urlsafe(32)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                existed = connection.execute(
                    "SELECT 1 FROM accounts WHERE account_id=?", (account_id,)
                ).fetchone() is not None
                connection.execute(
                    """INSERT INTO accounts(account_id,status,created_at,updated_at)
                       VALUES (?,'active',?,?)
                       ON CONFLICT(account_id) DO UPDATE SET updated_at=excluded.updated_at""",
                    (account_id, current.isoformat(), current.isoformat()),
                )
                connection.execute(
                    "INSERT INTO api_claims VALUES (?,?,?,?,?,?)",
                    (
                        _digest(claim), account_id, int(not existed), expires.isoformat(),
                        None, current.isoformat(),
                    ),
                )
                connection.commit()
            return {"applied": True, "claim": claim, "expires_at": expires.isoformat()}
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return {"applied": False, "warning": self.warning}

    def _exchange_claim(self, body: Mapping[str, Any], now: datetime) -> ApiResponse:
        claim = body.get("claim")
        if not isinstance(claim, str) or len(claim) < 32:
            raise ApiError(401, "INVALID_CLAIM", "claim이 유효하지 않거나 만료됐습니다")
        session = secrets.token_urlsafe(32)
        expires = now + timedelta(minutes=SESSION_TTL_MINUTES)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT c.account_id,c.is_new_account,c.expires_at,c.consumed_at,a.status
                   FROM api_claims c JOIN accounts a ON a.account_id=c.account_id
                   WHERE c.claim_hash=?""",
                (_digest(claim),),
            ).fetchone()
            if (
                row is None
                or row["consumed_at"] is not None
                or _as_utc(str(row["expires_at"])) < now
                or row["status"] != "active"
            ):
                connection.rollback()
                raise ApiError(401, "INVALID_CLAIM", "claim이 유효하지 않거나 만료됐습니다")
            account_id = str(row["account_id"])
            connection.execute(
                "UPDATE api_claims SET consumed_at=? WHERE claim_hash=?",
                (now.isoformat(), _digest(claim)),
            )
            connection.execute(
                "INSERT INTO api_sessions VALUES (?,?,?,?,?)",
                (_digest(session), account_id, expires.isoformat(), None, now.isoformat()),
            )
            connection.commit()
        referral_result: dict[str, Any] | None = None
        referral_token = body.get("referral_token")
        if referral_token is not None:
            if not isinstance(referral_token, str):
                referral_result = {"applied": False, "reason": "추천 토큰 형식이 올바르지 않습니다"}
            else:
                try:
                    referral_result = self.referrals.attribute(
                        referral_token,
                        account_id,
                        is_new_account=bool(row["is_new_account"]),
                        now=now,
                    )
                except ReferralRejected as exc:
                    referral_result = {"applied": False, "reason": str(exc)}
        wallet = self.wallet.snapshot(account_id, now=now)
        return ApiResponse(
            200,
            {
                "access_token": session,
                "token_type": "Bearer",
                "expires_at": expires.isoformat(),
                "account": {"account_id": account_id, "status": "active"},
                "wallet": wallet,
                "referral": referral_result,
            },
        )

    def _authenticate(self, headers: Mapping[str, str], now: datetime, *, optional: bool = False) -> str | None:
        authorization = self._header(headers, "Authorization")
        if authorization is None and optional:
            return None
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiError(401, "AUTH_REQUIRED", "유효한 세션 인증이 필요합니다")
        token = authorization[7:].strip()
        if len(token) < 32:
            raise ApiError(401, "AUTH_REQUIRED", "유효한 세션 인증이 필요합니다")
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT s.account_id,s.expires_at,s.revoked_at,a.status
                   FROM api_sessions s JOIN accounts a ON a.account_id=s.account_id
                   WHERE s.session_hash=?""",
                (_digest(token),),
            ).fetchone()
        if (
            row is None
            or row["revoked_at"] is not None
            or _as_utc(str(row["expires_at"])) < now
            or row["status"] != "active"
        ):
            raise ApiError(401, "AUTH_REQUIRED", "유효한 세션 인증이 필요합니다")
        return str(row["account_id"])

    def _register_device(self, account_id: str, body: Mapping[str, Any], now: datetime) -> ApiResponse:
        if "private_key" in body or "wg_private_key" in body:
            raise ApiError(400, "PRIVATE_KEY_FORBIDDEN", "개인키는 기기 밖으로 전송하면 안 됩니다")
        public_key = body.get("wg_public_key")
        if not isinstance(public_key, str) or not _valid_wg_key(public_key):
            raise ApiError(400, "INVALID_PUBLIC_KEY", "WireGuard 공개키 형식이 올바르지 않습니다")
        catalog = self.catalog.public_catalog(now=now)
        requested = body.get("server_id")
        server_id = str(requested) if isinstance(requested, str) else (
            str(catalog["servers"][0]["server_id"]) if catalog["servers"] else ""
        )
        server = self.catalog.connection_config(server_id, now=now)
        if server is None:
            raise ApiError(503, "SERVER_UNAVAILABLE", "현재 확인된 실제 VPN 서버가 없습니다")
        if self.peer_provisioner is None:
            raise ApiError(503, "PEER_ADAPTER_UNAVAILABLE", "실제 서버 피어 생성 연결이 준비되지 않았습니다")
        with closing(self._connect()) as connection:
            active = int(
                connection.execute(
                    "SELECT COUNT(*) FROM devices WHERE account_id=? AND status='active'", (account_id,)
                ).fetchone()[0]
            )
            if active >= MAX_ACTIVE_DEVICES:
                raise ApiError(409, "DEVICE_LIMIT", "활성 기기는 최대 2대입니다")
            if connection.execute("SELECT 1 FROM devices WHERE wg_public_key=?", (public_key,)).fetchone():
                raise ApiError(409, "DUPLICATE_PUBLIC_KEY", "이미 등록된 공개키입니다")
        device_id = uuid.uuid4().hex
        try:
            provisioned = self.peer_provisioner(account_id, device_id, public_key, server)
        except (OSError, RuntimeError) as exc:
            raise ApiError(503, "PEER_ADAPTER_FAILED", "실제 서버 피어 생성을 확인하지 못했습니다") from exc
        address = provisioned.get("assigned_address") if isinstance(provisioned, Mapping) else None
        try:
            interface = ipaddress.ip_interface(str(address))
        except ValueError as exc:
            raise ApiError(503, "INVALID_PEER_RESULT", "피어 생성 결과의 주소가 올바르지 않습니다") from exc
        if not interface.ip.is_private:
            raise ApiError(503, "INVALID_PEER_RESULT", "피어 생성 결과는 사설 터널 주소여야 합니다")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO devices VALUES (?,?,?,?,?,'active',?,NULL)",
                (device_id, account_id, public_key, server_id, str(interface), now.isoformat()),
            )
            connection.commit()
        return ApiResponse(
            201,
            {
                "device_id": device_id,
                "status": "active",
                "issued_at": now.isoformat(),
                "delivery_expires_at": (now + timedelta(minutes=10)).isoformat(),
                "configuration": {
                    "addresses": [str(interface)],
                    "dns": server["dns"],
                    "peer": {
                        "public_key": server["server_public_key"],
                        "endpoint": server["endpoint"],
                        "allowed_ips": ["0.0.0.0/0", "::/0"],
                        "persistent_keepalive": 25,
                    },
                },
                "private_key_received": False,
            },
        )

    def _revoke_device(self, account_id: str, device_id: str, now: datetime) -> ApiResponse:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT status FROM devices WHERE device_id=? AND account_id=?",
                (device_id, account_id),
            ).fetchone()
        if row is None:
            raise ApiError(404, "DEVICE_NOT_FOUND", "기기를 찾을 수 없습니다")
        if row["status"] == "revoked":
            return ApiResponse(200, {"device_id": device_id, "status": "revoked", "duplicate": True})
        try:
            revoked = bool(self.peer_revoker and self.peer_revoker(account_id, device_id))
        except (OSError, RuntimeError):
            revoked = False
        status = "revoked" if revoked else "revocation_pending"
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE devices SET status=?, revoked_at=? WHERE device_id=?",
                (status, now.isoformat() if revoked else None, device_id),
            )
            connection.commit()
        return ApiResponse(
            200 if revoked else 202,
            {
                "device_id": device_id,
                "status": status,
                "enforcement": "confirmed" if revoked else "pending",
            },
        )

    def _devices(self, account_id: str) -> ApiResponse:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT device_id,server_id,assigned_address,status,created_at,revoked_at
                   FROM devices WHERE account_id=?
                   ORDER BY created_at DESC,device_id DESC""",
                (account_id,),
            ).fetchall()
        devices = [
            {
                "device_id": str(row["device_id"]),
                "server_id": str(row["server_id"]),
                "assigned_address": str(row["assigned_address"]),
                "status": str(row["status"]),
                "created_at": str(row["created_at"]),
                "revoked_at": str(row["revoked_at"]) if row["revoked_at"] is not None else None,
            }
            for row in rows
        ]
        return ApiResponse(
            200,
            {
                "devices": devices,
                "active_count": sum(item["status"] == "active" for item in devices),
                "active_limit": MAX_ACTIVE_DEVICES,
            },
        )

    def record_peer_observation(
        self,
        device_id: str,
        *,
        server_id: str,
        epoch: int = 0,
        handshake_at: datetime | str | None,
        rx_bytes: int,
        tx_bytes: int,
        observed_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        """서버 계측 어댑터 전용. 브라우저 입력으로 노출하지 않는다."""
        if not isinstance(epoch, int) or epoch < 0:
            raise ValueError("counter epoch는 0 이상의 정수여야 합니다")
        if rx_bytes < 0 or tx_bytes < 0:
            raise ValueError("누적 카운터는 음수일 수 없습니다")
        observed = _as_utc(observed_at)
        handshake = _as_utc(handshake_at).isoformat() if handshake_at is not None else None
        with closing(self._connect()) as connection:
            device = connection.execute(
                "SELECT server_id,status FROM devices WHERE device_id=?", (device_id,)
            ).fetchone()
            if device is None or device["status"] != "active" or device["server_id"] != server_id:
                raise ValueError("활성 기기와 서버가 일치하지 않습니다")
            previous = connection.execute(
                "SELECT counter_epoch,rx_bytes,tx_bytes FROM peer_runtime WHERE device_id=?", (device_id,)
            ).fetchone()
            if previous and epoch < int(previous["counter_epoch"]):
                raise ValueError("오래된 counter epoch는 적용할 수 없습니다")
            if previous and epoch == int(previous["counter_epoch"]) and (
                rx_bytes < previous["rx_bytes"] or tx_bytes < previous["tx_bytes"]
            ):
                raise ValueError("동일 epoch 누적 카운터는 감소할 수 없습니다")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO peer_runtime VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(device_id) DO UPDATE SET server_id=excluded.server_id,
                     counter_epoch=excluded.counter_epoch,handshake_at=excluded.handshake_at,
                     rx_bytes=excluded.rx_bytes,
                     tx_bytes=excluded.tx_bytes,observed_at=excluded.observed_at""",
                (device_id, server_id, epoch, handshake, rx_bytes, tx_bytes, observed.isoformat()),
            )
            connection.commit()
        return {"applied": True, "device_id": device_id, "observed_at": observed.isoformat()}

    def record_safety_observation(
        self,
        device_id: str,
        *,
        os_family: str,
        dns_protected: bool,
        ipv6_protected: bool,
        kill_switch_protected: bool,
        observed_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        """OS 하네스 전용 안전 결과. 사용자의 자기신고를 보호 증거로 받지 않는다."""
        if os_family not in ("ios", "android", "windows"):
            raise ValueError("지원하는 OS는 ios, android, windows입니다")
        observed = _as_utc(observed_at)
        with closing(self._connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM devices WHERE device_id=? AND status='active'", (device_id,)
            ).fetchone() is None:
                raise ValueError("활성 기기를 찾을 수 없습니다")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO safety_observations VALUES (?,?,?,?,?,?)
                   ON CONFLICT(device_id) DO UPDATE SET os_family=excluded.os_family,
                     dns_protected=excluded.dns_protected,ipv6_protected=excluded.ipv6_protected,
                     kill_switch_protected=excluded.kill_switch_protected,
                     observed_at=excluded.observed_at""",
                (
                    device_id, os_family, int(dns_protected), int(ipv6_protected),
                    int(kill_switch_protected), observed.isoformat(),
                ),
            )
            connection.commit()
        return {"applied": True, "device_id": device_id, "observed_at": observed.isoformat()}

    def _check(self, headers: Mapping[str, str], remote_ip: str | None, now: datetime) -> ApiResponse:
        account_id = self._authenticate(headers, now, optional=True)
        exit_server = self.catalog.server_for_exit_ip(remote_ip or "", now=now)
        if account_id is None:
            return ApiResponse(
                200,
                {
                    "protected": False,
                    "state": "limited" if exit_server else "disconnected",
                    "on_freeflex_exit": exit_server is not None,
                    "exit": (
                        {"server_id": str(exit_server["server_id"]), "checked_at": now.isoformat()}
                        if exit_server else None
                    ),
                    "reason": "세션·기기·안전 근거 없이 보호됨으로 판정하지 않습니다",
                },
            )
        device_id = self._header(headers, "X-FreeFlex-Device")
        if not device_id:
            result = evaluate_connection(
                profile_present=False,
                tunnel_started=exit_server is not None,
                observed_exit_ip=remote_ip,
                expected_exit_ip=None,
                server_health=None,
                handshake_at=None,
                dns_protected=None,
                ipv6_protected=None,
                kill_switch_protected=None,
                checked_at=now,
            )
            return ApiResponse(200, result | {"on_freeflex_exit": exit_server is not None})
        with closing(self._connect()) as connection:
            device = connection.execute(
                """SELECT * FROM devices WHERE device_id=? AND account_id=? AND status='active'""",
                (device_id, account_id),
            ).fetchone()
            peer = connection.execute(
                "SELECT * FROM peer_runtime WHERE device_id=?", (device_id,)
            ).fetchone()
            safety = connection.execute(
                "SELECT * FROM safety_observations WHERE device_id=?", (device_id,)
            ).fetchone()
        if device is None:
            raise ApiError(404, "DEVICE_NOT_FOUND", "활성 기기를 찾을 수 없습니다")
        server = self.catalog.connection_config(str(device["server_id"]), now=now)
        safety_fresh = bool(
            safety
            and _as_utc(str(safety["observed_at"])) >= now - timedelta(hours=SAFETY_MAX_AGE_HOURS)
        )
        result = evaluate_connection(
            profile_present=True,
            tunnel_started=exit_server is not None,
            observed_exit_ip=remote_ip,
            expected_exit_ip=server["expected_exit_ip"] if server else None,
            server_health=server["health"] if server else None,
            handshake_at=str(peer["handshake_at"]) if peer and peer["handshake_at"] else None,
            dns_protected=bool(safety["dns_protected"]) if safety_fresh else None,
            ipv6_protected=bool(safety["ipv6_protected"]) if safety_fresh else None,
            kill_switch_protected=bool(safety["kill_switch_protected"]) if safety_fresh else None,
            checked_at=now,
        )
        referral_updates: list[str] = []
        if result["protected"]:
            for referral in self.referrals.list_for_account(account_id):
                if referral["invitee_id"] == account_id and referral["status"] == "attributed":
                    updated = self.referrals.mark_protected(str(referral["referral_id"]), now=now)
                    if updated.get("applied"):
                        referral_updates.append(str(referral["referral_id"]))
        return ApiResponse(
            200,
            result
            | {
                "on_freeflex_exit": exit_server is not None,
                "device_id": device_id,
                "referral_protection_updates": referral_updates,
            },
        )

    def _usage(self, account_id: str) -> ApiResponse:
        sessions = self.usage_meter.sessions(account_id, limit=20)
        return ApiResponse(
            200,
            {
                "sessions": sessions,
                "monthly_total_bytes": sum(int(item.get("charged_bytes", 0)) for item in sessions),
                "lag_notice": "서버 계측 반영은 최대 2분 지연될 수 있습니다",
                "persistence_status": self.wallet.persistence_status,
                "warning": self.wallet.warning,
            },
        )

    def ingest_usage_counter(
        self,
        *,
        event_id: str,
        node_id: str,
        device_id: str,
        epoch: int,
        rx_bytes: int,
        tx_bytes: int,
        observed_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        """인증된 exit-node 어댑터 전용 사용량 진입점."""
        result = self.usage_meter.ingest(
            event_id=event_id,
            node_id=node_id,
            device_id=device_id,
            epoch=epoch,
            rx_bytes=rx_bytes,
            tx_bytes=tx_bytes,
            observed_at=observed_at,
        )
        referral_updates: list[dict[str, Any]] = []
        if result.get("applied") and int(result.get("charged_bytes", 0)) > 0:
            account_id = str(result["account_id"])
            for referral in self.referrals.list_for_account(account_id):
                if referral["invitee_id"] == account_id and referral["status"] == "protected":
                    updated = self.referrals.record_usage(
                        str(referral["referral_id"]),
                        int(result["charged_bytes"]),
                        event_id=f"meter:{event_id}",
                        now=_as_utc(observed_at),
                    )
                    referral_updates.append(
                        {
                            "referral_id": str(referral["referral_id"]),
                            "status": updated.get("status"),
                            "rewarded_now": bool(updated.get("rewarded_now")),
                        }
                    )
        return result | {"referral_updates": referral_updates}

    def _request_deletion(self, account_id: str, now: datetime) -> ApiResponse:
        request_id = uuid.uuid4().hex
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT request_id,status,requested_at FROM deletion_requests WHERE account_id=?",
                (account_id,),
            ).fetchone()
            if existing:
                connection.commit()
                return ApiResponse(200, dict(existing) | {"duplicate": True})
            connection.execute(
                "INSERT INTO deletion_requests VALUES (?,?,'requested',?,NULL)",
                (request_id, account_id, now.isoformat()),
            )
            connection.execute(
                "UPDATE accounts SET status='deletion_requested',updated_at=? WHERE account_id=?",
                (now.isoformat(), account_id),
            )
            connection.execute(
                "UPDATE api_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL",
                (now.isoformat(), account_id),
            )
            connection.execute(
                "UPDATE devices SET status='revocation_pending' WHERE account_id=? AND status='active'",
                (account_id,),
            )
            connection.commit()
        return ApiResponse(
            202,
            {
                "request_id": request_id,
                "status": "requested",
                "requested_at": now.isoformat(),
                "session_revoked": True,
            },
        )

    def handle(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        remote_ip: str | None = None,
        now: datetime | str | None = None,
    ) -> ApiResponse:
        """요청을 처리한다. 원문 토큰·개인키·stack trace는 오류에 포함하지 않는다."""
        request_headers = headers or {}
        current = _as_utc(now)
        clean_path = urlsplit(path).path.rstrip("/") or "/"
        verb = method.upper()
        if not self._available:
            return ApiResponse(503, {"error": "STORAGE_UNAVAILABLE", "message": self.warning})
        try:
            if verb == "GET" and clean_path == "/v1/catalog":
                return ApiResponse(200, self.catalog.public_catalog(now=current))
            if verb == "POST" and clean_path == "/v1/claims/exchange":
                return self._exchange_claim(self._require_body(body), current)
            if verb == "GET" and clean_path == "/v1/check":
                return self._check(request_headers, remote_ip, current)

            account_id = self._authenticate(request_headers, current)
            assert account_id is not None
            if verb == "GET" and clean_path == "/v1/devices":
                return self._devices(account_id)
            if verb == "POST" and clean_path == "/v1/devices":
                return self._register_device(account_id, self._require_body(body), current)
            if verb == "DELETE" and clean_path.startswith("/v1/devices/"):
                return self._revoke_device(account_id, clean_path.removeprefix("/v1/devices/"), current)
            if verb == "GET" and clean_path == "/v1/wallet":
                return ApiResponse(200, self.wallet.snapshot(account_id, now=current))
            if verb == "GET" and clean_path == "/v1/usage":
                return self._usage(account_id)
            if verb == "POST" and clean_path == "/v1/referrals":
                issued = self.referrals.issue_token(account_id, now=current)
                if not issued.get("applied"):
                    raise ApiError(503, "REFERRAL_STORAGE_UNAVAILABLE", str(issued.get("warning")))
                token = str(issued.pop("token"))
                return ApiResponse(201, issued | {"share_url": f"{self.share_base_url}?ref={token}"})
            if verb == "GET" and clean_path == "/v1/referrals":
                return ApiResponse(200, {"referrals": self.referrals.list_for_account(account_id)})
            if verb == "POST" and clean_path == "/v1/account/delete":
                return self._request_deletion(account_id, current)
            raise ApiError(404, "NOT_FOUND", "요청한 API 경로를 찾을 수 없습니다")
        except ApiError as exc:
            return ApiResponse(exc.status, {"error": exc.code, "message": exc.message})
        except ReferralRejected as exc:
            return ApiResponse(409, {"error": "REFERRAL_REJECTED", "message": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return ApiResponse(400, {"error": "INVALID_REQUEST", "message": str(exc)})
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return ApiResponse(503, {"error": "STORAGE_UNAVAILABLE", "message": self.warning})
