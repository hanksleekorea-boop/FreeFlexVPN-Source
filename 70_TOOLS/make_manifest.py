#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MANIFEST.md 생성·왕복 대조. 전 파일 sha256.

    python3 70_TOOLS/make_manifest.py           # 생성
    python3 70_TOOLS/make_manifest.py --check   # 대조
검사 실행 시 재생성되는 파일은 EXCLUDE 로 제외한다 — 목록은 MANIFEST 본문에 적힌다.
"""
import hashlib, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fkvpaths

EXCLUDE_DIRS  = {"__pycache__", ".git", "node_modules", ".test-venv", ".chrome-ci", ".chrome-ci2", ".pytest_cache"}
EXCLUDE_NAMES = {"MANIFEST.md"}
EXCLUDE_GLOBS = ["60_OUTPUTS/checks/**/*", ".project-continuity/LOCK*.json", "*.pyc", "*.log", "*.tmp"]

def files(root):
    out = []
    for f in sorted(root.rglob("*")):
        if not f.is_file(): continue
        rel = f.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if rel.name in EXCLUDE_NAMES: continue
        if any(rel.match(g) for g in EXCLUDE_GLOBS): continue
        out.append(rel)
    return out

def sha(f): return hashlib.sha256(f.read_bytes()).hexdigest()

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
             "", "## 제외 (검사 실행 시 재생성)", ""]
    lines += [f"- `{g}`" for g in EXCLUDE_GLOBS]
    lines += [f"- `{n}` (자기 자신)" for n in sorted(EXCLUDE_NAMES)]
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
