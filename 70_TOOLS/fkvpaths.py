#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""경로 해석 단일 창구. 후보 경로를 열거하고 하나도 없으면 즉시 죽는다.

정리·재배치 중 검사가 '조용히 건너뛰는' 사고를 막기 위해 존재한다.
    python3 70_TOOLS/fkvpaths.py     # 자체 확인 (의존성 0)
"""
import os, sys, pathlib

MARKERS = ("10_STATE", "20_SRC", "40_TESTS", "70_TOOLS")

def root() -> pathlib.Path:
    cands = []
    env = os.environ.get("FKV_ROOT")
    if env: cands.append(pathlib.Path(env))
    here = pathlib.Path(__file__).resolve()
    cands += [here.parent.parent, here.parent, pathlib.Path.cwd(), pathlib.Path.cwd().parent]
    for c in cands:
        try:
            if all((c / m).is_dir() for m in MARKERS):
                return c.resolve()
        except OSError:
            continue
    sys.stderr.write(
        "FATAL: 프로젝트 루트를 찾지 못했습니다.\n"
        f"  찾은 표식: {MARKERS}\n"
        f"  시도한 경로: {[str(c) for c in cands]}\n"
        "  FKV_ROOT 환경변수로 루트를 지정하거나 zip 최상위에서 실행하십시오.\n")
    raise SystemExit(2)

def p(*parts) -> pathlib.Path:
    q = root().joinpath(*parts)
    if not q.exists():
        raise SystemExit(f"FATAL: 필수 경로 없음 → {q}")
    return q

def deliverables():
    return sorted((root() / "30_DEPLOY").glob("*.html"))

def documents():
    return sorted((root() / "60_OUTPUTS").glob("*.docx"))

if __name__ == "__main__":
    r = root()
    print(f"루트 확인 PASS — {r}")
    for m in MARKERS: print(f"  {m}/ 존재")
    print(f"  30_DEPLOY 산출물 {len(deliverables())}개")
    print(f"  60_OUTPUTS 문서 {len(documents())}개")
