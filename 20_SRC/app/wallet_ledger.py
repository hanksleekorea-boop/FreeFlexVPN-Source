#!/usr/bin/env python3
"""FreeFlexVPN v2의 무료·보상·충전 3지갑 append-only 원장."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from cost_model import CAP_GB_FREE


GB = 1_000_000_000
MB = 1_000_000
FREE_CAP_BYTES = int(CAP_GB_FREE * GB)
BUCKETS = ("free", "earned", "paid")
PERSISTENT_BUCKETS = ("earned", "paid")


class InsufficientWalletBalance(ValueError):
    """세 지갑의 합보다 큰 사용량을 요청했을 때 발생한다."""


class IdempotencyConflict(ValueError):
    """같은 사건 ID를 다른 계정·종류·요청 값으로 재사용했을 때 발생한다."""


def month_key(value: date | datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if isinstance(current, datetime) and current.tzinfo is not None:
        current = current.astimezone(timezone.utc)
    return f"{current.year:04d}-{current.month:02d}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WalletLedger:
    """SQLite WAL 기반 3지갑 원장.

    모든 잔액 변화는 ``wallet_entries``에 추가만 한다. 사용량 사건은 하나의
    트랜잭션에서 무료→보상→충전 순서로 차감하며 ``event_id`` 재수신 시
    저장된 기존 결과를 반환한다. 저장소가 실패하면 잔액을 추정 변경하지 않고
    ``applied=False``와 정직한 경고를 반환한다.
    """

    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
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
                CREATE TABLE IF NOT EXISTS wallet_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    bucket TEXT NOT NULL CHECK(bucket IN ('free','earned','paid')),
                    delta_bytes INTEGER NOT NULL CHECK(delta_bytes != 0),
                    reason TEXT NOT NULL,
                    idem_key TEXT NOT NULL UNIQUE,
                    free_month TEXT,
                    created_at TEXT NOT NULL,
                    CHECK((bucket = 'free' AND free_month IS NOT NULL) OR
                          (bucket != 'free' AND free_month IS NULL))
                );
                CREATE INDEX IF NOT EXISTS wallet_entries_account
                    ON wallet_entries(account_id, bucket, free_month);
                CREATE TABLE IF NOT EXISTS wallet_events (
                    event_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_receipts (
                    session_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    usage_event_id TEXT NOT NULL UNIQUE,
                    used_bytes INTEGER NOT NULL CHECK(used_bytes > 0),
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _mark_unavailable(self, exc: BaseException) -> None:
        self._available = False
        self.persistence_status = "unavailable"
        self.warning = (
            "지갑 저장소를 사용할 수 없습니다. 기존 파일은 덮어쓰지 않았고 "
            f"잔액 변경도 적용하지 않았습니다: {type(exc).__name__}"
        )

    @staticmethod
    def _validate_account(account_id: str) -> None:
        if not account_id or len(account_id) > 128:
            raise ValueError("account_id가 비어 있거나 너무 깁니다")

    @staticmethod
    def _validate_key(value: str, label: str) -> None:
        if not value or len(value) > 160:
            raise ValueError(f"{label}가 비어 있거나 너무 깁니다")

    def _ensure_month(self, connection: sqlite3.Connection, account_id: str, month: str) -> None:
        connection.execute(
            """INSERT OR IGNORE INTO wallet_entries
               (account_id,bucket,delta_bytes,reason,idem_key,free_month,created_at)
               VALUES (?, 'free', ?, 'monthly_free', ?, ?, ?)""",
            (account_id, FREE_CAP_BYTES, f"monthly-free:{account_id}:{month}", month, utc_now()),
        )

    @staticmethod
    def _balances(connection: sqlite3.Connection, account_id: str, month: str) -> dict[str, int]:
        rows = connection.execute(
            """SELECT bucket, COALESCE(SUM(delta_bytes),0) AS balance
               FROM wallet_entries
               WHERE account_id=? AND (bucket != 'free' OR free_month=?)
               GROUP BY bucket""",
            (account_id, month),
        ).fetchall()
        result = {bucket: 0 for bucket in BUCKETS}
        for row in rows:
            result[str(row["bucket"])] = int(row["balance"])
        if any(value < 0 for value in result.values()):
            raise sqlite3.IntegrityError("지갑 잔액이 음수입니다")
        return result

    def _failure(self, exc: BaseException) -> dict[str, Any]:
        self._mark_unavailable(exc)
        return {
            "applied": False,
            "duplicate": False,
            "balances": None,
            "persistence_status": self.persistence_status,
            "warning": self.warning,
        }

    def snapshot(self, account_id: str, *, now: date | datetime | None = None) -> dict[str, Any]:
        self._validate_account(account_id)
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        month = month_key(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_month(connection, account_id, month)
                balances = self._balances(connection, account_id, month)
                connection.commit()
            return {
                "applied": True,
                "duplicate": False,
                "account_id": account_id,
                "month": month,
                "balances": balances,
                "total_available_bytes": sum(balances.values()),
                "low_balance": self._low_balance(balances),
                "persistence_status": "persistent",
                "warning": None,
            }
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    @staticmethod
    def _low_balance(balances: dict[str, int]) -> str | None:
        total = sum(balances.values())
        if total <= 100 * MB:
            return "100mb"
        free_ratio = balances["free"] / FREE_CAP_BYTES
        if free_ratio <= 0.2:
            return "20pct_free"
        if free_ratio <= 0.5:
            return "50pct_free"
        return None

    @staticmethod
    def _stored_event(
        connection: sqlite3.Connection,
        event_id: str,
        *,
        account_id: str,
        event_type: str,
    ) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT account_id,event_type,result_json FROM wallet_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        if str(row["account_id"]) != account_id or str(row["event_type"]) != event_type:
            raise IdempotencyConflict("사건 ID는 다른 계정이나 사건 종류에 재사용할 수 없습니다")
        result = json.loads(str(row["result_json"]))
        result["duplicate"] = True
        return result

    def credit(
        self,
        account_id: str,
        bucket: str,
        amount_bytes: int,
        *,
        event_id: str,
        reason: str,
        now: date | datetime | None = None,
    ) -> dict[str, Any]:
        self._validate_account(account_id)
        self._validate_key(event_id, "event_id")
        if bucket not in PERSISTENT_BUCKETS:
            raise ValueError("직접 지급 가능한 지갑은 earned 또는 paid입니다")
        if amount_bytes <= 0:
            raise ValueError("지급 용량은 0보다 커야 합니다")
        if not reason or len(reason) > 80:
            raise ValueError("reason이 비어 있거나 너무 깁니다")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        month = month_key(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                stored = self._stored_event(connection, event_id, account_id=account_id, event_type="credit")
                if stored is not None:
                    if stored.get("credited_bucket") != bucket or stored.get("credited_bytes") != amount_bytes:
                        raise IdempotencyConflict("같은 지급 사건 ID의 지갑이나 용량이 다릅니다")
                    connection.commit()
                    return stored
                self._ensure_month(connection, account_id, month)
                connection.execute(
                    """INSERT INTO wallet_entries
                       (account_id,bucket,delta_bytes,reason,idem_key,free_month,created_at)
                       VALUES (?,?,?,?,?,NULL,?)""",
                    (account_id, bucket, amount_bytes, reason, f"credit:{event_id}", utc_now()),
                )
                balances = self._balances(connection, account_id, month)
                result = {
                    "applied": True,
                    "duplicate": False,
                    "event_id": event_id,
                    "credited_bucket": bucket,
                    "credited_bytes": amount_bytes,
                    "balances": balances,
                    "total_available_bytes": sum(balances.values()),
                    "low_balance": self._low_balance(balances),
                    "persistence_status": "persistent",
                    "warning": None,
                }
                connection.execute(
                    "INSERT INTO wallet_events VALUES (?,?,?,?,?)",
                    (event_id, account_id, "credit", json.dumps(result, sort_keys=True), utc_now()),
                )
                connection.commit()
                return result
        except IdempotencyConflict:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def consume(
        self,
        account_id: str,
        amount_bytes: int,
        *,
        event_id: str,
        session_id: str,
        now: date | datetime | None = None,
    ) -> dict[str, Any]:
        self._validate_account(account_id)
        self._validate_key(event_id, "event_id")
        self._validate_key(session_id, "session_id")
        if amount_bytes <= 0:
            raise ValueError("사용량은 0보다 커야 합니다")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        month = month_key(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                stored = self._stored_event(connection, event_id, account_id=account_id, event_type="usage")
                if stored is not None:
                    if stored.get("used_bytes") != amount_bytes:
                        raise IdempotencyConflict("같은 사용 사건 ID의 용량이 다릅니다")
                    connection.commit()
                    return stored
                if connection.execute(
                    "SELECT 1 FROM session_receipts WHERE session_id=?", (session_id,)
                ).fetchone():
                    raise sqlite3.IntegrityError("session_id가 다른 사용량 사건에 이미 쓰였습니다")
                self._ensure_month(connection, account_id, month)
                before = self._balances(connection, account_id, month)
                if amount_bytes > sum(before.values()):
                    connection.rollback()
                    raise InsufficientWalletBalance(
                        f"사용 가능 {sum(before.values())}바이트보다 요청량이 큽니다"
                    )
                remaining = amount_bytes
                consumed: dict[str, int] = {}
                for bucket in BUCKETS:
                    take = min(remaining, before[bucket])
                    consumed[bucket] = take
                    if take:
                        connection.execute(
                            """INSERT INTO wallet_entries
                               (account_id,bucket,delta_bytes,reason,idem_key,free_month,created_at)
                               VALUES (?,?,?,?,?,?,?)""",
                            (
                                account_id,
                                bucket,
                                -take,
                                "usage",
                                f"usage:{event_id}:{bucket}",
                                month if bucket == "free" else None,
                                utc_now(),
                            ),
                        )
                    remaining -= take
                after = self._balances(connection, account_id, month)
                result = {
                    "applied": True,
                    "duplicate": False,
                    "event_id": event_id,
                    "session_id": session_id,
                    "used_bytes": amount_bytes,
                    "consumed": consumed,
                    "before": before,
                    "balances": after,
                    "total_available_bytes": sum(after.values()),
                    "blocked": sum(after.values()) == 0,
                    "low_balance": self._low_balance(after),
                    "persistence_status": "persistent",
                    "warning": None,
                }
                encoded = json.dumps(result, sort_keys=True)
                connection.execute(
                    "INSERT INTO wallet_events VALUES (?,?,?,?,?)",
                    (event_id, account_id, "usage", encoded, utc_now()),
                )
                connection.execute(
                    "INSERT INTO session_receipts VALUES (?,?,?,?,?,?)",
                    (session_id, account_id, event_id, amount_bytes, encoded, utc_now()),
                )
                connection.commit()
                return result
        except (InsufficientWalletBalance, IdempotencyConflict):
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def receipts(self, account_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        self._validate_account(account_id)
        if limit < 1 or limit > 100:
            raise ValueError("limit은 1..100 범위여야 합니다")
        if not self._available:
            return []
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    """SELECT result_json FROM session_receipts
                       WHERE account_id=? ORDER BY rowid DESC LIMIT ?""",
                    (account_id, limit),
                ).fetchall()
            return [json.loads(str(row["result_json"])) for row in rows]
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return []
