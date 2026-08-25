#!/usr/bin/env python3
"""공개 검증기가 숨은 구형 프로토타입 대신 현재 고객 서비스 UI를 검사하는지 고정한다."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "70_TOOLS" / "verify_public_pc_v2_5.py").read_text(encoding="utf-8")

checks = (
    "data-service-shell" in SOURCE,
    all(selector in SOURCE for selector in (".svc-side", ".svc-main", ".svc-aside", ".svc-mobile-nav")),
    "development-dashboard.html" in SOURCE,
    "data-progress-dashboard" in SOURCE,
    "FreeFlexVPNPublicServiceEvidenceV2" in SOURCE,
    "contains_sensitive_data" in SOURCE,
    ".phone" not in SOURCE,
    "github_commit" not in SOURCE,
)

if not all(checks):
    raise SystemExit(f"공개 검증기 계약 {sum(checks)}/{len(checks)} 통과")
print(f"공개 검증기 계약 {len(checks)}/{len(checks)} 통과")
