#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MANIFEST.md 생성·왕복 대조. 전 파일 sha256.

    python3 70_TOOLS/make_manifest.py           # 생성
    python3 70_TOOLS/make_manifest.py --check   # 대조
검사 실행 시 재생성되는 파일은 EXCLUDE 로 제외한다 — 목록은 MANIFEST 본문에 적힌다.
텍스트 파일은 Windows·macOS·Linux의 줄바꿈 차이를 무시한 지문값을 쓴다.
"""
import hashlib, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fkvpaths

EXCLUDE_DIRS  = {"__pycache__", ".git", "node_modules", ".test-venv", ".chrome-ci", ".chrome-ci2", ".pytest_cache"}
EXCLUDE_NAMES = {"MANIFEST.md"}
EXCLUDE_GLOBS = [
    "60_OUTPUTS/checks/*",
    "60_OUTPUTS/checks/**/*",
    "60_OUTPUTS/AI_HANDOFF_CURRENT/*",
    "60_OUTPUTS/AI_HANDOFF_CURRENT/**/*",
    ".project-continuity/LOCK*.json",
    "*.pyc",
    "*.log",
    "*.tmp",
]
TEXT_SUFFIXES = {".css", ".html", ".ini", ".js", ".json", ".md", ".ps1", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
TEXT_NAMES = {".gitattributes", ".gitignore", "AGENTS.md", "LICENSE", "README"}
MOVE_HISTORY = (
    ("00_START/HANDOFF_V2_2026-08-01.md", "90_ARCHIVE/00_START_legacy/HANDOFF_V2_2026-08-01.md", 2352, "이전 시작 안내"),
    ("00_START/README.md", "90_ARCHIVE/00_START_legacy/README.md", 5242, "이전 시작 안내"),
    ("10_STATE/APP_SERVICE_PLAN_v2.0_2026-08-01.md", "90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v2.0_2026-08-01.md", 24251, "과거 제품 기획"),
    ("10_STATE/APP_SERVICE_PLAN_v3.0_2026-08-05.md", "90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v3.0_2026-08-05.md", 8313, "과거 제품 기획"),
    ("10_STATE/APP_SERVICE_PLAN_v4.0_2026-08-06.md", "90_ARCHIVE/10_STATE_plans/APP_SERVICE_PLAN_v4.0_2026-08-06.md", 8941, "과거 제품 기획"),
    ("10_STATE/DEV_EXECUTION_PLAN_v2.0_2026-08-01.md", "90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v2.0_2026-08-01.md", 26975, "과거 상세 실행계획"),
    ("10_STATE/DEV_EXECUTION_PLAN_v3.0_2026-08-05.md", "90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v3.0_2026-08-05.md", 11921, "과거 상세 실행계획"),
    ("10_STATE/DEV_EXECUTION_PLAN_v4.0_2026-08-06.md", "90_ARCHIVE/10_STATE_plans/DEV_EXECUTION_PLAN_v4.0_2026-08-06.md", 15009, "과거 상세 실행계획"),
)

def files(root):
    out = []
    for f in sorted(root.rglob("*")):
        if not f.is_file(): continue
        rel = f.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if rel.parts[:2] == (".project-continuity", "local"): continue
        if rel.name in EXCLUDE_NAMES: continue
        if any(rel.match(g) for g in EXCLUDE_GLOBS): continue
        out.append(rel)
    return out

def sha(f):
    """Hash text after CRLF-to-LF normalization; hash binary files byte-for-byte."""
    data = f.read_bytes()
    if f.suffix.lower() in TEXT_SUFFIXES or f.name in TEXT_NAMES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()

def purpose(rel):
    """Return a short, stable human-facing purpose for the project inventory."""
    first = rel.parts[0] if rel.parts else ""
    labels = {
        "00_START": "시작·인수인계",
        "10_STATE": "상태·근거·기록",
        "10_PLAN": "현재 기획·실행 정본",
        "20_SRC": "현행 소스",
        "30_DEPLOY": "공개용 결과물",
        "40_TESTS": "검사",
        "60_OUTPUTS": "생성 결과·참고 산출물",
        "70_TOOLS": "생성·검증 도구",
        ".project-continuity": "공동개발 연속성 기록",
    }
    if str(rel) == ".gitignore": return "버전 관리 제외 규칙"
    if str(rel) == "AGENTS.md": return "프로젝트 작업 규칙"
    return labels.get(first, "분류 확인 필요")

def build(root):
    rows = [(str(r).replace("\\", "/"), sha(root / r), (root / r).stat().st_size) for r in files(root)]
    total = sum(s for _, _, s in rows)
    lines = ["# MANIFEST — FreeFlexVPN 이관 묶음", "",
             f"| 항목 | 값 |", "|---|---|",
             f"| 파일 수 | {len(rows)} |",
             f"| 총 바이트 | {total:,} |",
             "", "## 지문 규칙", "",
             "- 텍스트 파일은 줄바꿈(CRLF/LF)을 LF로 맞춘 뒤 SHA-256을 계산한다. 따라서 Windows·macOS·Linux 복제본도 같은 내용이면 같은 지문값이다.",
             "- 이미지·압축 파일 등 이진 파일은 원래 바이트 그대로 SHA-256을 계산한다.",
             "", "## 제외 (검사 실행 시 재생성)", ""]
    lines += [f"- `{g}`" for g in EXCLUDE_GLOBS]
    lines += ["- `.project-continuity/local/**` (기기별 인계 원장)"]
    lines += [f"- `{n}` (자기 자신)" for n in sorted(EXCLUDE_NAMES)]
    lines += ["", "## 대청소 이동 기록", "", "| 원래 위치 | 새 위치 | 바이트 | 용도 |", "|---|---|---:|---|"]
    lines += [f"| `{old}` | `{new}` | {size:,} | {label} |" for old, new, size, label in MOVE_HISTORY]
    lines += ["", "## 파일별 목록", "", "| 파일 | 바이트 | 용도 | sha256 |", "|---|---:|---|---|"]
    lines += [f"| `{p}` | {s:,} | {purpose(pathlib.Path(p))} | `{h}` |" for p, h, s in rows]
    return "\n".join(lines) + "\n", rows

def parse(text):
    d = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln.startswith("| `") or "sha256" in ln: continue
        parts = [c.strip() for c in ln.strip("|").split("|")]
        if len(parts) not in {3, 4}: continue
        path = parts[0].strip().strip("`").strip()
        h = parts[-1].strip().strip("`").strip()
        if len(h) == 64:
            d[path] = h
    return d

def main():
    root = fkvpaths.root()
    mpath = root / "MANIFEST.md"
    if "--check" in sys.argv:
        if not mpath.exists(): raise SystemExit("FAIL: MANIFEST.md 없음")
        want = parse(mpath.read_text(encoding="utf-8"))
        have = {str(r).replace("\\", "/"): sha(root / r) for r in files(root)}
        missing = sorted(set(want) - set(have))
        extra   = sorted(set(have) - set(want))
        diff    = sorted(p for p in set(want) & set(have) if want[p] != have[p])
        if missing or extra or diff:
            for p in missing: print(f"  없음:   {p}")
            for p in extra:   print(f"  추가:   {p}")
            for p in diff:    print(f"  불일치: {p}")
            raise SystemExit(f"MANIFEST 왕복 대조 FAIL — 없음 {len(missing)} · 추가 {len(extra)} · 불일치 {len(diff)}")
        print(f"MANIFEST 왕복 대조 PASS — 파일 {len(want)}개 해시 전부 일치")
        return
    text, rows = build(root)
    mpath.write_text(text, encoding="utf-8")
    print(f"MANIFEST 생성 — 파일 {len(rows)}개 · {sum(s for _,_,s in rows):,} bytes")

if __name__ == "__main__":
    main()
