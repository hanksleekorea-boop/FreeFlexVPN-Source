#!/usr/bin/env python3
"""공개 QR 산출물의 형식·디코딩·URL 결속을 검사한다."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "70_TOOLS"))
import make_public_qr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

path = make_public_qr.OUTPUT
checks: list[tuple[str, bool]] = []
checks.append(("Q1 QR 파일 존재", path.is_file()))
raw = path.read_bytes() if path.is_file() else b""
checks.append(("Q2 PNG 매직넘버", raw.startswith(b"\x89PNG\r\n\x1a\n")))
image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR) if raw else None
decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(image) if image is not None else ("", None, None)
checks.append(("Q3 실제 디코더 인식", bool(decoded) and points is not None))
checks.append(("Q4 공개 URL payload 일치", decoded == make_public_qr.PUBLIC_URL))

failed = [label for label, ok in checks if not ok]
if failed:
    for label in failed:
        print(f"  FAIL {label}")
    raise SystemExit(f"공개 QR 검사 {len(checks)-len(failed)}/{len(checks)} 통과 · 실패 {len(failed)}")
print(f"공개 QR 검사 {len(checks)}/{len(checks)} 통과 · SHA256 {hashlib.sha256(raw).hexdigest().upper()}")
