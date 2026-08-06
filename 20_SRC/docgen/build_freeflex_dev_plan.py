#!/usr/bin/env python3
"""기존 개발계획서의 서식을 보존해 FreeFlexVPN 정본을 생성한다."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "60_OUTPUTS"
    / "archive_2026-07-31"
    / "legacy_docs"
    / "Free_Korea_VPN_개발실행계획서.docx"
)
TARGET = ROOT / "60_OUTPUTS" / "FreeFlexVPN_개발실행계획서_v1.0_2026-07-31.docx"

REPLACEMENTS = (
    ("Free Korea VPN", "FreeFlexVPN"),
    ("FreeKoreaVPN", "FreeFlexVPN"),
    ("2026년 7월 30일", "2026년 7월 31일"),
    ("2GB", "1GB"),
    (
        "매월 1일 쿼터 리셋 → 재활성화. 충전 사용자는 별도 잔여량에서 차감",
        "매월 1일 무료 쿼터 리셋 → 재활성화. 충전 사용자는 별도 무기한 잔여량에서 차감",
    ),
    ('<w:tblHeader w:val="false"/>', '<w:tblHeader w:val="true"/>'),
    ('<w:tblHeader/>', '<w:tblHeader w:val="true"/>'),
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def mark_table_headers(payload: bytes) -> bytes:
    root = etree.fromstring(payload)
    ns = {"w": W_NS}
    for table in root.xpath(".//w:tbl", namespaces=ns):
        rows = table.xpath("./w:tr", namespaces=ns)
        if not rows:
            continue
        row = rows[0]
        properties = row.find(f"{{{W_NS}}}trPr")
        if properties is None:
            properties = etree.Element(f"{{{W_NS}}}trPr")
            row.insert(0, properties)
        if properties.find(f"{{{W_NS}}}tblHeader") is None:
            etree.SubElement(properties, f"{{{W_NS}}}tblHeader")
    return etree.tostring(
        root, encoding="UTF-8", xml_declaration=True, standalone=True
    )


def build() -> Path:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffvpn_dev_docx_") as temp_dir:
        temp = Path(temp_dir) / TARGET.name
        with zipfile.ZipFile(SOURCE, "r") as source, zipfile.ZipFile(
            temp, "w", compression=zipfile.ZIP_DEFLATED
        ) as target:
            for info in source.infolist():
                payload = source.read(info.filename)
                if info.filename.endswith(".xml"):
                    text = payload.decode("utf-8")
                    for before, after in REPLACEMENTS:
                        text = text.replace(before, after)
                    payload = text.encode("utf-8")
                    if info.filename == "word/document.xml":
                        payload = mark_table_headers(payload)
                target.writestr(info, payload)
        shutil.copy2(temp, TARGET)
    return TARGET


if __name__ == "__main__":
    result = build()
    digest = hashlib.sha256(result.read_bytes()).hexdigest().upper()
    print(f"{result.relative_to(ROOT)} | {result.stat().st_size:,} bytes | SHA256 {digest}")
