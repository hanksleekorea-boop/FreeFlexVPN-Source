#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import ipaddress
import ssl
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from playwright.sync_api import sync_playwright


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

from app.collaboration_gateway import CollaborationGateway, ProjectContext  # noqa: E402
from app.collaboration_http import create_server  # noqa: E402
from app.collaboration_workspace import SafeWorkspace  # noqa: E402


PASSWORD = "correct horse battery staple 2026"
checks: list[tuple[str, bool]] = []


def check(name: str, value: object) -> None:
    checks.append((name, bool(value)))


with tempfile.TemporaryDirectory(prefix="ffvpn_portal_ui_") as temp:
    temp_path = pathlib.Path(temp)
    now = datetime.now(timezone.utc)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )
    cert_path = temp_path / "localhost-cert.pem"
    key_path = temp_path / "localhost-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ProjectContext(
        project_id="freeflexvpn", project_name="FreeFlexVPN",
        repository="hanksleekorea-boop/FreeFlexVPN-Source",
        production_branch="feature/pc-commercial-readiness-90",
        integration_branch="shared-development",
        production_environment="gcs-existing-production",
        production_url="https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
    )
    gateway = CollaborationGateway(
        temp_path / "gateway.sqlite3", context=context, bootstrap_password=PASSWORD,
    )
    repo = temp_path / "repo"; repo.mkdir()
    for arguments in (
        ("init",), ("config", "user.name", "Session Worker"),
        ("config", "user.email", "session@invalid"), ("config", "core.autocrlf", "false"),
    ):
        subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)
    (repo / "20_SRC" / "app").mkdir(parents=True)
    (repo / "20_SRC" / "app" / "collaboration_runtime.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "ai-session/ui/task"], cwd=repo, check=True, capture_output=True)
    workspace = SafeWorkspace(repo, "ai-session/ui/task")
    server = create_server(
        gateway, portal_path=ROOT / "20_SRC" / "html_templates" / "collaboration_portal.html",
        allowed_origin="https://placeholder.invalid", port=0, workspace=workspace,
    )
    origin = f"https://127.0.0.1:{server.server_port}"
    server.RequestHandlerClass.allowed_origin = origin
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certfile=cert_path, keyfile=key_path)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            browser_context = browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 360, "height": 800},
            )
            page = browser_context.new_page()
            page.goto(f"{origin}/collaboration")
            check("360px 가로 넘침 0", page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            check("제목·비밀번호 레이블", page.get_by_role("heading", name="FreeFlexVPN 공동개발").is_visible() and page.get_by_label("공동개발 비밀번호").is_visible())
            page.keyboard.press("Tab")
            check("키보드 첫 초점 비밀번호", page.evaluate("document.activeElement && document.activeElement.id === 'password'"))
            page.get_by_label("공동개발 비밀번호").fill(PASSWORD)
            page.get_by_role("button", name="안전하게 시작").click()
            page.get_by_text("로그인 완료", exact=False).wait_for()
            check("로그인 성공 신호", page.locator("#message.ok").is_visible())
            check("미연결 기능 정직 표시", "policy_only" in page.locator("#status").inner_text())
            page.get_by_role("button", name="최신 파일 읽기").click()
            page.get_by_text("최신판을 읽었습니다", exact=False).wait_for()
            check("브라우저 파일 읽기", page.locator("#file-content").input_value().replace("\r\n", "\n") == "VALUE = 1\n")
            page.locator("#file-content").fill("VALUE = 2\n")
            page.get_by_role("button", name="안전하게 저장").click()
            page.get_by_text("격리 작업공간에 저장했습니다.", exact=True).wait_for()
            page.get_by_role("button", name="현재 파일 커밋").click()
            page.get_by_text("커밋 완료", exact=False).wait_for()
            check("브라우저 저장·커밋", subprocess.run(
                ["git", "status", "--porcelain"], cwd=repo, text=True, capture_output=True, check=True,
            ).stdout == "")
            page.set_viewport_size({"width": 720, "height": 900})
            page.evaluate("document.documentElement.style.zoom='2'")
            check("200% 확대 핵심 입력 가시", page.get_by_label("공동개발 비밀번호").is_visible())
            check("200% 확대 행동 버튼 가시", page.get_by_role("button", name="안전하게 시작").is_visible())
            browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed:
    raise SystemExit("공동개발 포털 UI 실패: " + ", ".join(failed))
print(f"공동개발 포털 UI {len(checks)}/{len(checks)} 통과")
