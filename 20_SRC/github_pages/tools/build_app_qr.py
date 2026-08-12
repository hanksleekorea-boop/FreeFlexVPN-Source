#!/usr/bin/env python3
"""Build and decode-verify the stable public app QR."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

import cv2
import numpy as np
import qrcode

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_URL = os.environ.get(
    "FREEFLEX_PUBLIC_APP_URL",
    "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html",
)
QR_PATH = ROOT / "app-qr.png"
EVIDENCE_PATH = ROOT / "app-qr-evidence.json"


def main() -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    qr.make_image(fill_color="#07101d", back_color="white").convert("RGB").save(QR_PATH)

    image = cv2.imdecode(np.frombuffer(QR_PATH.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    if decoded != TARGET_URL:
        raise SystemExit(f"QR decode mismatch: {decoded!r}")

    raw = QR_PATH.read_bytes()
    evidence = {
        "target_url": TARGET_URL,
        "decoded_payload": decoded,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"QR decode PASS: {decoded}")
    print(f"SHA-256: {evidence['sha256']} ({len(raw)} bytes)")


if __name__ == "__main__":
    main()
