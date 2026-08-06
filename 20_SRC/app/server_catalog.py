#!/usr/bin/env python3
"""FreeFlexVPN의 실제 가동 서버만 공개하는 fail-closed 카탈로그."""
from __future__ import annotations

import base64
import ipaddress
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PUBLIC_HEALTH = ("healthy", "busy")
ALL_HEALTH = PUBLIC_HEALTH + ("maintenance", "unavailable")
DEFAULT_HEALTH_TTL_SECONDS = 120
MAX_FUTURE_SKEW_SECONDS = 30
_SERVER_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return utc_now()
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("시간에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _valid_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def _valid_wg_key(value: str) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except (ValueError, base64.binascii.Error):
        return False


class ServerCatalog:
    """서버 계약·프로비저닝·exit 확인·최신 health를 모두 통과한 항목만 노출한다.

    공급자명, endpoint, WireGuard 공개키와 exit IP는 제어면에서만 사용하며
    공개 카탈로그에는 내보내지 않는다. 저장 실패나 오래된 health는 서버 0대로
    처리해 존재하지 않는 연결 대상을 만들지 않는다.
    """

    def __init__(self, storage_path: str | Path, *, health_ttl_seconds: int = DEFAULT_HEALTH_TTL_SECONDS):
        if health_ttl_seconds < 15 or health_ttl_seconds > 3600:
            raise ValueError("health_ttl_seconds는 15..3600이어야 합니다")
        self.storage_path = Path(storage_path)
        self.health_ttl_seconds = health_ttl_seconds
        self.persistence_status = "persistent"
        self.warning: str | None = None
        self._available = True
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path, timeout=5, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA busy_timeout=5000")
        except BaseException:
            connection.close()
            raise
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS servers (
                    server_id TEXT PRIMARY KEY,
                    country_code TEXT NOT NULL,
                    country TEXT NOT NULL,
                    city TEXT NOT NULL,
                    provider_ref TEXT NOT NULL,
                    health TEXT NOT NULL CHECK(health IN ('healthy','busy','maintenance','unavailable')),
                    capacity_percent INTEGER NOT NULL CHECK(capacity_percent BETWEEN 0 AND 100),
                    exit_ip TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    wg_public_key TEXT NOT NULL,
                    dns_addresses TEXT NOT NULL,
                    contract_active INTEGER NOT NULL CHECK(contract_active IN (0,1)),
                    provisioned INTEGER NOT NULL CHECK(provisioned IN (0,1)),
                    exit_verified INTEGER NOT NULL CHECK(exit_verified IN (0,1)),
                    verified_at TEXT,
                    measured_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS servers_public_state
                    ON servers(contract_active, provisioned, exit_verified, health, measured_at);
                """
            )

    def _mark_unavailable(self, exc: BaseException) -> None:
        self._available = False
        self.persistence_status = "unavailable"
        self.warning = (
            "서버 카탈로그 저장소를 확인할 수 없어 서버를 공개하지 않습니다. "
            f"기존 파일은 덮어쓰지 않았습니다: {type(exc).__name__}"
        )

    @staticmethod
    def _validate_text(value: str, label: str, *, max_length: int = 100) -> None:
        if not value or len(value) > max_length or any(ord(char) < 32 for char in value):
            raise ValueError(f"{label}가 비어 있거나 올바르지 않습니다")

    def register_verified_server(
        self,
        *,
        server_id: str,
        country_code: str,
        country: str,
        city: str,
        provider_ref: str,
        exit_ip: str,
        endpoint: str,
        wg_public_key: str,
        dns_addresses: list[str],
        health: str,
        capacity_percent: int,
        contract_active: bool,
        provisioned: bool,
        exit_verified: bool,
        measured_at: datetime | str | None = None,
        verified_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        """운영자가 확인한 서버 후보를 추가하거나 갱신한다.

        ``exit_verified``는 실제 WireGuard 출구에서 확인한 경우에만 참이어야 한다.
        거짓이면 저장은 가능하지만 공개 목록에는 절대 들어가지 않는다.
        """
        if not self._available:
            return {"applied": False, "warning": self.warning}
        if not _SERVER_ID.fullmatch(server_id):
            raise ValueError("server_id 형식이 올바르지 않습니다")
        if not _COUNTRY_CODE.fullmatch(country_code):
            raise ValueError("country_code는 ISO 2자리 대문자여야 합니다")
        if country_code == "KR":
            raise ValueError("현행 D4 정책상 대한민국 exit 서버는 등록할 수 없습니다")
        for value, label in ((country, "country"), (city, "city"), (provider_ref, "provider_ref")):
            self._validate_text(value, label)
        if health not in ALL_HEALTH:
            raise ValueError("알 수 없는 health 상태입니다")
        if not isinstance(capacity_percent, int) or not 0 <= capacity_percent <= 100:
            raise ValueError("capacity_percent는 0..100 정수여야 합니다")
        if not _valid_public_ip(exit_ip):
            raise ValueError("exit_ip는 실제 공인 IP여야 합니다")
        self._validate_text(endpoint, "endpoint", max_length=255)
        if not _valid_wg_key(wg_public_key):
            raise ValueError("WireGuard 공개키는 32바이트 base64여야 합니다")
        if not dns_addresses or not all(_valid_public_ip(value) for value in dns_addresses):
            raise ValueError("DNS 주소는 하나 이상의 공인 IP여야 합니다")
        measured = _as_utc(measured_at)
        verified = _as_utc(verified_at) if exit_verified else None
        now = utc_now().isoformat()
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """INSERT INTO servers
                       (server_id,country_code,country,city,provider_ref,health,capacity_percent,
                        exit_ip,endpoint,wg_public_key,dns_addresses,contract_active,provisioned,
                        exit_verified,verified_at,measured_at,updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(server_id) DO UPDATE SET
                         country_code=excluded.country_code,country=excluded.country,city=excluded.city,
                         provider_ref=excluded.provider_ref,health=excluded.health,
                         capacity_percent=excluded.capacity_percent,exit_ip=excluded.exit_ip,
                         endpoint=excluded.endpoint,wg_public_key=excluded.wg_public_key,
                         dns_addresses=excluded.dns_addresses,contract_active=excluded.contract_active,
                         provisioned=excluded.provisioned,exit_verified=excluded.exit_verified,
                         verified_at=excluded.verified_at,measured_at=excluded.measured_at,
                         updated_at=excluded.updated_at""",
                    (
                        server_id, country_code, country, city, provider_ref, health,
                        capacity_percent, exit_ip, endpoint, wg_public_key, ",".join(dns_addresses),
                        int(contract_active), int(provisioned), int(exit_verified),
                        verified.isoformat() if verified else None, measured.isoformat(), now,
                    ),
                )
                connection.commit()
            return {"applied": True, "server_id": server_id, "public": self.is_public(server_id)}
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return {"applied": False, "warning": self.warning}

    def _public_rows(self, *, now: datetime | str | None = None) -> list[sqlite3.Row]:
        if not self._available:
            return []
        current = _as_utc(now)
        cutoff = current - timedelta(seconds=self.health_ttl_seconds)
        future_cutoff = current + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS)
        try:
            with closing(self._connect()) as connection:
                return connection.execute(
                    """SELECT * FROM servers
                       WHERE contract_active=1 AND provisioned=1 AND exit_verified=1
                         AND health IN ('healthy','busy') AND measured_at>=? AND measured_at<=?
                       ORDER BY capacity_percent ASC, country ASC, city ASC, server_id ASC""",
                    (cutoff.isoformat(), future_cutoff.isoformat()),
                ).fetchall()
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return []

    def public_catalog(self, *, now: datetime | str | None = None) -> dict[str, Any]:
        rows = self._public_rows(now=now)
        return {
            "servers": [
                {
                    "server_id": str(row["server_id"]),
                    "country_code": str(row["country_code"]),
                    "country": str(row["country"]),
                    "city": str(row["city"]),
                    "health": str(row["health"]),
                    "capacity_percent": int(row["capacity_percent"]),
                    "measured_at": str(row["measured_at"]),
                }
                for row in rows
            ],
            "available_count": len(rows),
            "measured_at": max((str(row["measured_at"]) for row in rows), default=None),
            "stale_after_seconds": self.health_ttl_seconds,
            "persistence_status": self.persistence_status,
            "warning": self.warning,
        }

    def is_public(self, server_id: str, *, now: datetime | str | None = None) -> bool:
        return any(str(row["server_id"]) == server_id for row in self._public_rows(now=now))

    def server_for_exit_ip(self, exit_ip: str, *, now: datetime | str | None = None) -> dict[str, Any] | None:
        if not _valid_public_ip(exit_ip):
            return None
        for row in self._public_rows(now=now):
            if str(row["exit_ip"]) == exit_ip:
                return {key: row[key] for key in row.keys()}
        return None

    def connection_config(self, server_id: str, *, now: datetime | str | None = None) -> dict[str, Any] | None:
        for row in self._public_rows(now=now):
            if str(row["server_id"]) == server_id:
                return {
                    "server_id": server_id,
                    "endpoint": str(row["endpoint"]),
                    "server_public_key": str(row["wg_public_key"]),
                    "dns": str(row["dns_addresses"]).split(","),
                    "expected_exit_ip": str(row["exit_ip"]),
                    "health": str(row["health"]),
                    "measured_at": str(row["measured_at"]),
                }
        return None
