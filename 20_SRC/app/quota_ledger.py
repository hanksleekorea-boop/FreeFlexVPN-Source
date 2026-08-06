#!/usr/bin/env python3
"""월 무료량과 만료 없는 충전 잔액을 원자적으로 관리한다."""
from __future__ import annotations

import copy
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from cost_model import CAP_GB_FREE, PRODUCT_NAME, TOPUP_EXPIRES


GB = 1_000_000_000
SCHEMA_VERSION = 1


class InsufficientBalance(ValueError):
    """무료량과 충전 잔액을 합쳐도 요청량보다 적을 때 발생한다."""


def _month_key(value: date | datetime | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    return f"{value.year:04d}-{value.month:02d}"


class QuotaLedger:
    """사용자 한 명의 무료·충전 잔액을 관리한다.

    저장 실패는 예외로 앱 전체를 멈추지 않는다. 변경 상태는 현재 프로세스의
    메모리에 유지하고 ``persistence_status``와 ``warning``으로 정직하게 알린다.
    """

    def __init__(self, storage_path: str | Path, *, now: date | datetime | None = None):
        self.storage_path = Path(storage_path)
        self.warning: str | None = None
        self.persistence_status = "persistent"
        self._write_disabled = False
        self._state = self._empty_state(_month_key(now))
        self._load_preserving_source()
        self._reset_month_if_needed(now)

    @staticmethod
    def _empty_state(month: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "product": PRODUCT_NAME,
            "free_month": month,
            "free_used_bytes": 0,
            "paid_bytes": 0,
            "topup_expires": TOPUP_EXPIRES,
            "updated_at": None,
        }

    def _load_preserving_source(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            loaded = json.loads(self.storage_path.read_text(encoding="utf-8"))
            required = {"free_month", "free_used_bytes", "paid_bytes", "topup_expires"}
            if not required.issubset(loaded):
                raise ValueError("필수 잔액 필드가 없습니다")
            if int(loaded["free_used_bytes"]) < 0 or int(loaded["paid_bytes"]) < 0:
                raise ValueError("잔액은 음수일 수 없습니다")
            self._state.update(loaded)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self.persistence_status = "memory_only"
            self._write_disabled = True
            self.warning = (
                "저장 파일을 읽지 못했습니다. 원본은 덮어쓰지 않았으며 복구 전까지 "
                f"변경은 메모리에만 유지됩니다: {type(exc).__name__}"
            )

    def _reset_month_if_needed(self, now: date | datetime | None) -> None:
        month = _month_key(now)
        if self._state["free_month"] == month:
            return
        candidate = copy.deepcopy(self._state)
        candidate["free_month"] = month
        candidate["free_used_bytes"] = 0
        self._commit(candidate)

    @property
    def free_cap_bytes(self) -> int:
        return int(CAP_GB_FREE * GB)

    def snapshot(self, *, now: date | datetime | None = None) -> dict[str, Any]:
        self._reset_month_if_needed(now)
        free_remaining = max(0, self.free_cap_bytes - int(self._state["free_used_bytes"]))
        return {
            **copy.deepcopy(self._state),
            "free_cap_bytes": self.free_cap_bytes,
            "free_remaining_bytes": free_remaining,
            "total_available_bytes": free_remaining + int(self._state["paid_bytes"]),
            "persistence_status": self.persistence_status,
            "warning": self.warning,
        }

    def top_up_gb(self, amount_gb: float) -> dict[str, Any]:
        amount_bytes = int(amount_gb * GB)
        if amount_bytes <= 0:
            raise ValueError("충전 용량은 0보다 커야 합니다")
        candidate = copy.deepcopy(self._state)
        candidate["paid_bytes"] = int(candidate["paid_bytes"]) + amount_bytes
        candidate["topup_expires"] = False
        self._commit(candidate)
        return self.snapshot()

    def consume(self, amount_bytes: int, *, now: date | datetime | None = None) -> dict[str, Any]:
        if amount_bytes <= 0:
            raise ValueError("사용량은 0보다 커야 합니다")
        self._reset_month_if_needed(now)
        before = self.snapshot(now=now)
        if amount_bytes > before["total_available_bytes"]:
            raise InsufficientBalance(
                f"사용 가능 {before['total_available_bytes']}바이트보다 요청량이 큽니다"
            )

        candidate = copy.deepcopy(self._state)
        from_free = min(amount_bytes, before["free_remaining_bytes"])
        from_paid = amount_bytes - from_free
        candidate["free_used_bytes"] = int(candidate["free_used_bytes"]) + from_free
        candidate["paid_bytes"] = int(candidate["paid_bytes"]) - from_paid
        self._commit(candidate)
        result = self.snapshot(now=now)
        result["consumed_free_bytes"] = from_free
        result["consumed_paid_bytes"] = from_paid
        return result

    def _commit(self, candidate: dict[str, Any]) -> None:
        candidate["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self._write_disabled:
            self._state = candidate
            return
        try:
            self._write_atomic(candidate)
            self.persistence_status = "persistent"
            self.warning = None
        except OSError as exc:
            self.persistence_status = "memory_only"
            self.warning = (
                "저장에 실패했습니다. 현재 입력은 메모리에 유지되지만 앱을 종료하면 "
                f"유지되지 않을 수 있습니다: {type(exc).__name__}"
            )
        self._state = candidate

    def _write_atomic(self, state: dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.storage_path.with_name(self.storage_path.name + ".tmp")
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.storage_path)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
