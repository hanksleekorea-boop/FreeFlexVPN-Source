from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_freeflex_business_plan.py <docx>")

    path = Path(sys.argv[1]).resolve()
    raw = path.read_bytes()
    xml_errors: list[str] = []

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        xml_parts: dict[str, str] = {}
        for name in names:
            if not name.endswith(".xml"):
                continue
            data = archive.read(name)
            try:
                ET.fromstring(data)
            except ET.ParseError as exc:
                xml_errors.append(f"{name}: {exc}")
            xml_parts[name] = data.decode("utf-8")

        document_root = ET.fromstring(archive.read("word/document.xml"))

    package_text = "\n".join(xml_parts.values())
    document_text = "".join(node.text or "" for node in document_root.findall(".//w:t", NS))
    table_header_indexes: list[list[int]] = []
    for table in document_root.findall(".//w:tbl", NS):
        flagged: list[int] = []
        for index, row in enumerate(table.findall("./w:tr", NS)):
            if row.find("./w:trPr/w:tblHeader", NS) is not None:
                flagged.append(index)
        table_header_indexes.append(flagged)
    invalid_header_indexes = [indexes for indexes in table_header_indexes if any(index != 0 for index in indexes)]

    required_fragments = [
        "FreeFlexVPN",
        "월 1GB",
        "충전 용량은 만료 없이 남는 VPN",
        "VPN이 상시가 아니라 상황별 도구인 라이트 사용자",
        "무료 상한(확정) — 월 1GB로 운영한다.",
        "14TB41,160원91만원76%",
        "18TB52,920원215만원86%",
        "26TB76,440원434만원91%",
        "42TB123,480원892만원93%",
        "11개월11,000명11.0TB102Mbps1대46,931원4.3원",
        "24개월24,000명24.0TB222Mbps2대60,480원2.5원",
        "36개월36,000명36.0TB333Mbps2대60,480원1.7원",
        "3년 누적 약 189만원",
    ]
    forbidden_fragments = [
        "Free Korea VPN",
        "월 2GB",
        "1인 2GB 상한",
        "무료 상한 — 2GB",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in document_text]
    forbidden = [fragment for fragment in forbidden_fragments if fragment in package_text]

    report = {
        "file": str(path),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "zip_entries": len(names),
        "xml_invalid": xml_errors,
        "table_count": len(table_header_indexes),
        "table_header_indexes": table_header_indexes,
        "invalid_table_header_indexes": invalid_header_indexes,
        "required_missing": missing,
        "forbidden_present": forbidden,
        "status": "PASS" if not xml_errors and not missing and not forbidden and not invalid_header_indexes else "FAIL",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
