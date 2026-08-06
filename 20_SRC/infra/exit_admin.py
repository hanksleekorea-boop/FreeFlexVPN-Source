#!/usr/bin/env python3
"""SSH를 통해 호출되는 FreeFlexVPN exit-node 피어 관리 CLI."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

try:
    from . import quota_agent as qa
except ImportError:  # 대상 서버의 /opt/freeflexvpn 직접 실행 경로
    import quota_agent as qa  # type: ignore


SCHEMA_VERSION = 1
PRODUCT_NAME = "FreeFlexVPN"
DEFAULT_STATE_PATH = pathlib.Path("/var/lib/freeflexvpn/admin/state.json")
DEFAULT_QUOTA_PATH = pathlib.Path("/var/lib/freeflexvpn/quota/state.json")
DEFAULT_HEALTH_PATH = pathlib.Path("/var/lib/freeflexvpn/health/latest.json")
DEFAULT_SERVER_PUBLIC_KEY_PATH = pathlib.Path("/etc/wireguard/wg0.pub")
DEFAULT_BOOT_ID_PATH = pathlib.Path("/proc/sys/kernel/random/boot_id")
_DEVICE_ID = re.compile(r"^[a-f0-9]{32}$")
_NODE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")


def empty_state(node_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT_NAME,
        "node_id": node_id,
        "peers": {},
        "updated_at": None,
    }


def _validate_state(state: dict[str, Any], node_id: str) -> None:
    if (
        state.get("schema_version") != SCHEMA_VERSION
        or state.get("product") != PRODUCT_NAME
        or state.get("node_id") != node_id
        or not isinstance(state.get("peers"), dict)
    ):
        raise qa.QuotaStateError("지원하지 않는 exit admin 상태입니다")
    for device_id, peer in state["peers"].items():
        if not _DEVICE_ID.fullmatch(str(device_id)):
            raise qa.QuotaStateError("장치 ID가 올바르지 않습니다")
        if not {"account_id", "public_key", "allowed_ip", "status"}.issubset(peer):
            raise qa.QuotaStateError("exit admin 피어 필드가 부족합니다")
        qa.validate_account_id(str(peer["account_id"]))
        qa.validate_public_key(str(peer["public_key"]))
        qa.validate_allowed_ip(str(peer["allowed_ip"]) + "/32")
        if peer["status"] not in ("provisioning", "active", "revoking", "revoked"):
            raise qa.QuotaStateError("exit admin 피어 상태가 올바르지 않습니다")


def load_state(path: pathlib.Path, node_id: str) -> dict[str, Any]:
    if not path.exists():
        return empty_state(node_id)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        _validate_state(state, node_id)
        return state
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, qa.QuotaStateError) as exc:
        raise qa.QuotaStateError(
            f"exit admin 상태를 읽지 못했습니다. 원본을 덮어쓰지 않습니다: {type(exc).__name__}"
        ) from exc


def write_state_atomic(path: pathlib.Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = copy.deepcopy(state)
    candidate["updated_at"] = datetime.now(timezone.utc).isoformat()
    descriptor, name = tempfile.mkstemp(prefix=".admin.", suffix=".json", dir=path.parent)
    temp = pathlib.Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(candidate, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
        state.clear()
        state.update(candidate)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise qa.QuotaStateError(
            f"exit admin 상태 저장에 실패해 런타임 변경을 확정하지 않습니다: {type(exc).__name__}"
        ) from exc


def _next_address(state: dict[str, Any]) -> str:
    used = {str(peer["allowed_ip"]) for peer in state["peers"].values()}
    # 폐기된 주소도 A0에서는 재사용하지 않아 오래된 QR과 새 피어의 충돌을 막는다.
    for host in qa.ipaddress.ip_network("10.66.0.0/24").hosts():
        if str(host) == "10.66.0.1":
            continue
        if str(host) not in used:
            return str(host)
    raise RuntimeError("exit 노드의 A0 피어 주소가 모두 사용됐습니다")


def _verify_runtime(public_key: str, allowed_ip: str, observed: dict[str, dict[str, Any]]) -> bool:
    peer = observed.get(public_key)
    return bool(peer and peer.get("allowed_ip") == allowed_ip)


class ExitAdmin:
    def __init__(
        self,
        *,
        node_id: str,
        state_path: pathlib.Path = DEFAULT_STATE_PATH,
        quota_path: pathlib.Path = DEFAULT_QUOTA_PATH,
        health_path: pathlib.Path = DEFAULT_HEALTH_PATH,
        server_public_key_path: pathlib.Path = DEFAULT_SERVER_PUBLIC_KEY_PATH,
        boot_id_path: pathlib.Path = DEFAULT_BOOT_ID_PATH,
    ):
        if not _NODE_ID.fullmatch(node_id):
            raise ValueError("node_id 형식이 올바르지 않습니다")
        self.node_id = node_id
        self.state_path = pathlib.Path(state_path)
        self.quota_path = pathlib.Path(quota_path)
        self.health_path = pathlib.Path(health_path)
        self.server_public_key_path = pathlib.Path(server_public_key_path)
        self.boot_id_path = pathlib.Path(boot_id_path)

    def provision(self, account_id: str, device_id: str, public_key: str) -> dict[str, Any]:
        qa.validate_account_id(account_id)
        qa.validate_public_key(public_key)
        if not _DEVICE_ID.fullmatch(device_id):
            raise ValueError("device_id는 32자리 소문자 hex여야 합니다")
        with qa.state_lock(self.quota_path):
            state = load_state(self.state_path, self.node_id)
            existing = state["peers"].get(device_id)
            if existing:
                if existing["account_id"] != account_id or existing["public_key"] != public_key:
                    raise ValueError("같은 device_id에 다른 계정 또는 공개키를 사용할 수 없습니다")
                allowed_ip = str(existing["allowed_ip"])
                duplicate = existing["status"] == "active"
            else:
                active_count = sum(
                    1 for peer in state["peers"].values()
                    if peer["account_id"] == account_id and peer["status"] in ("provisioning", "active")
                )
                if active_count >= qa.MAX_ACTIVE_PEERS_PER_ACCOUNT:
                    raise ValueError("계정당 활성 기기 2대 제한을 초과했습니다")
                if any(peer["public_key"] == public_key for peer in state["peers"].values()):
                    raise ValueError("이미 등록 또는 폐기된 WireGuard 공개키입니다")
                allowed_ip = _next_address(state)
                state["peers"][device_id] = {
                    "account_id": account_id,
                    "public_key": public_key,
                    "allowed_ip": allowed_ip,
                    "status": "provisioning",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "revoked_at": None,
                }
                duplicate = False
                write_state_atomic(self.state_path, state)

            quota = qa.load_state(self.quota_path)
            before = qa.read_wg()
            qa.enroll(quota, account_id, public_key, allowed_ip, before)
            qa.write_state_atomic(self.quota_path, quota)
            qa.sync_firewall(quota)
            qa.sync_wireguard(quota, before)
            confirmed = _verify_runtime(public_key, allowed_ip, qa.read_wg())
            if not confirmed:
                raise RuntimeError("WireGuard 피어 readback이 등록 결과와 일치하지 않습니다")
            state = load_state(self.state_path, self.node_id)
            state["peers"][device_id]["status"] = "active"
            write_state_atomic(self.state_path, state)
            return {
                "applied": True,
                "duplicate": duplicate,
                "node_id": self.node_id,
                "device_id": device_id,
                "assigned_address": allowed_ip + "/32",
                "runtime_confirmed": True,
            }

    def revoke(self, device_id: str) -> dict[str, Any]:
        if not _DEVICE_ID.fullmatch(device_id):
            raise ValueError("device_id는 32자리 소문자 hex여야 합니다")
        with qa.state_lock(self.quota_path):
            state = load_state(self.state_path, self.node_id)
            peer = state["peers"].get(device_id)
            if peer is None:
                raise ValueError("등록된 device_id가 아닙니다")
            duplicate = peer["status"] == "revoked"
            peer["status"] = "revoking"
            write_state_atomic(self.state_path, state)
            quota = qa.load_state(self.quota_path)
            qa.revoke(quota, str(peer["public_key"]))
            qa.write_state_atomic(self.quota_path, quota)
            qa.sync_firewall(quota)
            qa.sync_wireguard(quota, qa.read_wg())
            confirmed = str(peer["public_key"]) not in qa.read_wg()
            if not confirmed:
                raise RuntimeError("WireGuard 피어가 readback에서 여전히 발견됩니다")
            state = load_state(self.state_path, self.node_id)
            state["peers"][device_id]["status"] = "revoked"
            state["peers"][device_id]["revoked_at"] = datetime.now(timezone.utc).isoformat()
            write_state_atomic(self.state_path, state)
            return {
                "applied": True,
                "duplicate": duplicate,
                "node_id": self.node_id,
                "device_id": device_id,
                "runtime_confirmed": True,
            }

    def counters(self) -> dict[str, Any]:
        state = load_state(self.state_path, self.node_id)
        observed = qa.read_wg()
        boot_id = self.boot_id_path.read_text(encoding="ascii").strip()
        epoch = int(hashlib.sha256(boot_id.encode("ascii")).hexdigest()[:15], 16)
        samples = []
        for device_id, peer in state["peers"].items():
            if peer["status"] != "active":
                continue
            sample = observed.get(str(peer["public_key"]))
            if sample is None:
                continue
            handshake_epoch = int(sample.get("latest_handshake_epoch", 0))
            handshake_at = (
                datetime.fromtimestamp(handshake_epoch, tz=timezone.utc).isoformat()
                if handshake_epoch > 0 else None
            )
            samples.append(
                {
                    "device_id": device_id,
                    "epoch": epoch,
                    "rx_bytes": int(sample["rx_bytes"]),
                    "tx_bytes": int(sample["tx_bytes"]),
                    "handshake_at": handshake_at,
                }
            )
        return {
            "node_id": self.node_id,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "samples": samples,
        }

    def health(self) -> dict[str, Any]:
        try:
            health = json.loads(self.health_path.read_text(encoding="utf-8"))
            public_key = self.server_public_key_path.read_text(encoding="ascii").strip()
            qa.validate_public_key(public_key)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"health readback을 확인할 수 없습니다: {type(exc).__name__}") from exc
        if health.get("status") not in ("ok", "degraded") or not health.get("checked_at"):
            raise RuntimeError("health readback 형식이 올바르지 않습니다")
        return {
            "node_id": self.node_id,
            "health": "healthy" if health["status"] == "ok" else "unavailable",
            "measured_at": str(health["checked_at"]),
            "failures": str(health.get("failures", "")),
            "server_public_key": public_key,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--quota-state", type=pathlib.Path, default=DEFAULT_QUOTA_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    provision = sub.add_parser("provision")
    provision.add_argument("--account-id", required=True)
    provision.add_argument("--device-id", required=True)
    provision.add_argument("--peer-key", required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--device-id", required=True)
    sub.add_parser("counters")
    sub.add_parser("health")
    args = parser.parse_args(argv)
    admin = ExitAdmin(node_id=args.node_id, state_path=args.state, quota_path=args.quota_state)
    try:
        if args.command == "provision":
            result = admin.provision(args.account_id, args.device_id, args.peer_key)
        elif args.command == "revoke":
            result = admin.revoke(args.device_id)
        elif args.command == "counters":
            result = admin.counters()
        else:
            result = admin.health()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (qa.QuotaStateError, RuntimeError, ValueError, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=qa.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
