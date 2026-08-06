#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""비밀값·개인정보 스캔. 존재 여부와 '비밀 없는 구성 상태'만 기록한다."""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fkvpaths

PATTERNS = [
    ("AWS 액세스 키",      re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub 토큰",        re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("Slack 토큰",         re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Anthropic 키",       re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI 키",          re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("개인키 블록",        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer 하드코딩",    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{24,}")),
    ("한국 휴대전화",      re.compile(r"(?<![0-9A-Fa-f])01[016789][- ]?\d{3,4}[- ]?\d{4}(?![0-9A-Fa-f])")),
    ("주민등록번호형",     re.compile(r"\b\d{6}[- ]?[1-4]\d{6}\b")),
    ("이메일",             re.compile(r"(?<!\\)\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
]
# 허용 목록 — 이유를 반드시 적는다
ALLOW = [
    (re.compile(r"wireguard-trademark-usage@zx2c4\.com"), "WireGuard 상표 사용 문의처(공개 문서 기재 주소)"),
    (re.compile(r"sales@melbicom\.net"),                  "공급자 견적 문의처(공개 홈페이지 기재)"),
    (re.compile(r"noreply@anthropic\.com"),               "커밋 서명용 공개 주소"),
    (re.compile(r"wg-quick@wg0\.service"),                 "systemd 인스턴스 유닛명이며 이메일이 아님"),
]
TEXT_EXT = {".py", ".js", ".html", ".md", ".json", ".txt", ".yml", ".yaml", ".sh", ".bat"}

def main():
    root = fkvpaths.root()
    hits, allowed = [], 0
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in TEXT_EXT: continue
        if "__pycache__" in f.parts: continue
        try: text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError: continue
        for label, pat in PATTERNS:
            for m in pat.finditer(text):
                s = m.group(0)
                if any(a.search(s) for a, _ in ALLOW):
                    allowed += 1; continue
                line = text[:m.start()].count("\n") + 1
                hits.append((str(f.relative_to(root)), line, label, s[:12] + "…"))
    if hits:
        for p, ln, label, frag in hits[:40]:
            print(f"  {p}:{ln}  [{label}]  {frag}")
        raise SystemExit(f"비밀값·개인정보 스캔 FAIL — 허용 목록 외 {len(hits)}건")
    print(f"비밀값·개인정보 스캔 PASS — 허용 목록 외 항목 0건 (허용 목록 일치 {allowed}건)")
    print("  구성 상태: 이 묶음에는 API 키·토큰·비밀값이 포함되어 있지 않습니다.")

if __name__ == "__main__":
    main()
