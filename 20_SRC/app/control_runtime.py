#!/usr/bin/env python3
"""외부 JSON 설정으로 제어 API와 SSH exit 노드 폴러를 조립한다."""
from __future__ import annotations

import json
import pathlib
import threading
from dataclasses import dataclass
from typing import Any

from app.control_api import ControlAPI
from app.ssh_node_adapter import NodeAdapterError, SSHNodeAdapter, SSHNodeSpec


class RuntimeConfigError(ValueError):
    pass


_FORBIDDEN_KEYS = {"private_key", "password", "secret", "token", "passphrase"}
_NODE_FIELDS = {
    "server_id", "node_id", "host", "ssh_user", "ssh_port", "identity_file",
    "known_hosts_file", "country_code", "country", "city", "provider_ref",
    "exit_ip", "endpoint", "server_public_key", "dns_addresses", "exit_verified",
    "verified_at", "capacity_percent",
}


def _reject_embedded_secrets(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise RuntimeConfigError(f"{path}에는 비밀값 필드 {key!r}를 넣을 수 없습니다")
            _reject_embedded_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_embedded_secrets(child, f"{path}[{index}]")


@dataclass(frozen=True)
class RuntimeSettings:
    nodes: tuple[SSHNodeSpec, ...]
    health_interval_seconds: int = 60
    counter_interval_seconds: int = 60


def load_runtime_settings(path: str | pathlib.Path) -> RuntimeSettings:
    config_path = pathlib.Path(path)
    if not config_path.is_absolute() or not config_path.is_file():
        raise RuntimeConfigError("node config는 프로젝트 밖의 기존 절대 경로 파일이어야 합니다")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeConfigError("node config JSON을 읽을 수 없습니다") from exc
    if not isinstance(raw, dict):
        raise RuntimeConfigError("node config 최상위는 객체여야 합니다")
    _reject_embedded_secrets(raw)
    allowed_top = {"nodes", "health_interval_seconds", "counter_interval_seconds"}
    if set(raw) - allowed_top:
        raise RuntimeConfigError("node config에 알 수 없는 최상위 필드가 있습니다")
    rows = raw.get("nodes")
    if not isinstance(rows, list) or not rows:
        raise RuntimeConfigError("nodes에는 하나 이상의 exit 노드가 필요합니다")
    nodes = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict) or set(item) != _NODE_FIELDS:
            raise RuntimeConfigError(f"nodes[{index}]의 필드 집합이 계약과 일치하지 않습니다")
        try:
            normalized = dict(item)
            normalized["identity_file"] = pathlib.Path(item["identity_file"])
            normalized["known_hosts_file"] = pathlib.Path(item["known_hosts_file"])
            normalized["dns_addresses"] = tuple(item["dns_addresses"])
            node = SSHNodeSpec(**normalized).validated()
        except (TypeError, ValueError) as exc:
            raise RuntimeConfigError(f"nodes[{index}]가 올바르지 않습니다: {exc}") from exc
        nodes.append(node)
    health = raw.get("health_interval_seconds", 60)
    counters = raw.get("counter_interval_seconds", 60)
    if not isinstance(health, int) or not 30 <= health <= 300:
        raise RuntimeConfigError("health_interval_seconds는 30..300초 정수여야 합니다")
    if not isinstance(counters, int) or not 30 <= counters <= 300:
        raise RuntimeConfigError("counter_interval_seconds는 30..300초 정수여야 합니다")
    return RuntimeSettings(tuple(nodes), health, counters)


class NodePollingService:
    def __init__(self, api: ControlAPI, adapter: SSHNodeAdapter, settings: RuntimeSettings):
        self.api = api
        self.adapter = adapter
        self.settings = settings
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> dict[str, Any]:
        health = self.adapter.poll_health(self.api)
        try:
            counters = self.adapter.poll_counters(self.api)
            counter_error = None
        except (NodeAdapterError, OSError, ValueError) as exc:
            counters = []
            counter_error = type(exc).__name__
        return {"health": health, "counters": counters, "counter_error": counter_error}

    def _run(self) -> None:
        counter_elapsed = self.settings.counter_interval_seconds
        while not self._stop.is_set():
            if counter_elapsed >= self.settings.counter_interval_seconds:
                self.run_once()
                counter_elapsed = 0
            else:
                self.adapter.poll_health(self.api)
            waited = min(self.settings.health_interval_seconds, self.settings.counter_interval_seconds)
            if self._stop.wait(waited):
                break
            counter_elapsed += waited

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="freeflex-node-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def build_runtime(
    storage_path: str | pathlib.Path,
    config_path: str | pathlib.Path,
    *,
    runner=None,
) -> tuple[ControlAPI, SSHNodeAdapter, NodePollingService]:
    settings = load_runtime_settings(config_path)
    adapter = SSHNodeAdapter(storage_path, list(settings.nodes), runner=runner)
    api = ControlAPI(storage_path, peer_provisioner=adapter.provision, peer_revoker=adapter.revoke)
    poller = NodePollingService(api, adapter, settings)
    return api, adapter, poller
