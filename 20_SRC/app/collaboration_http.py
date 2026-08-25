#!/usr/bin/env python3
"""Same-origin HTTP shell for the FreeFlexVPN collaboration gateway."""
from __future__ import annotations

import argparse
import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app.collaboration_gateway import (
    CollaborationGateway, GatewayError, GatewayResult, ProjectContext, as_error,
)
from app.collaboration_runtime import (
    GitHubIntegrationBroker, SessionWorktreeManager, SignedDriveOutbox,
)
from app.collaboration_workspace import SafeWorkspace, WorkspaceError


MAX_BODY_BYTES = 32 * 1024
COOKIE_NAME = "ffvpn_collab"
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class CollaborationRequestHandler(BaseHTTPRequestHandler):
    gateway: CollaborationGateway
    portal_path: Path
    allowed_origin: str
    workspace: SafeWorkspace | None = None
    workspace_manager: SessionWorktreeManager | None = None
    integration_broker: GitHubIntegrationBroker | None = None
    python_executable: str = "python"
    server_version = "FreeFlexCollaboration/0.1"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # BaseHTTPRequestHandler includes the visitor IP in its default log.
        return

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin == self.allowed_origin

    def _session_token(self) -> str:
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else ""

    def _workspace_for_session(self) -> SafeWorkspace:
        token = self._session_token()
        self.gateway.status(token)
        if self.workspace_manager is not None:
            return self.workspace_manager.workspace_for(token)
        if self.workspace is not None:
            return self.workspace
        raise GatewayError(503, "WORKSPACE_UNAVAILABLE", "서버 작업공간이 아직 연결되지 않았습니다")

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise GatewayError(400, "INVALID_BODY", "Content-Length가 올바르지 않습니다") from exc
        if length <= 0 or length > MAX_BODY_BYTES:
            raise GatewayError(413 if length > MAX_BODY_BYTES else 400, "INVALID_BODY", "요청 본문 크기가 올바르지 않습니다")
        if self.headers.get_content_type() != "application/json":
            raise GatewayError(415, "JSON_REQUIRED", "application/json 본문이 필요합니다")
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GatewayError(400, "INVALID_JSON", "JSON 본문이 올바르지 않습니다") from exc
        if not isinstance(body, dict):
            raise GatewayError(400, "INVALID_JSON", "JSON 객체가 필요합니다")
        return body

    def _base_headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(length))

    def _write_json(self, result: GatewayResult, *, set_cookie: str | None = None, clear_cookie: bool = False) -> None:
        payload = json.dumps(result.body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(result.status)
        self._base_headers("application/json; charset=utf-8", len(payload))
        if set_cookie is not None:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}={set_cookie}; Path=/api/development; Max-Age=900; HttpOnly; Secure; SameSite=Strict",
            )
        elif clear_cookie:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}=; Path=/api/development; Max-Age=0; HttpOnly; Secure; SameSite=Strict",
            )
        self.end_headers()
        self.wfile.write(payload)

    def _write_portal(self) -> None:
        payload = self.portal_path.read_bytes()
        self.send_response(200)
        self._base_headers("text/html; charset=utf-8", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def _write_script(self) -> None:
        script_path = self.portal_path.with_name("collaboration-portal.js")
        payload = script_path.read_bytes()
        self.send_response(200)
        self._base_headers("text/javascript; charset=utf-8", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def _dispatch(self) -> None:
        if not self._origin_allowed():
            self._write_json(GatewayResult(403, {"error": "ORIGIN_FORBIDDEN", "message": "허용되지 않은 출처입니다"}))
            return
        try:
            if self.command == "GET" and self.path in ("/", "/collaboration"):
                self._write_portal()
                return
            if self.command == "GET" and self.path == "/collaboration-portal.js":
                self._write_script()
                return
            if self.command == "GET" and self.path == "/healthz":
                self._write_json(GatewayResult(200, {
                    "status": "ok", "secrets_exposed": False,
                    "session_worktrees": self.workspace_manager is not None,
                    "integration_broker": self.integration_broker is not None,
                }))
                return
            if self.command == "GET" and self.path == "/.well-known/ai-development.json":
                self._write_json(GatewayResult(200, {
                    "schema": "FreeFlexAIDevelopmentV1",
                    "project": self.gateway.context.public_card(),
                    "authentication": "password_session",
                    "session_minutes": 15,
                    "capabilities": {
                        "context": self.workspace is not None or self.workspace_manager is not None,
                        "read": self.workspace is not None or self.workspace_manager is not None,
                        "search": self.workspace is not None or self.workspace_manager is not None,
                        "write": self.workspace is not None or self.workspace_manager is not None,
                        "diff": self.workspace is not None or self.workspace_manager is not None,
                        "commit": self.workspace is not None or self.workspace_manager is not None,
                        "checks": self.workspace is not None or self.workspace_manager is not None,
                        "integration_request": self.integration_broker is not None,
                        "protected_deploy": self.gateway.release_broker is not None,
                        "arbitrary_shell": False,
                        "owner_admin": False,
                        "secret_read": False,
                    },
                }))
                return
            if self.command == "POST" and self.path == "/api/development/login":
                body = self._read_json()
                password = body.get("password")
                if not isinstance(password, str):
                    raise GatewayError(401, "LOGIN_FAILED", "비밀번호가 올바르지 않습니다")
                result = self.gateway.login(password, client_hint=str(self.client_address[0]))
                session_token = str(result.body.pop("session_token"))
                self._write_json(result, set_cookie=session_token)
                return
            if self.command == "GET" and self.path == "/api/development/status":
                self._write_json(self.gateway.status(self._session_token()))
                return
            if self.command == "GET" and self.path == "/api/development/context":
                self._write_json(GatewayResult(200, self._workspace_for_session().context()))
                return
            parsed = urlsplit(self.path)
            if self.command == "GET" and parsed.path == "/api/development/read":
                path = parse_qs(parsed.query).get("path", [""])[0]
                self._write_json(GatewayResult(200, self._workspace_for_session().read(path)))
                return
            if self.command == "GET" and parsed.path == "/api/development/search":
                query = parse_qs(parsed.query)
                self._write_json(GatewayResult(200, self._workspace_for_session().search(
                    query.get("q", [""])[0], prefix=query.get("prefix", [""])[0]
                )))
                return
            if self.command == "GET" and self.path == "/api/development/diff":
                self._write_json(GatewayResult(200, self._workspace_for_session().diff()))
                return
            if self.command == "PUT" and self.path == "/api/development/write":
                workspace = self._workspace_for_session()
                body = self._read_json(); operation_id = str(body.get("operation_id", ""))
                result = self.gateway.perform_workspace_operation(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""),
                    operation_id=operation_id, action="workspace.write", request=body,
                    callback=lambda: GatewayResult(200, workspace.write(
                        str(body.get("path", "")), str(body.get("content", "")),
                        expected_revision=str(body.get("expected_revision", "")), operation_id=operation_id,
                    )),
                )
                self._write_json(result); return
            if self.command == "POST" and self.path == "/api/development/commit":
                workspace = self._workspace_for_session()
                body = self._read_json(); operation_id = str(body.get("operation_id", ""))
                result = self.gateway.perform_workspace_operation(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""),
                    operation_id=operation_id, action="workspace.commit", request=body,
                    callback=lambda: GatewayResult(201, workspace.commit(
                        str(body.get("message", "")), list(body.get("paths", [])),
                    )),
                )
                self._write_json(result); return
            if self.command == "POST" and self.path.startswith("/api/development/checks/"):
                workspace = self._workspace_for_session()
                check_id = self.path.rsplit("/", 1)[-1]
                body = self._read_json(); operation_id = str(body.get("operation_id", ""))
                result = self.gateway.perform_workspace_operation(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""),
                    operation_id=operation_id, action="workspace.check", request={**body, "check_id": check_id},
                    callback=lambda: GatewayResult(200, workspace.run_check(
                        check_id, python_executable=self.python_executable,
                    )),
                )
                self._write_json(result); return
            if self.command == "POST" and self.path == "/api/development/integration-request":
                if self.integration_broker is None:
                    raise GatewayError(503, "INTEGRATION_BROKER_UNAVAILABLE", "통합 요청 중계가 아직 연결되지 않았습니다")
                workspace = self._workspace_for_session()
                body = self._read_json(); operation_id = str(body.get("operation_id", ""))
                result = self.gateway.perform_workspace_operation(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""),
                    operation_id=operation_id, action="workspace.integration", request=body,
                    callback=lambda: GatewayResult(202, self.integration_broker.request(
                        workspace, operation_id=operation_id,
                        title=str(body.get("title", "")), body=str(body.get("body", "")),
                    )),
                )
                self._write_json(result); return
            if self.command == "POST" and self.path == "/api/development/deployments/prepare":
                body = self._read_json()
                self._write_json(self.gateway.prepare_deployment(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""), body
                ))
                return
            prefix = "/api/development/deployments/"
            suffix = "/execute"
            if self.command == "POST" and self.path.startswith(prefix) and self.path.endswith(suffix):
                deployment_id = self.path[len(prefix):-len(suffix)]
                body = self._read_json()
                self._write_json(self.gateway.execute_deployment(
                    self._session_token(), self.headers.get("X-FreeFlex-CSRF", ""),
                    deployment_id, body,
                ))
                return
            raise GatewayError(404, "NOT_FOUND", "요청한 공동개발 기능이 없습니다")
        except WorkspaceError as exc:
            self._write_json(GatewayResult(exc.status, {"error": exc.code, "message": exc.message}))
        except GatewayError as exc:
            self._write_json(as_error(exc))

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch()


def create_server(
    gateway: CollaborationGateway,
    *,
    portal_path: str | Path,
    allowed_origin: str,
    host: str = "127.0.0.1",
    port: int = 8790,
    workspace: SafeWorkspace | None = None,
    workspace_manager: SessionWorktreeManager | None = None,
    integration_broker: GitHubIntegrationBroker | None = None,
    python_executable: str = "python",
) -> ThreadingHTTPServer:
    path = Path(portal_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if not allowed_origin.startswith("https://"):
        raise ValueError("공개 공동개발 출처는 정확한 HTTPS Origin이어야 합니다")

    class BoundHandler(CollaborationRequestHandler):
        pass

    BoundHandler.gateway = gateway
    BoundHandler.portal_path = path
    BoundHandler.allowed_origin = allowed_origin.rstrip("/")
    BoundHandler.workspace = workspace
    BoundHandler.workspace_manager = workspace_manager
    BoundHandler.integration_broker = integration_broker
    BoundHandler.python_executable = python_executable
    return ThreadingHTTPServer((host, port), BoundHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("FFVPN_COLLAB_DB", "collaboration.sqlite3")))
    parser.add_argument("--host", default=os.environ.get("FFVPN_COLLAB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FFVPN_COLLAB_PORT", "8790")))
    parser.add_argument("--origin", default=os.environ.get("FFVPN_COLLAB_ORIGIN", ""))
    parser.add_argument("--portal", type=Path, default=Path(__file__).parents[2] / "html_templates" / "collaboration_portal.html")
    args = parser.parse_args(argv)
    password = os.environ.get("FFVPN_COLLAB_PASSWORD")
    if not password:
        parser.error("FFVPN_COLLAB_PASSWORD는 호스팅 비밀 저장소에서 주입해야 합니다")
    if not args.origin:
        parser.error("FFVPN_COLLAB_ORIGIN이 필요합니다")
    context = ProjectContext(
        project_id="freeflexvpn",
        project_name="FreeFlexVPN",
        repository="hanksleekorea-boop/FreeFlexVPN-Source",
        production_branch="feature/pc-commercial-readiness-90",
        integration_branch="shared-development",
        production_environment="gcs-existing-production",
        production_url="https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
    )
    gateway = CollaborationGateway(args.db, context=context, bootstrap_password=password)
    workspace = None
    workspace_manager = None
    workspace_root = os.environ.get("FFVPN_COLLAB_WORKSPACE")
    workspace_branch = os.environ.get("FFVPN_COLLAB_SESSION_BRANCH")
    if workspace_root or workspace_branch:
        if not workspace_root or not workspace_branch:
            parser.error("작업공간 경로와 세션 브랜치를 함께 설정해야 합니다")
        workspace = SafeWorkspace(Path(workspace_root), workspace_branch)
    source_repo = os.environ.get("FFVPN_COLLAB_SOURCE_REPO")
    sessions_root = os.environ.get("FFVPN_COLLAB_SESSIONS_ROOT")
    if source_repo or sessions_root:
        if workspace is not None or not source_repo or not sessions_root:
            parser.error("정적 작업공간과 세션 작업공간을 함께 쓰지 말고 두 세션 경로를 모두 설정하세요")
        workspace_manager = SessionWorktreeManager(
            Path(source_repo), Path(sessions_root), context.repository,
            base_ref=f"origin/{context.integration_branch}",
        )
    outbox = None
    outbox_root = os.environ.get("FFVPN_COLLAB_DRIVE_OUTBOX")
    outbox_key = os.environ.get("FFVPN_COLLAB_DRIVE_SIGNING_KEY")
    if outbox_root or outbox_key:
        if not outbox_root or not outbox_key:
            parser.error("Drive 발신함 경로와 서명키를 함께 설정해야 합니다")
        outbox = SignedDriveOutbox(outbox_root, outbox_key.encode("utf-8"))
    integration_broker = None
    if os.environ.get("FFVPN_COLLAB_GITHUB_ENABLED") == "1":
        if workspace is None and workspace_manager is None:
            parser.error("GitHub 중계에는 작업공간이 필요합니다")
        integration_broker = GitHubIntegrationBroker(
            repository=context.repository, integration_branch=context.integration_branch,
            gh_executable=os.environ.get("FFVPN_COLLAB_GH", "gh"), outbox=outbox,
        )
    server = create_server(
        gateway, portal_path=args.portal, allowed_origin=args.origin, host=args.host, port=args.port,
        workspace=workspace, workspace_manager=workspace_manager, integration_broker=integration_broker,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
