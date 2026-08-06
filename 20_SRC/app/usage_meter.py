#!/usr/bin/env python3
"""WireGuard 누적 카운터를 v2 지갑 사용량 사건으로 안전하게 연결한다."""
from __future__ import annotations

import json
import hashlib
import re
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.wallet_ledger import WalletLedger


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_-]{2,159}$")
_WRITE_LOCK = threading.RLock()


class UsageRejected(ValueError):
    """오래된 epoch, 감소 카운터, event 충돌을 거부한다."""


def _as_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("시간에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


class UsageMeter:
    """단일 제어 writer에서 카운터 증가분만 차감하고 재수신은 한 번만 반영한다.

    첫 관측은 등록 전 트래픽을 청구하지 않기 위해 기준선으로만 저장한다. 노드가
    재시작하면 호출자가 epoch를 올려야 하며, 같은 epoch의 감소는 fail-closed다.
    """

    def __init__(self, storage_path: str | Path, wallet: WalletLedger | None = None):
        self.storage_path = Path(storage_path)
        self.wallet = wallet or WalletLedger(self.storage_path)
        self.persistence_status = self.wallet.persistence_status
        self.warning = self.wallet.warning

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if not _ID.fullmatch(value):
            raise ValueError(f"{label} 형식이 올바르지 않습니다")

    def ingest(
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
        for value, label in ((event_id, "event_id"), (node_id, "node_id"), (device_id, "device_id")):
            self._validate_id(value, label)
        if not isinstance(epoch, int) or epoch < 0:
            raise ValueError("epoch는 0 이상의 정수여야 합니다")
        if min(rx_bytes, tx_bytes) < 0:
            raise ValueError("누적 카운터는 음수일 수 없습니다")
        observed = _as_utc(observed_at)
        with _WRITE_LOCK:
            return self._ingest_locked(
                event_id=event_id,
                node_id=node_id,
                device_id=device_id,
                epoch=epoch,
                rx_bytes=rx_bytes,
                tx_bytes=tx_bytes,
                observed=observed,
            )

    def _ingest_locked(
        self,
        *,
        event_id: str,
        node_id: str,
        device_id: str,
        epoch: int,
        rx_bytes: int,
        tx_bytes: int,
        observed: datetime,
    ) -> dict[str, Any]:
        try:
            with closing(self._connect()) as connection:
                stored = connection.execute(
                    "SELECT * FROM usage_events WHERE event_id=?", (event_id,)
                ).fetchone()
                if stored is not None:
                    same = (
                        stored["node_id"] == node_id
                        and stored["device_id"] == device_id
                        and int(stored["epoch"]) == epoch
                        and int(stored["rx_bytes"]) == rx_bytes
                        and int(stored["tx_bytes"]) == tx_bytes
                    )
                    if not same:
                        raise UsageRejected("같은 event_id에 다른 카운터 내용이 들어왔습니다")
                    result = json.loads(str(stored["result_json"]))
                    result["duplicate"] = True
                    return result
                same_sample = connection.execute(
                    """SELECT result_json FROM usage_events
                       WHERE node_id=? AND device_id=? AND epoch=? AND rx_bytes=? AND tx_bytes=?""",
                    (node_id, device_id, epoch, rx_bytes, tx_bytes),
                ).fetchone()
                if same_sample is not None:
                    result = json.loads(str(same_sample["result_json"]))
                    result["duplicate"] = True
                    result["duplicate_sample"] = True
                    return result
                device = connection.execute(
                    "SELECT account_id,status FROM devices WHERE device_id=?", (device_id,)
                ).fetchone()
                if device is None or device["status"] != "active":
                    raise UsageRejected("활성 기기를 찾을 수 없습니다")
                account_id = str(device["account_id"])
                previous = connection.execute(
                    "SELECT * FROM peer_counter_state WHERE node_id=? AND device_id=?",
                    (node_id, device_id),
                ).fetchone()

            total = rx_bytes + tx_bytes
            baseline = previous is None
            if baseline:
                delta = 0
            else:
                previous_epoch = int(previous["epoch"])
                previous_total = int(previous["rx_bytes"]) + int(previous["tx_bytes"])
                if epoch < previous_epoch:
                    raise UsageRejected("오래된 counter epoch는 적용하지 않습니다")
                if epoch == previous_epoch and (
                    rx_bytes < int(previous["rx_bytes"]) or tx_bytes < int(previous["tx_bytes"])
                ):
                    raise UsageRejected("같은 epoch의 누적 카운터는 감소할 수 없습니다")
                delta = total if epoch > previous_epoch else total - previous_total

            wallet_before = self.wallet.snapshot(account_id, now=observed)
            if not wallet_before.get("applied"):
                raise sqlite3.OperationalError("wallet snapshot unavailable")
            available = int(wallet_before["total_available_bytes"])
            charged = min(delta, available)
            session_id = f"wg:{node_id}:{device_id}:{epoch}"
            sample_key = hashlib.sha256(
                f"{node_id}\0{device_id}\0{epoch}\0{rx_bytes}\0{tx_bytes}".encode("utf-8")
            ).hexdigest()
            if charged:
                wallet_result = self.wallet.consume(
                    account_id,
                    charged,
                    event_id=f"wg-sample:{sample_key}",
                    session_id=f"wg-poll:{sample_key}",
                    now=observed,
                )
                if not wallet_result.get("applied"):
                    raise sqlite3.OperationalError("wallet consume unavailable")
            else:
                wallet_result = wallet_before
            result = {
                "applied": True,
                "duplicate": False,
                "event_id": event_id,
                "account_id": account_id,
                "device_id": device_id,
                "session_id": session_id,
                "epoch": epoch,
                "baseline": baseline,
                "observed_delta_bytes": delta,
                "charged_bytes": charged,
                "unbilled_bytes": delta - charged,
                "blocked": delta > charged or int(wallet_result["total_available_bytes"]) == 0,
                "balances": wallet_result["balances"],
                "observed_at": observed.isoformat(),
                "persistence_status": "persistent",
                "warning": None,
            }
            encoded = json.dumps(result, sort_keys=True)
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """INSERT INTO usage_events
                       (event_id,node_id,device_id,account_id,session_id,epoch,rx_bytes,tx_bytes,
                        observed_delta_bytes,applied_delta_bytes,result_json,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        event_id, node_id, device_id, account_id, session_id, epoch, rx_bytes,
                        tx_bytes, delta, charged, encoded, observed.isoformat(),
                    ),
                )
                connection.execute(
                    """INSERT INTO peer_counter_state VALUES (?,?,?,?,?,?)
                       ON CONFLICT(node_id,device_id) DO UPDATE SET epoch=excluded.epoch,
                         rx_bytes=excluded.rx_bytes,tx_bytes=excluded.tx_bytes,
                         updated_at=excluded.updated_at""",
                    (node_id, device_id, epoch, rx_bytes, tx_bytes, observed.isoformat()),
                )
                connection.commit()
            return result
        except UsageRejected:
            raise
        except (OSError, sqlite3.Error) as exc:
            self.persistence_status = "unavailable"
            self.warning = (
                "사용량 저장에 실패해 새 차감을 확정하지 않았습니다. 원본 카운터를 보존하고 "
                f"재시도 전까지 피어를 허용하면 안 됩니다: {type(exc).__name__}"
            )
            return {
                "applied": False,
                "duplicate": False,
                "blocked": True,
                "persistence_status": self.persistence_status,
                "warning": self.warning,
            }

    def sessions(self, account_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        self._validate_id(account_id, "account_id")
        if limit < 1 or limit > 100:
            raise ValueError("limit은 1..100 범위여야 합니다")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT session_id,MIN(created_at) started_at,MAX(created_at) updated_at,
                          SUM(observed_delta_bytes) observed_bytes,
                          SUM(applied_delta_bytes) charged_bytes,
                          SUM(observed_delta_bytes-applied_delta_bytes) unbilled_bytes
                   FROM usage_events WHERE account_id=? AND observed_delta_bytes>0
                   GROUP BY session_id ORDER BY updated_at DESC LIMIT ?""",
                (account_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
