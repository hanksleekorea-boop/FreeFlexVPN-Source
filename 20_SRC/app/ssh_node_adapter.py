#!/usr/bin/env python3
"""제어 API와 분리된 exit 노드를 strict SSH로 연결하는 어댑터."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import pathlib
import re
import shlex
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


_SAFE_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_SSH_USER = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_DEVICE_ID = re.compile(r"^[a-f0-9]{32}$")
_ACCOUNT_ID = re.compile(r"^[a-f0-9]{64}$")
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
DEFAULT_HEALTH_MAX_AGE_SECONDS = 120
MAX_FUTURE_SKEW_SECONDS = 30


class NodeAdapterError(RuntimeError):
    """SSH·원격 readback·응답 계약 실패."""


def _as_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("verified_at에는 timezone이 필요합니다")
    return parsed.astimezone(timezone.utc)


def _valid_wg_key(value: str) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except (ValueError, base64.binascii.Error):
        return False


@dataclass(frozen=True)
class SSHNodeSpec:
    server_id: str
    node_id: str
    host: str
    ssh_user: str
    ssh_port: int
    identity_file: pathlib.Path
    known_hosts_file: pathlib.Path
    country_code: str
    country: str
    city: str
    provider_ref: str
    exit_ip: str
    endpoint: str
    server_public_key: str
    dns_addresses: tuple[str, ...]
    exit_verified: bool
    verified_at: datetime | str | None
    capacity_percent: int = 0

    def validated(self) -> "SSHNodeSpec":
        if not _SAFE_NAME.fullmatch(self.server_id) or not _SAFE_NAME.fullmatch(self.node_id):
            raise ValueError("server_id와 node_id 형식이 올바르지 않습니다")
        if self.country_code == "KR" or not re.fullmatch(r"[A-Z]{2}", self.country_code):
            raise ValueError("D4 정책상 KR은 금지되며 ISO 2자리 국가 코드가 필요합니다")
        if not _SSH_USER.fullmatch(self.ssh_user):
            raise ValueError("SSH 사용자 형식이 올바르지 않습니다")
        if not 1 <= self.ssh_port <= 65535:
            raise ValueError("SSH 포트 범위가 올바르지 않습니다")
        if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", self.host):
            raise ValueError("SSH host 형식이 올바르지 않습니다")
        if not self.identity_file.is_absolute() or not self.known_hosts_file.is_absolute():
            raise ValueError("SSH identity와 known_hosts는 절대 경로여야 합니다")
        if not self.identity_file.is_file() or not self.known_hosts_file.is_file():
            raise ValueError("SSH identity 또는 known_hosts 파일을 찾을 수 없습니다")
        if not ipaddress.ip_address(self.exit_ip).is_global:
            raise ValueError("exit_ip는 실제 공인 IP여야 합니다")
        if self.exit_verified and self.verified_at is None:
            raise ValueError("확인된 exit에는 verified_at이 필요합니다")
        if self.verified_at is not None:
            _as_utc(self.verified_at)
        if not _valid_wg_key(self.server_public_key):
            raise ValueError("서버 WireGuard 공개키가 올바르지 않습니다")
        if not self.dns_addresses or not all(ipaddress.ip_address(value).is_global for value in self.dns_addresses):
            raise ValueError("DNS 주소는 하나 이상의 공인 IP여야 합니다")
        if not 0 <= self.capacity_percent <= 100:
            raise ValueError("capacity_percent는 0..100이어야 합니다")
        for value, label in (
            (self.country, "country"), (self.city, "city"),
            (self.provider_ref, "provider_ref"), (self.endpoint, "endpoint"),
        ):
            if not value or len(value) > 255 or any(ord(char) < 32 for char in value):
                raise ValueError(f"{label}가 비어 있거나 올바르지 않습니다")
        return self


class SSHNodeAdapter:
    def __init__(
        self,
        storage_path: str | pathlib.Path,
        nodes: list[SSHNodeSpec],
        *,
        runner: Runner | None = None,
        timeout_seconds: int = 20,
        health_max_age_seconds: int = DEFAULT_HEALTH_MAX_AGE_SECONDS,
    ):
        if not 5 <= timeout_seconds <= 60:
            raise ValueError("SSH timeout은 5..60초여야 합니다")
        if not 15 <= health_max_age_seconds <= 3600:
            raise ValueError("health 최대 나이는 15..3600초여야 합니다")
        validated = [node.validated() for node in nodes]
        if len({node.server_id for node in validated}) != len(validated):
            raise ValueError("server_id가 중복됐습니다")
        if len({node.node_id for node in validated}) != len(validated):
            raise ValueError("node_id가 중복됐습니다")
        if len({node.server_public_key for node in validated}) != len(validated):
            raise ValueError("서버 WireGuard 공개키가 중복됐습니다")
        self.storage_path = pathlib.Path(storage_path)
        self.nodes = {node.server_id: node for node in validated}
        self.timeout_seconds = timeout_seconds
        self.health_max_age_seconds = health_max_age_seconds
        self.runner = runner or self._default_runner

    def _default_runner(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )

    def _run(self, node: SSHNodeSpec, operation: str, arguments: list[str] | None = None) -> dict[str, Any]:
        if operation not in ("provision", "revoke", "counters", "health"):
            raise ValueError("허용되지 않은 exit admin 작업입니다")
        remote_parts = [
            "sudo", "--non-interactive", "/usr/bin/python3",
            "/opt/freeflexvpn/exit_admin.py", "--node-id", node.node_id,
            operation,
        ] + list(arguments or [])
        remote_command = shlex.join(remote_parts)
        command = [
            "ssh",
            "-i", str(node.identity_file),
            "-p", str(node.ssh_port),
            "-o", "BatchMode=yes",
            "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={node.known_hosts_file}",
            "-o", f"ConnectTimeout={self.timeout_seconds}",
            f"{node.ssh_user}@{node.host}",
            remote_command,
        ]
        try:
            completed = self.runner(command)
        except (OSError, subprocess.SubprocessError) as exc:
            raise NodeAdapterError(f"{node.server_id} SSH 실행에 실패했습니다: {type(exc).__name__}") from exc
        if completed.returncode != 0:
            raise NodeAdapterError(
                f"{node.server_id} {operation}이 exit code {completed.returncode}로 실패했습니다"
            )
        try:
            result = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise NodeAdapterError(f"{node.server_id} 응답이 JSON 객체가 아닙니다") from exc
        if not isinstance(result, dict) or result.get("error"):
            raise NodeAdapterError(f"{node.server_id} 응답 계약이 실패했습니다")
        return result

    def provision(self, account_id: str, device_id: str, public_key: str, server: dict[str, Any]) -> dict[str, Any]:
        if not _ACCOUNT_ID.fullmatch(account_id):
            raise NodeAdapterError("실제 피어 계정 ID는 64자리 HMAC 가명값이어야 합니다")
        if not _DEVICE_ID.fullmatch(device_id) or not _valid_wg_key(public_key):
            raise NodeAdapterError("기기 ID 또는 WireGuard 공개키가 올바르지 않습니다")
        server_id = str(server.get("server_id", ""))
        node = self.nodes.get(server_id)
        if node is None:
            raise NodeAdapterError("등록된 SSH exit 노드가 아닙니다")
        result = self._run(
            node,
            "provision",
            ["--account-id", account_id, "--device-id", device_id, "--peer-key", public_key],
        )
        if result.get("device_id") != device_id or result.get("node_id") != node.node_id:
            raise NodeAdapterError("피어 생성 readback의 식별자가 일치하지 않습니다")
        if result.get("runtime_confirmed") is not True:
            raise NodeAdapterError("피어 생성이 WireGuard readback으로 확인되지 않았습니다")
        try:
            assigned = ipaddress.ip_interface(str(result["assigned_address"]))
        except (KeyError, ValueError) as exc:
            raise NodeAdapterError("할당된 터널 주소가 올바르지 않습니다") from exc
        if assigned.version != 4 or assigned.network.prefixlen != 32 or assigned.ip not in ipaddress.ip_network("10.66.0.0/24"):
            raise NodeAdapterError("할당 주소가 FreeFlexVPN 터널 범위 밖입니다")
        return {"assigned_address": str(assigned), "runtime_confirmed": True}

    def revoke(self, account_id: str, device_id: str) -> bool:
        if not _DEVICE_ID.fullmatch(device_id):
            raise NodeAdapterError("device_id가 올바르지 않습니다")
        with closing(sqlite3.connect(self.storage_path)) as connection:
            row = connection.execute(
                "SELECT account_id,server_id FROM devices WHERE device_id=?", (device_id,)
            ).fetchone()
        if row is None or str(row[0]) != account_id:
            raise NodeAdapterError("제어 DB의 기기 소유권을 확인할 수 없습니다")
        node = self.nodes.get(str(row[1]))
        if node is None:
            raise NodeAdapterError("기기에 연결된 exit 노드를 찾을 수 없습니다")
        result = self._run(node, "revoke", ["--device-id", device_id])
        return bool(
            result.get("device_id") == device_id
            and result.get("node_id") == node.node_id
            and result.get("runtime_confirmed") is True
        )

    def poll_health(self, api: Any, *, now: datetime | None = None) -> list[dict[str, Any]]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        outcomes = []
        for node in self.nodes.values():
            try:
                result = self._run(node, "health")
                key_match = result.get("server_public_key") == node.server_public_key
                node_match = result.get("node_id") == node.node_id
                try:
                    measured = _as_utc(result["measured_at"])
                    age_seconds = (current - measured).total_seconds()
                    time_valid = -MAX_FUTURE_SKEW_SECONDS <= age_seconds <= self.health_max_age_seconds
                except (KeyError, TypeError, ValueError):
                    measured = current
                    time_valid = False
                healthy = result.get("health") == "healthy" and key_match and node_match and time_valid
                measured_at = measured.isoformat()
                applied = api.catalog.register_verified_server(
                    server_id=node.server_id,
                    country_code=node.country_code,
                    country=node.country,
                    city=node.city,
                    provider_ref=node.provider_ref,
                    exit_ip=node.exit_ip,
                    endpoint=node.endpoint,
                    wg_public_key=node.server_public_key,
                    dns_addresses=list(node.dns_addresses),
                    health="healthy" if healthy else "unavailable",
                    capacity_percent=node.capacity_percent,
                    contract_active=True,
                    provisioned=healthy,
                    exit_verified=bool(healthy and node.exit_verified),
                    measured_at=measured_at,
                    verified_at=node.verified_at if healthy and node.exit_verified else None,
                )
                outcomes.append(
                    {"server_id": node.server_id, "healthy": healthy, "catalog_applied": applied.get("applied", False)}
                )
            except (NodeAdapterError, ValueError) as exc:
                api.catalog.register_verified_server(
                    server_id=node.server_id,
                    country_code=node.country_code,
                    country=node.country,
                    city=node.city,
                    provider_ref=node.provider_ref,
                    exit_ip=node.exit_ip,
                    endpoint=node.endpoint,
                    wg_public_key=node.server_public_key,
                    dns_addresses=list(node.dns_addresses),
                    health="unavailable",
                    capacity_percent=node.capacity_percent,
                    contract_active=True,
                    provisioned=False,
                    exit_verified=False,
                    measured_at=current,
                    verified_at=None,
                )
                outcomes.append({"server_id": node.server_id, "healthy": False, "error": type(exc).__name__})
        return outcomes

    def poll_counters(self, api: Any) -> list[dict[str, Any]]:
        outcomes = []
        for node in self.nodes.values():
            result = self._run(node, "counters")
            if result.get("node_id") != node.node_id or not isinstance(result.get("samples"), list):
                raise NodeAdapterError("counter 응답 계약이 올바르지 않습니다")
            observed_at = str(result.get("observed_at"))
            for sample in result["samples"]:
                device_id = str(sample.get("device_id", ""))
                epoch = int(sample.get("epoch", -1))
                rx_bytes = int(sample.get("rx_bytes", -1))
                tx_bytes = int(sample.get("tx_bytes", -1))
                identity = f"{node.node_id}\0{device_id}\0{epoch}\0{rx_bytes}\0{tx_bytes}"
                event_id = "node:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
                usage = api.ingest_usage_counter(
                    event_id=event_id,
                    node_id=node.node_id,
                    device_id=device_id,
                    epoch=epoch,
                    rx_bytes=rx_bytes,
                    tx_bytes=tx_bytes,
                    observed_at=observed_at,
                )
                api.record_peer_observation(
                    device_id,
                    server_id=node.server_id,
                    epoch=epoch,
                    handshake_at=sample.get("handshake_at"),
                    rx_bytes=rx_bytes,
                    tx_bytes=tx_bytes,
                    observed_at=observed_at,
                )
                outcomes.append(
                    {
                        "server_id": node.server_id,
                        "device_id": device_id,
                        "usage_applied": bool(usage.get("applied")),
                        "duplicate": bool(usage.get("duplicate")),
                        "blocked": bool(usage.get("blocked")),
                    }
                )
        return outcomes
