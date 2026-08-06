#!/usr/bin/env python3
"""FreeFlexVPN v2 추천 귀속·자격·양쪽 보상의 로컬 원장."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from app.wallet_ledger import MB, WalletLedger, month_key, utc_now


QUALIFY_BYTES = 100 * MB
REWARD_BYTES = 500 * MB
MONTHLY_REWARD_CAP = 5
MONTHLY_TOKEN_CAP = 20
TOKEN_TTL_DAYS = 30


class ReferralRejected(ValueError):
    """자기 추천·중복·순환·만료·상한 위반을 거부한다."""


def _as_datetime(value: date | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ReferralLedger:
    """추천 토큰 원문을 저장하지 않고 보상을 하나의 DB 트랜잭션으로 지급한다."""

    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.persistence_status = "persistent"
        self.warning: str | None = None
        self._available = True
        self.wallet = WalletLedger(self.storage_path)
        if self.wallet.persistence_status != "persistent":
            self._mark_unavailable(RuntimeError("wallet storage unavailable"))
            return
        try:
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
                CREATE TABLE IF NOT EXISTS referral_tokens (
                    token_hash TEXT PRIMARY KEY,
                    inviter_id TEXT NOT NULL,
                    issued_month TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    claimed_referral_id TEXT UNIQUE
                );
                CREATE INDEX IF NOT EXISTS referral_tokens_inviter
                    ON referral_tokens(inviter_id, issued_month);
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id TEXT PRIMARY KEY,
                    inviter_id TEXT NOT NULL,
                    invitee_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK(status IN ('attributed','protected','rewarded','held')),
                    created_month TEXT NOT NULL,
                    reward_month TEXT,
                    protected_at TEXT,
                    rewarded_at TEXT,
                    held_reason TEXT,
                    created_at TEXT NOT NULL,
                    CHECK(inviter_id != invitee_id)
                );
                CREATE INDEX IF NOT EXISTS referrals_inviter
                    ON referrals(inviter_id, status, reward_month);
                CREATE TABLE IF NOT EXISTS referral_usage_events (
                    event_id TEXT PRIMARY KEY,
                    referral_id TEXT NOT NULL,
                    used_bytes INTEGER NOT NULL CHECK(used_bytes > 0),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(referral_id) REFERENCES referrals(referral_id)
                );
                """
            )

    def _mark_unavailable(self, exc: BaseException) -> None:
        self._available = False
        self.persistence_status = "unavailable"
        self.warning = (
            "추천 저장소를 사용할 수 없습니다. 원본은 덮어쓰지 않았고 "
            f"귀속·보상도 적용하지 않았습니다: {type(exc).__name__}"
        )

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if not value or len(value) > 160:
            raise ValueError(f"{label}가 비어 있거나 너무 깁니다")

    def _failure(self, exc: BaseException) -> dict[str, Any]:
        self._mark_unavailable(exc)
        return {
            "applied": False,
            "persistence_status": "unavailable",
            "warning": self.warning,
        }

    def issue_token(self, inviter_id: str, *, now: date | datetime | None = None) -> dict[str, Any]:
        self._validate_id(inviter_id, "inviter_id")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        current = _as_datetime(now)
        month = month_key(current)
        token = secrets.token_urlsafe(32)
        digest = _token_hash(token)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                count = connection.execute(
                    "SELECT COUNT(*) FROM referral_tokens WHERE inviter_id=? AND issued_month=?",
                    (inviter_id, month),
                ).fetchone()[0]
                if int(count) >= MONTHLY_TOKEN_CAP:
                    connection.rollback()
                    raise ReferralRejected("월 추천 링크 발급 상한에 도달했습니다")
                expires = current + timedelta(days=TOKEN_TTL_DAYS)
                connection.execute(
                    "INSERT INTO referral_tokens VALUES (?,?,?,?,?,NULL)",
                    (digest, inviter_id, month, current.isoformat(), expires.isoformat()),
                )
                connection.commit()
            return {
                "applied": True,
                "token": token,
                "expires_at": expires.isoformat(),
                "persistence_status": "persistent",
                "warning": None,
            }
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def list_for_account(self, account_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """계정이 초대자 또는 피초대자인 추천 진행을 최신순으로 반환한다."""
        self._validate_id(account_id, "account_id")
        if limit < 1 or limit > 100:
            raise ValueError("limit은 1..100 범위여야 합니다")
        if not self._available:
            return []
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    """SELECT referral_id FROM referrals
                       WHERE inviter_id=? OR invitee_id=?
                       ORDER BY created_at DESC LIMIT ?""",
                    (account_id, account_id, limit),
                ).fetchall()
            return [self.status(str(row["referral_id"])) for row in rows]
        except (OSError, sqlite3.Error) as exc:
            self._mark_unavailable(exc)
            return []

    def attribute(
        self,
        token: str,
        invitee_id: str,
        *,
        is_new_account: bool,
        now: date | datetime | None = None,
    ) -> dict[str, Any]:
        self._validate_id(token, "token")
        self._validate_id(invitee_id, "invitee_id")
        if not is_new_account:
            raise ReferralRejected("추천은 신규 계정에만 한 번 귀속됩니다")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        current = _as_datetime(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                token_row = connection.execute(
                    "SELECT * FROM referral_tokens WHERE token_hash=?", (_token_hash(token),)
                ).fetchone()
                if token_row is None:
                    raise ReferralRejected("유효하지 않은 추천 토큰입니다")
                if token_row["claimed_referral_id"] is not None:
                    raise ReferralRejected("이미 사용된 추천 토큰입니다")
                if _as_datetime(datetime.fromisoformat(str(token_row["expires_at"]))) < current:
                    raise ReferralRejected("만료된 추천 토큰입니다")
                inviter_id = str(token_row["inviter_id"])
                if inviter_id == invitee_id:
                    raise ReferralRejected("자기 추천은 허용되지 않습니다")
                if connection.execute(
                    "SELECT 1 FROM referrals WHERE invitee_id=?", (invitee_id,)
                ).fetchone():
                    raise ReferralRejected("이 계정에는 이미 추천이 귀속됐습니다")
                if connection.execute(
                    "SELECT 1 FROM referrals WHERE inviter_id=? AND invitee_id=?",
                    (invitee_id, inviter_id),
                ).fetchone():
                    raise ReferralRejected("서로 추천하는 순환 귀속은 허용되지 않습니다")
                referral_id = uuid.uuid4().hex
                connection.execute(
                    """INSERT INTO referrals
                       (referral_id,inviter_id,invitee_id,status,created_month,reward_month,
                        protected_at,rewarded_at,held_reason,created_at)
                       VALUES (?,?,?,'attributed',?,NULL,NULL,NULL,NULL,?)""",
                    (referral_id, inviter_id, invitee_id, month_key(current), current.isoformat()),
                )
                connection.execute(
                    "UPDATE referral_tokens SET claimed_referral_id=? WHERE token_hash=?",
                    (referral_id, _token_hash(token)),
                )
                connection.commit()
            return self.status(referral_id) | {"applied": True}
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def mark_protected(self, referral_id: str, *, now: date | datetime | None = None) -> dict[str, Any]:
        self._validate_id(referral_id, "referral_id")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        current = _as_datetime(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT status FROM referrals WHERE referral_id=?", (referral_id,)
                ).fetchone()
                if row is None:
                    raise ReferralRejected("추천 건을 찾을 수 없습니다")
                if row["status"] == "attributed":
                    connection.execute(
                        "UPDATE referrals SET status='protected', protected_at=? WHERE referral_id=?",
                        (current.isoformat(), referral_id),
                    )
                connection.commit()
            return self.status(referral_id) | {"applied": True}
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def record_usage(
        self,
        referral_id: str,
        used_bytes: int,
        *,
        event_id: str,
        now: date | datetime | None = None,
    ) -> dict[str, Any]:
        self._validate_id(referral_id, "referral_id")
        self._validate_id(event_id, "event_id")
        if used_bytes <= 0:
            raise ValueError("사용량은 0보다 커야 합니다")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        current = _as_datetime(now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                if connection.execute(
                    "SELECT 1 FROM referral_usage_events WHERE event_id=?", (event_id,)
                ).fetchone():
                    connection.commit()
                    return self.status(referral_id) | {"applied": True, "duplicate": True}
                referral = connection.execute(
                    "SELECT * FROM referrals WHERE referral_id=?", (referral_id,)
                ).fetchone()
                if referral is None:
                    raise ReferralRejected("추천 건을 찾을 수 없습니다")
                connection.execute(
                    "INSERT INTO referral_usage_events VALUES (?,?,?,?)",
                    (event_id, referral_id, used_bytes, current.isoformat()),
                )
                cumulative = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(used_bytes),0) FROM referral_usage_events WHERE referral_id=?",
                        (referral_id,),
                    ).fetchone()[0]
                )
                rewarded = False
                if referral["status"] == "protected" and cumulative >= QUALIFY_BYTES:
                    reward_month = month_key(current)
                    rewarded_count = int(
                        connection.execute(
                            """SELECT COUNT(*) FROM referrals
                               WHERE inviter_id=? AND status='rewarded' AND reward_month=?""",
                            (referral["inviter_id"], reward_month),
                        ).fetchone()[0]
                    )
                    if rewarded_count >= MONTHLY_REWARD_CAP:
                        connection.execute(
                            "UPDATE referrals SET status='held', held_reason='monthly_cap' WHERE referral_id=?",
                            (referral_id,),
                        )
                    else:
                        for side, account_id in (
                            ("inviter", str(referral["inviter_id"])),
                            ("invitee", str(referral["invitee_id"])),
                        ):
                            wallet_event = f"referral:{referral_id}:{side}"
                            connection.execute(
                                """INSERT INTO wallet_entries
                                   (account_id,bucket,delta_bytes,reason,idem_key,free_month,created_at)
                                   VALUES (?,'earned',?,'referral_reward',?,NULL,?)""",
                                (account_id, REWARD_BYTES, wallet_event, current.isoformat()),
                            )
                            event_result = json.dumps(
                                {"referral_id": referral_id, "side": side, "credited_bytes": REWARD_BYTES},
                                sort_keys=True,
                            )
                            connection.execute(
                                "INSERT INTO wallet_events VALUES (?,?,?,?,?)",
                                (wallet_event, account_id, "referral_reward", event_result, current.isoformat()),
                            )
                        connection.execute(
                            """UPDATE referrals SET status='rewarded', reward_month=?,
                               rewarded_at=?, held_reason=NULL WHERE referral_id=?""",
                            (reward_month, current.isoformat(), referral_id),
                        )
                        rewarded = True
                connection.commit()
            return self.status(referral_id) | {
                "applied": True,
                "duplicate": False,
                "cumulative_used_bytes": cumulative,
                "rewarded_now": rewarded,
            }
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def hold(self, referral_id: str, reason: str) -> dict[str, Any]:
        self._validate_id(referral_id, "referral_id")
        if not reason or len(reason) > 80:
            raise ValueError("보류 사유가 비어 있거나 너무 깁니다")
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT status FROM referrals WHERE referral_id=?", (referral_id,)
                ).fetchone()
                if row is None:
                    raise ReferralRejected("추천 건을 찾을 수 없습니다")
                if row["status"] != "rewarded":
                    connection.execute(
                        "UPDATE referrals SET status='held', held_reason=? WHERE referral_id=?",
                        (reason, referral_id),
                    )
                connection.commit()
            return self.status(referral_id) | {"applied": True}
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)

    def status(self, referral_id: str) -> dict[str, Any]:
        self._validate_id(referral_id, "referral_id")
        if not self._available:
            return self._failure(RuntimeError("storage unavailable"))
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT * FROM referrals WHERE referral_id=?", (referral_id,)
                ).fetchone()
                if row is None:
                    raise ReferralRejected("추천 건을 찾을 수 없습니다")
                cumulative = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(used_bytes),0) FROM referral_usage_events WHERE referral_id=?",
                        (referral_id,),
                    ).fetchone()[0]
                )
            return {
                "referral_id": referral_id,
                "inviter_id": str(row["inviter_id"]),
                "invitee_id": str(row["invitee_id"]),
                "status": str(row["status"]),
                "protected": row["protected_at"] is not None,
                "cumulative_used_bytes": cumulative,
                "qualify_bytes": QUALIFY_BYTES,
                "reward_bytes_each": REWARD_BYTES,
                "held_reason": row["held_reason"],
                "persistence_status": "persistent",
                "warning": None,
            }
        except ReferralRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            return self._failure(exc)
