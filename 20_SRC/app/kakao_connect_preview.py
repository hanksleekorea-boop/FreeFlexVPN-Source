#!/usr/bin/env python3
"""Render the isolated, local-only Kakao Connect preview."""
from __future__ import annotations

import html

from .kakao_connect_policy import private_preview_model


def render_private_preview() -> str:
    model = private_preview_model()
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in model["warnings"])
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in model["badges"])
    supported = "".join(f"<li>{html.escape(item)}</li>" for item in model["supported"])
    unsupported = "".join(f"<li>{html.escape(item)}</li>" for item in model["unsupported"])
    action = model["primary_action"]
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kakao Connect 비공개 미리보기</title>
<style>
:root{{--bg:#07111d;--card:#102033;--line:#29415a;--text:#f4f8fc;--muted:#b7c4d3;--mint:#5be6ba;--warn:#ffd18a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif}}
main{{width:min(720px,calc(100% - 32px));margin:32px auto}}article{{border:1px solid var(--line);border-radius:24px;background:var(--card);padding:24px}}
.eyebrow{{color:var(--mint);font-weight:800}}h1{{font-size:clamp(1.6rem,5vw,2.4rem);margin:.35rem 0}}p,li{{color:var(--muted)}}
.badges{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}}.badges span{{border:1px solid var(--warn);border-radius:999px;padding:5px 9px;color:var(--text);font-weight:750}}
.warning{{border-left:4px solid var(--warn);padding:2px 14px;margin:22px 0}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
section{{border:1px solid var(--line);border-radius:16px;padding:14px}}button{{width:100%;padding:14px;border:0;border-radius:14px;background:#526171;color:#fff;font-weight:800}}
button:disabled{{cursor:not-allowed;opacity:.72}}@media(max-width:560px){{main{{margin:16px auto}}article{{padding:18px}}.columns{{grid-template-columns:1fr}}}}
</style></head><body><main><article data-profile="{html.escape(model['profile_id'])}" data-release="private">
<div class="eyebrow">{html.escape(model['status'])}</div><h1>{html.escape(model['title'])}</h1><div class="badges" aria-label="후보 상태">{badges}</div><p>{html.escape(model['summary'])}</p>
<div class="warning" role="status" aria-live="polite"><strong>확인되지 않은 기능</strong><ul>{warnings}</ul></div>
<div class="columns"><section><h2>대상 사용</h2><ul>{supported}</ul></section><section><h2>지원하지 않음</h2><ul>{unsupported}</ul></section></div>
<p>이 미리보기는 공개 앱과 연결되지 않은 로컬 검토용입니다.</p>
<button type="button" disabled aria-disabled="true">{html.escape(action['label'])}</button>
</article></main></body></html>"""
