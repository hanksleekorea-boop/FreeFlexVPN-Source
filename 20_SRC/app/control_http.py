#!/usr/bin/env python3
"""FreeFlexVPN 제어 계약을 실행 가능한 최소 HTTP 서비스로 노출한다."""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.control_api import ApiResponse, ControlAPI


MAX_BODY_BYTES = 64 * 1024
DEFAULT_ORIGINS = {"https://hanksleekorea-boop.github.io"}


class ControlRequestHandler(BaseHTTPRequestHandler):
    """reverse proxy 뒤 loopback에서 실행하는 개인정보 최소 HTTP 어댑터."""

    api: ControlAPI
    allowed_origins: set[str] = DEFAULT_ORIGINS
    server_version = "FreeFlexControl/0.1"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # 기본 BaseHTTPRequestHandler 로그는 원격 IP를 남긴다. 방문 IP 보존을 피한다.
        return

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin in self.allowed_origins

    def _read_json(self) -> dict[str, Any] | None:
        length_text = self.headers.get("Content-Length")
        if length_text is None:
            return None
        try:
            length = int(length_text)
        except ValueError as exc:
            raise ValueError("Content-Length가 올바르지 않습니다") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise OverflowError("요청 본문은 64KB 이하여야 합니다")
        if length == 0:
            return None
        if self.headers.get_content_type() != "application/json":
            raise TypeError("Content-Type은 application/json이어야 합니다")
        parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON 본문은 객체여야 합니다")
        return parsed

    def _write(self, response: ApiResponse) -> None:
        payload = json.dumps(response.body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(response.status)
        for key, value in response.headers.items():
            self.send_header(key, value)
        origin = self.headers.get("Origin")
        if origin in self.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _dispatch(self) -> None:
        if not self._origin_allowed():
            self._write(ApiResponse(403, {"error": "ORIGIN_FORBIDDEN", "message": "허용되지 않은 앱 출처입니다"}))
            return
        if self.command == "GET" and self.path.rstrip("/") == "/healthz":
            status = 200 if self.api.persistence_status == "persistent" else 503
            self._write(
                ApiResponse(
                    status,
                    {"status": "ok" if status == 200 else "unavailable", "storage": self.api.persistence_status},
                )
            )
            return
        try:
            body = self._read_json() if self.command in ("POST", "PUT", "PATCH") else None
        except OverflowError as exc:
            self._write(ApiResponse(413, {"error": "BODY_TOO_LARGE", "message": str(exc)}))
            return
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._write(ApiResponse(400, {"error": "INVALID_JSON", "message": str(exc)}))
            return
        response = self.api.handle(
            self.command,
            self.path,
            headers={key: value for key, value in self.headers.items()},
            body=body,
            remote_ip=str(self.client_address[0]),
        )
        self._write(response)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch()

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch()

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._origin_allowed():
            self._write(ApiResponse(403, {"error": "ORIGIN_FORBIDDEN", "message": "허용되지 않은 앱 출처입니다"}))
            return
        self.send_response(204)
        origin = self.headers.get("Origin")
        if origin in self.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-FreeFlex-Device")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()


def create_server(
    api: ControlAPI,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    allowed_origins: set[str] | None = None,
) -> ThreadingHTTPServer:
    class BoundHandler(ControlRequestHandler):
        pass

    BoundHandler.api = api
    BoundHandler.allowed_origins = set(allowed_origins or DEFAULT_ORIGINS)
    return ThreadingHTTPServer((host, port), BoundHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("FFVPN_DB_PATH", "control.sqlite3")))
    parser.add_argument("--host", default=os.environ.get("FFVPN_BIND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FFVPN_PORT", "8787")))
    parser.add_argument(
        "--node-config",
        type=Path,
        default=Path(os.environ["FFVPN_NODE_CONFIG"]) if os.environ.get("FFVPN_NODE_CONFIG") else None,
        help="프로젝트 밖 실서버 JSON 설정의 절대 경로",
    )
    parser.add_argument(
        "--origin",
        action="append",
        dest="origins",
        help="허용할 정확한 HTTPS Origin. 반복 가능",
    )
    args = parser.parse_args(argv)
    origins = set(args.origins) if args.origins else DEFAULT_ORIGINS
    if any(not origin.startswith("https://") for origin in origins):
        parser.error("공개 앱 Origin은 https://여야 합니다")
    poller = None
    if args.node_config is not None:
        from app.control_runtime import build_runtime

        api, _adapter, poller = build_runtime(args.db, args.node_config)
        poller.run_once()
    else:
        api = ControlAPI(args.db)
    server = create_server(api, host=args.host, port=args.port, allowed_origins=origins)
    try:
        if poller is not None:
            poller.start()
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if poller is not None:
            poller.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
