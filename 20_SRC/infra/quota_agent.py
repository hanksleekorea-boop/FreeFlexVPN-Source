#!/usr/bin/env python3
"""WireGuard 누적 카운터를 FreeFlexVPN 월 1GB·충전 잔액에 반영한다.

대상 서버에서는 root 전용 systemd 서비스로 실행한다. 상태를 먼저 원자 저장한 뒤
nftables 차단 세트를 한 트랜잭션으로 동기화한다. 손상된 상태 파일은 덮어쓰지 않는다.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import copy
import datetime as dt
import ipaddress
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # Windows 로컬 순수함수 테스트용; 대상 Ubuntu에는 반드시 존재한다.
    fcntl = None

PRODUCT_NAME = "FreeFlexVPN"
SCHEMA_VERSION = 2
GB = 1_000_000_000
FREE_CAP_BYTES = GB
MAX_ACTIVE_PEERS_PER_ACCOUNT = 2
DEFAULT_STATE_PATH = pathlib.Path("/var/lib/freeflexvpn/quota/state.json")


class QuotaStateError(RuntimeError):
    """상태를 안전하게 읽거나 기록할 수 없을 때 발생한다."""


def month_key(now: dt.datetime | None = None) -> str:
    value = now or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    value = value.astimezone(dt.timezone.utc)
    return f"{value.year:04d}-{value.month:02d}"


def empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "product": PRODUCT_NAME, "peers": {}, "updated_at": None}


def validate_allowed_ip(value: str) -> str:
    values = [part.strip() for part in value.split(",") if part.strip()]
    if len(values) != 1:
        raise ValueError("피어 AllowedIPs는 IPv4 /32 한 개여야 합니다")
    network = ipaddress.ip_network(values[0], strict=True)
    if network.version != 4 or network.prefixlen != 32:
        raise ValueError("피어 AllowedIPs는 IPv4 /32 한 개여야 합니다")
    return str(network.network_address)


def validate_public_key(value: str) -> str:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("WireGuard 공개키가 올바른 base64가 아닙니다") from exc
    if len(raw) != 32 or raw == bytes(32):
        raise ValueError("WireGuard 공개키는 0이 아닌 32바이트여야 합니다")
    return value


def validate_account_id(value: str) -> str:
    """가입 계층이 만든 비가역 64자리 소문자 hex 가명 ID만 받는다."""
    if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
        raise ValueError("계정 ID는 HMAC-SHA256 기반 64자리 소문자 hex 가명값이어야 합니다")
    return value


def parse_wg_dump(text: str) -> dict[str, dict[str, Any]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return {}
    peers: dict[str, dict[str, Any]] = {}
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) < 8:
            raise ValueError("wg dump 피어 행의 필드가 부족합니다")
        public_key = fields[0].strip()
        if not public_key or public_key == "(none)":
            raise ValueError("wg dump 피어 공개키가 없습니다")
        allowed_ip = validate_allowed_ip(fields[3])
        latest_handshake_epoch = int(fields[4])
        rx_bytes, tx_bytes = int(fields[5]), int(fields[6])
        if latest_handshake_epoch < 0:
            raise ValueError("WireGuard 핸드셰이크 시각은 음수일 수 없습니다")
        if rx_bytes < 0 or tx_bytes < 0:
            raise ValueError("WireGuard 전송량은 음수일 수 없습니다")
        peers[public_key] = {
            "allowed_ip": allowed_ip,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "total_bytes": rx_bytes + tx_bytes,
            "latest_handshake_epoch": latest_handshake_epoch,
        }
    return peers


def _validate_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != SCHEMA_VERSION or state.get("product") != PRODUCT_NAME:
        raise QuotaStateError("지원하지 않는 쿼터 상태 스키마입니다")
    if not isinstance(state.get("peers"), dict):
        raise QuotaStateError("피어 원장이 객체가 아닙니다")
    for key, peer in state["peers"].items():
        required = {"account_id", "allowed_ip", "enrolled", "free_month", "free_used_bytes", "paid_bytes", "last_total_bytes", "blocked"}
        if not isinstance(key, str) or not required.issubset(peer):
            raise QuotaStateError("피어 원장의 필수 필드가 없습니다")
        validate_public_key(key)
        validate_allowed_ip(str(peer["allowed_ip"]) + "/32")
        if peer["enrolled"]:
            validate_account_id(str(peer["account_id"]))
        elif peer["account_id"] is not None:
            validate_account_id(str(peer["account_id"]))
        for field in ("free_used_bytes", "paid_bytes", "last_total_bytes"):
            if int(peer[field]) < 0:
                raise QuotaStateError(f"{field}는 음수일 수 없습니다")


def load_state(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        _validate_state(state)
        return state
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, QuotaStateError) as exc:
        raise QuotaStateError(
            f"쿼터 상태를 읽지 못했습니다. 원본을 보존하고 차단 상태를 변경하지 않습니다: {type(exc).__name__}"
        ) from exc


def write_state_atomic(path: pathlib.Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = copy.deepcopy(state)
    candidate["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    fd, tmp_name = tempfile.mkstemp(prefix=".state.", suffix=".json", dir=path.parent)
    tmp = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(candidate, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        if os.name != "nt":
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        state.clear()
        state.update(candidate)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise QuotaStateError(
            f"쿼터 상태 저장에 실패했습니다. 방화벽은 변경하지 않습니다: {type(exc).__name__}"
        ) from exc


@contextlib.contextmanager
def state_lock(path: pathlib.Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".lock"
    with lock_path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def reset_month(peer: dict[str, Any], now: dt.datetime | None = None) -> None:
    current = month_key(now)
    if peer["free_month"] != current:
        peer["free_month"] = current
        peer["free_used_bytes"] = 0


def available_bytes(peer: dict[str, Any], now: dt.datetime | None = None) -> int:
    reset_month(peer, now)
    free_remaining = max(0, FREE_CAP_BYTES - int(peer["free_used_bytes"]))
    return free_remaining + int(peer["paid_bytes"])


def charge_counter(peer: dict[str, Any], current_total: int, now: dt.datetime | None = None) -> dict[str, int | bool]:
    if current_total < 0:
        raise ValueError("누적 전송량은 음수일 수 없습니다")
    reset_month(peer, now)
    previous = int(peer["last_total_bytes"])
    delta = current_total - previous if current_total >= previous else current_total
    available = available_bytes(peer, now)
    charged = min(delta, available)
    free_remaining = max(0, FREE_CAP_BYTES - int(peer["free_used_bytes"]))
    from_free = min(charged, free_remaining)
    from_paid = charged - from_free
    peer["free_used_bytes"] = int(peer["free_used_bytes"]) + from_free
    peer["paid_bytes"] = int(peer["paid_bytes"]) - from_paid
    peer["last_total_bytes"] = current_total
    peer["blocked"] = delta > charged or available_bytes(peer, now) == 0
    peer["block_reason"] = "quota_exhausted" if peer["blocked"] else ""
    return {"delta_bytes": delta, "charged_bytes": charged, "blocked": bool(peer["blocked"])}


def new_peer(
    allowed_ip: str,
    *,
    enrolled: bool,
    account_id: str | None = None,
    baseline: int = 0,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    if enrolled:
        validate_account_id(str(account_id or ""))
    elif account_id is not None:
        validate_account_id(account_id)
    return {
        "account_id": account_id,
        "allowed_ip": validate_allowed_ip(allowed_ip + "/32"),
        "enrolled": enrolled,
        "free_month": month_key(now),
        "free_used_bytes": 0,
        "paid_bytes": 0,
        "last_total_bytes": baseline,
        "blocked": not enrolled,
        "block_reason": "enrollment_required" if not enrolled else "",
    }


def poll_state(state: dict[str, Any], observed: dict[str, dict[str, Any]], now: dt.datetime | None = None) -> dict[str, Any]:
    result = {"unknown_peers": 0, "charged_bytes": 0, "blocked_peers": 0}
    for public_key, sample in observed.items():
        peer = state["peers"].get(public_key)
        if peer is None:
            peer = new_peer(sample["allowed_ip"], enrolled=False, baseline=sample["total_bytes"], now=now)
            state["peers"][public_key] = peer
            result["unknown_peers"] += 1
        elif peer["allowed_ip"] != sample["allowed_ip"]:
            peer["blocked"] = True
            peer["block_reason"] = "allowed_ip_changed"
        elif peer["enrolled"]:
            charged = charge_counter(peer, sample["total_bytes"], now)
            result["charged_bytes"] += int(charged["charged_bytes"])
        if peer["blocked"]:
            result["blocked_peers"] += 1
    return result


def nft_batch(state: dict[str, Any]) -> str:
    blocked = sorted({str(peer["allowed_ip"]) for peer in state["peers"].values() if peer["blocked"]})
    lines = ["flush set inet freeflex_filter quota_blocked_v4"]
    if blocked:
        lines.append("add element inet freeflex_filter quota_blocked_v4 { " + ", ".join(blocked) + " }")
    return "\n".join(lines) + "\n"


def sync_firewall(state: dict[str, Any]) -> None:
    proc = subprocess.run(["nft", "-f", "-"], input=nft_batch(state), text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"nftables 쿼터 차단 동기화 실패: {proc.stderr.strip()}")


def read_wg() -> dict[str, dict[str, Any]]:
    proc = subprocess.run(["wg", "show", "wg0", "dump"], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"WireGuard 카운터 읽기 실패: {proc.stderr.strip()}")
    return parse_wg_dump(proc.stdout)


def enroll(
    state: dict[str, Any],
    account_id: str,
    public_key: str,
    allowed_ip: str,
    observed: dict[str, dict[str, Any]],
    now: dt.datetime | None = None,
) -> None:
    account_id = validate_account_id(account_id)
    validate_public_key(public_key)
    ip = validate_allowed_ip(allowed_ip)
    baseline = int(observed.get(public_key, {}).get("total_bytes", 0))
    existing = state["peers"].get(public_key)
    if existing and existing.get("enrolled") and existing.get("account_id") != account_id:
        raise ValueError("이미 다른 가명 계정에 등록된 피어 공개키입니다")
    for key, peer in state["peers"].items():
        if key != public_key and peer.get("enrolled") and peer.get("allowed_ip") == ip:
            raise ValueError("이미 다른 활성 피어가 사용 중인 Allowed IP입니다")
    active_for_account = sum(
        1 for key, peer in state["peers"].items()
        if key != public_key and peer.get("enrolled") and peer.get("account_id") == account_id
    )
    if active_for_account >= MAX_ACTIVE_PEERS_PER_ACCOUNT:
        raise ValueError("계정당 활성 기기 2대 제한을 초과했습니다")
    paid = int(existing.get("paid_bytes", 0)) if existing else 0
    state["peers"][public_key] = new_peer(
        ip, enrolled=True, account_id=account_id, baseline=baseline, now=now
    )
    state["peers"][public_key]["paid_bytes"] = paid


def topup(state: dict[str, Any], public_key: str, amount_bytes: int, now: dt.datetime | None = None) -> None:
    if amount_bytes <= 0:
        raise ValueError("충전 바이트는 0보다 커야 합니다")
    peer = state["peers"].get(public_key)
    if not peer or not peer["enrolled"]:
        raise ValueError("등록된 피어가 아닙니다")
    peer["paid_bytes"] = int(peer["paid_bytes"]) + amount_bytes
    if available_bytes(peer, now) > 0:
        peer["blocked"] = False
        peer["block_reason"] = ""


def revoke(state: dict[str, Any], public_key: str) -> None:
    validate_public_key(public_key)
    peer = state["peers"].get(public_key)
    if not peer:
        raise ValueError("등록된 피어가 아닙니다")
    peer["enrolled"] = False
    peer["blocked"] = True
    peer["block_reason"] = "revoked"


def sync_wireguard(state: dict[str, Any], observed: dict[str, dict[str, Any]] | None = None) -> dict[str, int]:
    current = observed if observed is not None else read_wg()
    desired = {
        key: peer for key, peer in state["peers"].items()
        if peer["enrolled"] and peer.get("block_reason") != "revoked"
    }
    removed = 0
    ensured = 0
    for public_key in sorted(set(current) - set(desired)):
        proc = subprocess.run(
            ["wg", "set", "wg0", "peer", public_key, "remove"],
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"미등록·폐기 피어 제거 실패: {proc.stderr.strip()}")
        removed += 1
    for public_key, peer in sorted(desired.items()):
        allowed = str(peer["allowed_ip"]) + "/32"
        proc = subprocess.run(
            ["wg", "set", "wg0", "peer", public_key, "allowed-ips", allowed],
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"등록 피어 적용 실패: {proc.stderr.strip()}")
        ensured += 1
    return {"removed_peers": removed, "ensured_peers": ensured}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("poll")
    enroll_p = sub.add_parser("enroll")
    enroll_p.add_argument("--account-id", required=True, help="가입 계층이 만든 64자리 HMAC 가명 ID")
    enroll_p.add_argument("--peer-key", required=True)
    enroll_p.add_argument("--allowed-ip", required=True, help="예: 10.66.0.2/32")
    topup_p = sub.add_parser("topup")
    topup_p.add_argument("--peer-key", required=True)
    topup_p.add_argument("--bytes", type=int, required=True)
    revoke_p = sub.add_parser("revoke")
    revoke_p.add_argument("--peer-key", required=True)
    sub.add_parser("status")
    args = parser.parse_args(argv)

    try:
        with state_lock(args.state):
            state = load_state(args.state)
            if args.command == "status":
                print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
                return 0
            result: dict[str, Any] = {"command": args.command}
            if args.command == "poll":
                before_sync = read_wg()
                sync_result = sync_wireguard(state, before_sync)
                observed = read_wg()
                result.update(poll_state(state, observed))
                result.update(sync_result)
                result["unknown_peers"] += sync_result["removed_peers"]
            elif args.command == "enroll":
                observed = read_wg()
                enroll(state, args.account_id, args.peer_key, args.allowed_ip, observed)
            elif args.command == "topup":
                topup(state, args.peer_key, args.bytes)
            elif args.command == "revoke":
                revoke(state, args.peer_key)
            write_state_atomic(args.state, state)
            if args.command == "revoke":
                errors = []
                try:
                    sync_firewall(state)
                except RuntimeError as exc:
                    errors.append(str(exc))
                try:
                    result.update(sync_wireguard(state))
                except RuntimeError as exc:
                    errors.append(str(exc))
                if errors:
                    raise RuntimeError("; ".join(errors))
            else:
                sync_firewall(state)
                if args.command in {"enroll", "topup"}:
                    result.update(sync_wireguard(state))
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 3 if result.get("unknown_peers") else 0
    except (QuotaStateError, RuntimeError, ValueError, OSError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
