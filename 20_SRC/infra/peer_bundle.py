#!/usr/bin/env python3
"""저장소 밖에만 WireGuard 클라이언트 구성·QR 묶음을 생성한다."""
from __future__ import annotations

import base64
import hashlib
import io
import ipaddress
import json
import os
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from .quota_agent import validate_public_key

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
VPN_NETWORK = ipaddress.ip_network("10.66.0.0/24")
SERVER_IP = ipaddress.ip_address("10.66.0.1")
DEFAULT_DNS = "1.1.1.1"


@dataclass(frozen=True)
class PeerSpec:
    name: str
    server_public_key: str
    endpoint: str
    client_ip: str
    dns: str = DEFAULT_DNS

    def validated(self) -> "PeerSpec":
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?", self.name):
            raise ValueError("피어 이름은 1~32자의 소문자·숫자·하이픈만 허용합니다")
        validate_public_key(self.server_public_key)
        _validate_endpoint(self.endpoint)
        network = ipaddress.ip_network(self.client_ip, strict=True)
        if network.version != 4 or network.prefixlen != 32:
            raise ValueError("클라이언트 주소는 IPv4 /32여야 합니다")
        address = network.network_address
        if address not in VPN_NETWORK or address in {VPN_NETWORK.network_address, SERVER_IP, VPN_NETWORK.broadcast_address}:
            raise ValueError("클라이언트 주소는 10.66.0.2~10.66.0.254의 /32여야 합니다")
        dns = ipaddress.ip_address(self.dns)
        if dns.version != 4 or dns.is_unspecified or dns.is_multicast:
            raise ValueError("DNS는 사용 가능한 IPv4 주소여야 합니다")
        return self


def _validate_endpoint(value: str) -> tuple[str, int]:
    if value.count(":") != 1:
        raise ValueError("endpoint는 hostname:port 또는 IPv4:port 형식이어야 합니다")
    host, port_text = value.rsplit(":", 1)
    if not host or not port_text.isdigit():
        raise ValueError("endpoint 형식이 올바르지 않습니다")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("endpoint 포트 범위가 올바르지 않습니다")
    try:
        address = ipaddress.ip_address(host)
    except ValueError as ip_error:
        if not re.fullmatch(r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", host):
            raise ValueError("endpoint 호스트명이 올바르지 않습니다") from ip_error
    else:
        if address.version != 4 or address.is_unspecified or address.is_multicast:
            raise ValueError("endpoint IPv4를 사용할 수 없습니다")
    return host, port


def generate_keypair(private_bytes: bytes | None = None) -> tuple[str, str]:
    private = X25519PrivateKey.from_private_bytes(private_bytes) if private_bytes is not None else X25519PrivateKey.generate()
    private_raw = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(private_raw).decode("ascii"), base64.b64encode(public_raw).decode("ascii")


def render_client_config(spec: PeerSpec, private_key: str) -> str:
    spec.validated()
    validate_public_key(private_key)
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {spec.client_ip}\n"
        f"DNS = {spec.dns}\n\n"
        "[Peer]\n"
        f"PublicKey = {spec.server_public_key}\n"
        "AllowedIPs = 0.0.0.0/0, ::/0\n"
        f"Endpoint = {spec.endpoint}\n"
        "PersistentKeepalive = 25\n"
    )


def _qr_png(payload: str) -> bytes:
    import cv2
    import numpy as np
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M, ERROR_CORRECT_Q

    # OpenCV가 특정 무작위 키 조합에서 한 가지 QR 밀도를 간헐적으로 읽지 못할 수 있다.
    # 소비자와 같은 디코더 왕복 검증을 유지한 채 더 큰 모듈/복원력 후보로 한 번씩 강화한다.
    for box_size, error_correction in ((16, ERROR_CORRECT_M), (20, ERROR_CORRECT_M), (20, ERROR_CORRECT_Q)):
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction,
            box_size=box_size,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="#000000", back_color="#ffffff")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        raw = buffer.getvalue()
        decoded_image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(decoded_image)
        if points is not None and decoded == payload:
            return raw
    raise RuntimeError("클라이언트 QR 왕복 디코드가 실패했습니다")


def _outside_project(output: pathlib.Path) -> pathlib.Path:
    resolved = output.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return resolved
    raise ValueError("개인키 묶음은 프로젝트·Git 저장소 내부에 만들 수 없습니다")


def build_bundle(
    spec: PeerSpec,
    output_dir: pathlib.Path,
    *,
    private_bytes: bytes | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    spec = spec.validated()
    target = _outside_project(pathlib.Path(output_dir))
    if target.exists():
        raise FileExistsError("출력 폴더가 이미 존재합니다. 기존 개인키를 덮어쓰지 않습니다")
    if not target.parent.exists():
        raise FileNotFoundError("출력 폴더의 부모 경로가 존재하지 않습니다")

    private_key, public_key = generate_keypair(private_bytes)
    config = render_client_config(spec, private_key)
    qr = _qr_png(config)
    created_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    enrollment = {
        "schema_version": 1,
        "product": "FreeFlexVPN",
        "peer_name": spec.name,
        "client_public_key": public_key,
        "allowed_ip": spec.client_ip,
        "endpoint": spec.endpoint,
        "created_at": created_at,
        "contains_private_key": False,
    }
    commands = (
        "# 서버 root 콘솔에서 실행 — 공개키만 포함\n"
        "# <64-char-HMAC-account-id>를 가입 계층의 비가역 가명 계정 ID로 교체\n"
        f"python3 /opt/freeflexvpn/quota_agent.py enroll --account-id '<64-char-HMAC-account-id>' --peer-key '{public_key}' --allowed-ip '{spec.client_ip}'\n"
        "# 폐기 시 아래 한 줄 실행\n"
        f"python3 /opt/freeflexvpn/quota_agent.py revoke --peer-key '{public_key}'\n"
    )
    readme = (
        "FreeFlexVPN 개인 피어 묶음\n\n"
        "- .conf와 QR PNG에는 같은 개인키가 들어 있습니다. 둘 다 외부 공유·Git 업로드 금지입니다.\n"
        "- enrollment.json과 SERVER_COMMANDS.txt에는 공개키만 들어 있습니다.\n"
        "- 등록 명령의 account-id는 Telegram 원본 ID가 아니라 가입 계층이 만든 64자리 HMAC 가명값이어야 합니다.\n"
        "- 계정당 활성 공개키는 2개까지이며 같은 키를 여러 기기에 복사하면 물리 기기 수를 구분할 수 없습니다.\n"
        "- WireGuard 앱에서 QR을 가져온 뒤 원본 파일 보관 여부를 사용자가 결정하십시오.\n"
        "- IPv6는 ::/0을 터널로 보내 서버에서 차단하므로 로컬 IPv6 우회 누수를 허용하지 않습니다.\n"
        "- 폐기 명령 실행 뒤 기존 QR·conf는 다시 연결할 수 없습니다.\n"
    )

    payloads: dict[str, bytes] = {
        f"FreeFlexVPN-{spec.name}.conf": config.encode("utf-8"),
        f"FreeFlexVPN-{spec.name}-QR.png": qr,
        "enrollment.json": (json.dumps(enrollment, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "SERVER_COMMANDS.txt": commands.encode("utf-8"),
        "README.txt": readme.encode("utf-8"),
    }
    manifest = {
        name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for name, raw in payloads.items()
    }
    payloads["BUNDLE_MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    written: list[pathlib.Path] = []
    target.mkdir(mode=0o700)
    try:
        for name, raw in payloads.items():
            path = target / name
            with path.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(path, 0o600)
            written.append(path)
    except Exception:
        for path in reversed(written):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            target.rmdir()
        except OSError:
            pass
        raise
    finally:
        private_key = ""
        config = ""

    return {
        "output_dir": str(target),
        "peer_name": spec.name,
        "client_public_key": public_key,
        "files": manifest,
        "qr_payload_match": True,
        "private_material_in_project": False,
    }
