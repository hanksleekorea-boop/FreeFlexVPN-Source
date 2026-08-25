#!/usr/bin/env python3
"""CC-TASK-1-07 계정 자료 내보내기·삭제 화면과 서버 계약 검사."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
api = (ROOT / "20_SRC/app/control_api.py").read_text(encoding="utf-8")
client = (ROOT / "20_SRC/app/pwa_api_client.js").read_text(encoding="utf-8")
runtime = (ROOT / "20_SRC/app/pwa_runtime.js").read_text(encoding="utf-8")
shell = (ROOT / "20_SRC/html_templates/service_shell.html").read_text(encoding="utf-8")
migration = (ROOT / "20_SRC/app/db_migrations/001_v2_alpha.sql").read_text(encoding="utf-8")

checks = {
    "최근 5분 세션 재확인": "DATA_RIGHTS_REAUTH_MINUTES = 5" in api and "RECENT_AUTH_REQUIRED" in api,
    "계정 범위 JSON 내보내기": "FreeFlexVPNAccountExportV1" in api and "scope_notice" in api,
    "개인키·세션 열쇠 제외": all(value in api for value in ("wireguard_private_keys", "api_session_tokens", '"contains_private_keys": False')),
    "삭제 명시 확인": 'body.get("confirm") != "DELETE"' in api and 'body: { confirm: "DELETE" }' in client,
    "삭제 상태 열쇠 해시 저장": "deletion_status_tokens" in migration and "status_token_hash" in migration and "_digest(status_token)" in api,
    "삭제 완료 과장 금지": "completion_is_verified" in api and "아직 삭제 완료가 아니며" in runtime,
    "내보내기·삭제·상태 UI": all(value in shell for value in ("data-account-export", "data-account-delete", "data-deletion-receipt")),
    "삭제 영수증 자동 영구 저장 없음": "localStorage.setItem" not in runtime[runtime.index('document.querySelector("[data-account-delete]")'):runtime.index('document.querySelector("[data-pc-download-diagnostic]")')],
}

failed = [label for label, ok in checks.items() if not ok]
if failed:
    raise SystemExit(f"계정 자료 권리 검사 {len(checks)-len(failed)}/{len(checks)} 통과 · 실패: {', '.join(failed)}")
print(f"계정 자료 권리 검사 {len(checks)}/{len(checks)} 통과")
