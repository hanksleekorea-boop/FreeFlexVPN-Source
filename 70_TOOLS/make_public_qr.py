#!/usr/bin/env python3
"""FreeFlexVPN 공개 URL QR을 생성하고 실제 디코더로 왕복 검증한다."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_Q


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_URL = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html"
OUTPUT = ROOT / "60_OUTPUTS" / "FreeFlexVPN_PUBLIC_QR_v1_2026-07-31.png"
EVIDENCE = ROOT / "60_OUTPUTS" / "checks" / "public_qr_v1.json"


def build() -> dict[str, object]:
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_Q, box_size=12, border=4)
    qr.add_data(PUBLIC_URL)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#07101d", back_color="#ffffff")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)

    qr_image = cv2.imdecode(np.frombuffer(OUTPUT.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(qr_image)
    result = {
        "public_url": PUBLIC_URL,
        "decoded_payload": decoded,
        "payload_match": decoded == PUBLIC_URL,
        "detected": points is not None,
        "bytes": OUTPUT.stat().st_size,
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest().upper(),
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not result["payload_match"]:
        raise SystemExit(f"QR payload 불일치: {decoded!r}")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
