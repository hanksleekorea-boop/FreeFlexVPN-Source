#!/usr/bin/env python3
"""원가 모델에서 계약 원장을 재생성한다."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

import cost_model


target = ROOT / "10_STATE" / "CONTRACTS.json"
target.write_text(
    json.dumps(cost_model.contracts(), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(target.relative_to(ROOT))
