#!/usr/bin/env python3
"""정책 초안·데이터 지도·현재 저장 스키마의 최소 일관성 검사."""
from __future__ import annotations

import pathlib
import re
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = (ROOT / "60_OUTPUTS" / "policy_drafts" / "FreeFlexVPN_약관_개인정보_국외이전_초안팩_v0.1_2026-08-03.md").read_text(encoding="utf-8")
MAP = (ROOT / "10_STATE" / "POLICY_CODE_CONSISTENCY_v0.2_2026-08-03.md").read_text(encoding="utf-8")
SQL = (ROOT / "20_SRC" / "app" / "db_migrations" / "001_v2_alpha.sql").read_text(encoding="utf-8")
TELEGRAM_CONFIG = (ROOT / "20_SRC" / "infra" / "telegram_bot_config.py").read_text(encoding="utf-8")
PWA_CLIENT = (ROOT / "20_SRC" / "app" / "pwa_api_client.js").read_text(encoding="utf-8")
CLIENT_KEYGEN = (ROOT / "20_SRC" / "app" / "client_keygen.js").read_text(encoding="utf-8")


class PolicyConsistencyTests(unittest.TestCase):
    def test_draft_is_fail_closed_until_placeholders_and_review_are_resolved(self):
        self.assertIn("공개·동의 수집·서비스 적용 금지", POLICY)
        self.assertGreaterEqual(POLICY.count("[확정 필요]"), 10)
        self.assertIn("한국 개인정보·소비자법 전문가 검토", POLICY)

    def test_product_promises_are_consistent(self):
        for phrase in ("월 1GB", "미사용 충전분 무기한 보존", "무료량을 먼저 사용"):
            self.assertIn(phrase, POLICY)
        self.assertIn("자동결제 없음", (ROOT / "20_SRC" / "html_templates" / "app_v2.html").read_text(encoding="utf-8"))

    def test_code_map_discloses_all_current_server_data_categories(self):
        phrases = (
            "가명 계정 식별자", "동의 여부·정책 버전·동의 시각", "SHA-256 해시",
            "WireGuard 공개키", "기기 ID", "배정 내부 주소", "서버 ID",
            "송수신 누적량", "지갑·차감·세션 요약 원장", "추천 관계·자격 사용량·보상 원장",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, MAP)

    def test_telegram_config_and_policy_map_share_stored_fields(self):
        for field in ("hmac_user_ref", "consent_version", "claim_sha256", "peer_public_key", "allowed_ip"):
            self.assertIn(f'"{field}"', TELEGRAM_CONFIG)
        for phrase in ("가명 계정", "정책 버전", "수령권", "공개키", "내부 주소"):
            self.assertIn(phrase, MAP)

    def test_raw_identity_token_and_private_key_are_explicitly_not_stored(self):
        for phrase in (
            "Telegram 원본 사용자 ID", "username", "전화번호", "메시지 원문",
            "로그인 수령권 원문", "API 세션 원문", "WireGuard 클라이언트 개인키",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, MAP)

    def test_database_schema_has_hashes_and_no_forbidden_identity_columns(self):
        for column in ("claim_hash", "session_hash", "wg_public_key", "token_hash"):
            self.assertRegex(SQL, rf"\b{column}\b")
        for forbidden in ("client_private_key", "telegram_user_id", "username", "phone_number", "message_text"):
            self.assertIsNone(re.search(rf"\b{forbidden}\b", SQL, flags=re.IGNORECASE))

    def test_browser_session_token_scope_matches_policy_map(self):
        self.assertIn("globalThis.sessionStorage", PWA_CLIENT)
        self.assertNotIn("globalThis.localStorage", PWA_CLIENT)
        self.assertIn("sessionStorage", MAP)
        self.assertIn("메모리", MAP)

    def test_private_key_never_leaves_client_contract(self):
        self.assertIn("client_private_key", TELEGRAM_CONFIG)
        self.assertIn("The private key is generated and used only in this browser context", CLIENT_KEYGEN)
        self.assertIn("body: JSON.stringify({ wg_public_key: publicKey, server_id: serverId })", CLIENT_KEYGEN)
        self.assertNotIn("body: JSON.stringify({ privateKey", CLIENT_KEYGEN)
        self.assertIn("개인키는 서비스가 보유하지 않는 구조", POLICY)

    def test_traffic_content_and_dns_queries_are_not_collection_claims(self):
        for phrase in ("방문 사이트", "통신 내용", "DNS 질의 원문"):
            self.assertIn(phrase, POLICY)
            self.assertIn(phrase, MAP)
        self.assertIn("완전한 노로그", MAP)
        self.assertIn("주장하지 않는다", MAP)

    def test_unresolved_operations_remain_visible(self):
        for phrase in ("원본 IP", "보존 및 파기 주기", "처리 국가", "탈퇴 뒤 잔액", "만 14세 미만"):
            self.assertIn(phrase, MAP)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PolicyConsistencyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"정책-코드 일관성 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
