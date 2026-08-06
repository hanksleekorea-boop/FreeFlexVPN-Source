from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
Q = f"{{{W}}}"

REQUIRED = [
    "가끔 VPN이 필요한 순간, 구독 없이 바로 보호받고 필요한 데이터만 평생 보관해 쓰는 라이트 VPN",
    "무료 사용자를 포함한 모든 사용자에게 VPN 안전 기본기를 제공한다",
    "공용 Wi-Fi 보호",
    "여행 중 잠깐 사용",
    "다른 국가의 공개 웹 확인",
    "연결 문제 해결",
    "VPN 보호 확인됨",
    "무료 데이터",
    "함께 받은 데이터",
    "구매 데이터",
    "친구가 실제로 써 보면 둘 다 500MB",
    "첫 실제 터널에 성공하고 누적 100MB 사용",
    "추천인 기준 월 5건",
    "100GB·300GB",
    "파일럿 전 기본 노출 중단",
    "PWA와 공식 WireGuard",
    "R3 — 진실한 안전 기반",
    "R9 — 네이티브 앱 결정 게이트",
    "실제 VPN 서버",
]

FORBIDDEN_CLAIMS = [
    "가장 안전한 VPN입니다",
    "가장 빠른 VPN입니다",
    "모든 스트리밍 완벽 해제됩니다",
    "완전한 노로그를 보장합니다",
    "대한민국 · 서울표준 서버",
]


def read_docx(path: Path):
    errors = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            if name.endswith(".xml"):
                try:
                    ET.fromstring(archive.read(name))
                except ET.ParseError as exc:
                    errors.append(f"{name}: {exc}")
        document = ET.fromstring(archive.read("word/document.xml"))
        numbering = ET.fromstring(archive.read("word/numbering.xml"))
    text = "".join(node.text or "" for node in document.findall(".//w:t", NS))
    return document, numbering, text, names, errors


def validate_text(text):
    return {
        "missing": [value for value in REQUIRED if value not in text],
        "forbidden": [value for value in FORBIDDEN_CLAIMS if value in text],
    }


def validate_tables(document):
    errors = []
    tables = document.findall(".//w:tbl", NS)
    for table_index, table in enumerate(tables):
        grid = [int(node.get(Q + "w")) for node in table.findall("./w:tblGrid/w:gridCol", NS)]
        tbl_w = table.find("./w:tblPr/w:tblW", NS)
        tbl_ind = table.find("./w:tblPr/w:tblInd", NS)
        if not grid or sum(grid) != 9360:
            errors.append(f"table {table_index}: grid total {sum(grid) if grid else 0}")
        if tbl_w is None or tbl_w.get(Q + "w") != "9360" or tbl_w.get(Q + "type") != "dxa":
            errors.append(f"table {table_index}: invalid tblW")
        if tbl_ind is None or tbl_ind.get(Q + "w") != "120" or tbl_ind.get(Q + "type") != "dxa":
            errors.append(f"table {table_index}: invalid tblInd")
        rows = table.findall("./w:tr", NS)
        if rows and rows[0].find("./w:trPr/w:tblHeader", NS) is None:
            errors.append(f"table {table_index}: header not repeated")
        for row_index, row in enumerate(rows):
            cells = row.findall("./w:tc", NS)
            if len(cells) != len(grid):
                errors.append(f"table {table_index} row {row_index}: cell count")
                continue
            widths = []
            for cell in cells:
                width = cell.find("./w:tcPr/w:tcW", NS)
                if width is None:
                    widths.append(-1)
                else:
                    widths.append(int(width.get(Q + "w")))
            if widths != grid:
                errors.append(f"table {table_index} row {row_index}: widths {widths} != {grid}")
    return len(tables), errors


def validate_page(document):
    section = document.find(".//w:sectPr", NS)
    if section is None:
        return ["missing sectPr"]
    size = section.find("./w:pgSz", NS)
    margins = section.find("./w:pgMar", NS)
    errors = []
    if size is None or size.get(Q + "w") != "12240" or size.get(Q + "h") != "15840":
        errors.append("page size is not US Letter portrait")
    expected = {"top": "1440", "right": "1440", "bottom": "1440", "left": "1440"}
    if margins is None:
        errors.append("missing page margins")
    else:
        for key, value in expected.items():
            if margins.get(Q + key) != value:
                errors.append(f"margin {key} != {value}")
    return errors


def run(md_path: Path, docx_path: Path):
    md_text = md_path.read_text(encoding="utf-8")
    document, numbering, docx_text, names, xml_errors = read_docx(docx_path)
    md_result = validate_text(md_text)
    docx_result = validate_text(docx_text)
    table_count, table_errors = validate_tables(document)
    page_errors = validate_page(document)
    numbering_count = len(numbering.findall("./w:abstractNum", NS))
    status = "PASS" if not any([
        md_result["missing"], md_result["forbidden"],
        docx_result["missing"], docx_result["forbidden"],
        xml_errors, table_errors, page_errors, numbering_count < 2,
    ]) else "FAIL"
    return {
        "status": status,
        "markdown": md_result,
        "docx": docx_result,
        "xml_errors": xml_errors,
        "table_count": table_count,
        "table_errors": table_errors,
        "page_errors": page_errors,
        "numbering_abstract_count": numbering_count,
        "docx_zip_entries": len(names),
        "docx_bytes": docx_path.stat().st_size,
        "docx_sha256": hashlib.sha256(docx_path.read_bytes()).hexdigest(),
    }


def negative_control(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    needle = REQUIRED[0]
    mutated = text.replace(needle, "의도적으로 제거된 제품 한 줄", 1)
    result = validate_text(mutated)
    passed = needle in result["missing"]
    return {"status": "PASS" if passed else "FAIL", "detected_missing": result["missing"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("docx", type=Path, nargs="?")
    parser.add_argument("--negative-control", action="store_true")
    args = parser.parse_args()
    if args.negative_control:
        report = negative_control(args.markdown)
    else:
        if args.docx is None:
            parser.error("docx is required unless --negative-control is used")
        report = run(args.markdown, args.docx)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
