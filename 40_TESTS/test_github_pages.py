#!/usr/bin/env python3
"""공개 GitHub Pages 묶음의 최소 안전·배포 계약을 검사한다."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))
sys.path.insert(0, str(ROOT / "70_TOOLS"))

import build_web_assets
import build_github_pages

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

build_web_assets.build()
build_github_pages.build()
PUBLIC = build_github_pages.PUBLIC_REPO
CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))


index = PUBLIC / "index.html"
workflow = PUBLIC / ".github" / "workflows" / "pages.yml"
manifest_path = PUBLIC / "PUBLIC_MANIFEST.json"
check("G1 index.html 진입점", index.is_file())
check("G2 Pages workflow", workflow.is_file())
check("G3 공개 묶음 심볼릭 링크 0", not any(p.is_symlink() for p in PUBLIC.rglob("*")))

allowed = {".html", ".md", ".json", ".yml", ".png", ".js", ".py", ".mjs"}
unexpected = [
    p.relative_to(PUBLIC).as_posix()
    for p in PUBLIC.rglob("*")
    if p.is_file() and p.name not in {".nojekyll", ".gitignore"} and ".git" not in p.parts and p.suffix not in allowed
]
check("G4 공개 허용 파일형식만 포함", not unexpected, str(unexpected))

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
actual = {
    p.relative_to(PUBLIC).as_posix()
    for p in PUBLIC.rglob("*")
    if p.is_file() and ".git" not in p.parts and p != manifest_path
}
check("G5 공개 MANIFEST 파일 목록 일치", set(manifest) == actual)
bad_hashes = []
for relative, record in manifest.items():
    path = PUBLIC / relative
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
    if digest != record["sha256"] or (path.is_file() and path.stat().st_size != record["bytes"]):
        bad_hashes.append(relative)
check("G6 공개 MANIFEST 해시·크기 일치", not bad_hashes, str(bad_hashes))

body = index.read_text(encoding="utf-8")
check("G7 제품 계약 노출", all(value in body for value in ("FreeFlexVPN", "1GB", "충전분 무기한", "자동결제 없음")))
check("G7b 실제 서비스형 3단계 사용법", all(value in body for value in ("세 단계면 충분합니다", "기기를 고릅니다", "WireGuard에 추가합니다", "켜고 확인합니다")))
check("G8 정직한 보호 상태 계약", "실제 터널 검사가 성공할 때만 보호됨으로 표시합니다" in body)

app = PUBLIC / "app.html"
app_body = app.read_text(encoding="utf-8") if app.is_file() else ""
check("G9 서비스 앱 v2.6 진입점", app.is_file() and all(value in app_body for value in ('data-service-shell', 'data-svc-view="home"', 'data-svc-view="locations"', 'data-svc-view="usage"', 'data-svc-view="account"', "무료 1GB로 시작", "상태를 꾸미지 않습니다")))
check("G10 PWA 설치·실패 안전 계약", all(value in app_body for value in ("beforeinstallprompt", "appinstalled", "86400000", "catch{}", "location.protocol==='https:'")))
check("G11 브라우저 터치 겹침 검사", all(value in app_body for value in ("layout_probe", "elementFromPoint", "dataset.layoutSafe=safe?'pass':'fail'")))
check("G11b PC 앱 모드 레이아웃 검사", all(value in app_body for value in ("app_layout_probe", "dataset.appLayoutSafe=safe?'pass':'fail'", 'id="appModeToggle"')))

qr = PUBLIC / "app-qr.png"
qr_evidence_path = PUBLIC / "app-qr-evidence.json"
qr_evidence = json.loads(qr_evidence_path.read_text(encoding="utf-8")) if qr_evidence_path.is_file() else {}
qr_hash = hashlib.sha256(qr.read_bytes()).hexdigest() if qr.is_file() else "missing"
check("G12 앱 QR payload·해시", qr_evidence.get("target_url") == qr_evidence.get("decoded_payload") and qr_evidence.get("sha256") == qr_hash)
check("G13 QR 자산·정본 앱 주소 보존", qr.is_file() and 'href="app.html"' in body and "__APP_QR_B64__" not in app_body)

workflow_text = workflow.read_text(encoding="utf-8")
check("G14 Pages 최소 배포 권한", "pages: write" in workflow_text and "id-token: write" in workflow_text)
check(
    "G15 원격 공개검증(무캐시 3회·Chrome·오클루전)",
    workflow_text.count("for probe in 1 2 3") >= 2
    and all(value in workflow_text for value in ("Cache-Control: no-cache", "google-chrome", "--dump-dom", "data-layout-safe", "app-layout-broken.html", "data-layout-safe=\"fail\"")),
)
secret_pattern = re.compile(r"(?:gh[opsu]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})")
leaks = [p.relative_to(PUBLIC).as_posix() for p in PUBLIC.rglob("*") if p.is_file() and secret_pattern.search(p.read_text(encoding="utf-8", errors="ignore"))]
check("G16 공개 묶음 비밀값 패턴 0", not leaks, str(leaks))
modules = ("client_keygen.js", "pwa_api_client.js", "moment_catalog.js", "platform_support.js", "pc_readiness.js", "pwa_runtime.js")
check("G17 PWA API 모듈 6종과 단일 파일 HTML 진입점", all((PUBLIC / name).is_file() for name in modules) and 'data-freeflex-runtime="inline"' in app_body and 'src="./pwa_runtime.js"' not in app_body)
check("G18 API 미설정 기본값은 무네트워크", '<meta name="freeflex-api-base" content="">' in app_body and 'data-api-mode="live"' not in app_body)
check("G19 서비스워커가 API 모듈 앱 셸 보존", all(name in (PUBLIC / "sw.js").read_text(encoding="utf-8") for name in modules))
check("G20 원격 CI가 API 모듈 구문 검사", all(f"node --check {name}" in workflow_text for name in modules))
check("G21 claim referrer·서비스워커 캐시 차단", '<meta name="referrer" content="no-referrer">' in app_body and all(token in (PUBLIC / "sw.js").read_text(encoding="utf-8") for token in ('searchParams.has("claim")', 'searchParams.has("ref")')))

failed = [item for item in CHECKS if not item[1]]
if failed:
    for label, _, detail in failed:
        print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"GitHub Pages 검사 {len(CHECKS)-len(failed)}/{len(CHECKS)} 통과 · 실패 {len(failed)}")
print(f"GitHub Pages 검사 {len(CHECKS)}/{len(CHECKS)} 통과")
