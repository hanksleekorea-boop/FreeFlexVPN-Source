#!/usr/bin/env python3
"""보존된 v1.1 UI를 바탕으로 진실한 상태·순간 중심 v2 후보를 생성한다."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "20_SRC" / "html_templates" / "app_v1_1.html"
TARGET = ROOT / "20_SRC" / "html_templates" / "app_v2.html"
SERVICE_SHELL = ROOT / "20_SRC" / "html_templates" / "service_shell.html"
SERVICE_STYLES = ROOT / "20_SRC" / "html_templates" / "service_shell.css"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one source block, found {text.count(old)}")
    return text.replace(old, new, 1)


def build() -> Path:
    text = SOURCE.read_text(encoding="utf-8")

    # The preserved review UI is selected by query string. Apply that mode
    # before any layout probes run so the legacy viewport is measurable and
    # does not briefly render underneath the customer service shell.
    text = replace_once(
        text,
        "<body>",
        "<body>\n  <script>if(new URLSearchParams(location.search).get('review')==='1')document.body.classList.add('review-mode')</script>",
        "early review mode",
    )

    simple = {
        "FreeFlexVPN 공식 채택 UI · UX v1.1": "FreeFlexVPN 알파 UI · UX v2.5 PC-2·3",
        '<span class="tag"><strong>ADOPTED</strong> UI · UX v1.1</span>': '<span class="tag"><strong>ALPHA CANDIDATE</strong> UI · UX v2.5 · PC DESK · HANDOFF · ALL DEVICES · API READY</span>',
        "필요할 때만 쓰는 VPN의 전체 여정": "필요한 순간에서 시작하는 VPN",
        "왼쪽 화면 이름을 누르거나 앱 안의 버튼을 눌러 흐름을 확인하세요. 모든 결제·연결은 시각 시뮬레이션입니다.": "먼저 지금 필요한 순간을 고르고 보호 상태를 확인합니다. 서버·결제·계정은 아직 연결되지 않은 알파 UI입니다.",
        '<b>홈</b><small>연결·잔액</small>': '<b>홈</b><small>순간·보호 상태</small>',
        '<b>국가 선택</b><small>가까운 서버</small>': '<b>서버 상태</b><small>실제 가동 목록만</small>',
        "실제 VPN·결제·계정 발급 기능 없음": "실제 VPN 서버·결제·계정 기능 없음",
        "FreeFlexVPN · UI Prototype v1.1": "FreeFlexVPN · Alpha UI v2.5 · PC-2·3",
        "홈 · 연결과 잔액": "홈 · 필요한 순간과 보호 상태",
        "앱을 열자마자 남은 데이터와 연결 상태를 동시에 보여줍니다. 라이트 사용자는 복잡한 설정 대신 ‘연결’ 한 번이면 됩니다.": "VPN이 필요한 구체적인 순간을 먼저 고르고, 실제로 확인 가능한 보호 상태만 보여줍니다.",
        '<small>잔액과 연결</small>': '<small>순간과 보호 상태</small>',
        '<small>서버 선택</small>': '<small>가동 서버 없음</small>',
        '<span class="tag">화면 9개</span>': '<span class="tag">화면 14개</span>',
    }
    for old, new in simple.items():
        text = text.replace(old, new)

    css = """
    .moment-title{display:flex;justify-content:space-between;align-items:end;margin:14px 0 8px}.moment-title b{font-size:13px}.moment-title span{color:var(--muted2);font-size:9px}
    .moment-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.moment-card{min-height:74px;border:1px solid var(--line);background:#0c1928;border-radius:15px;padding:11px;text-align:left;cursor:pointer}.moment-card:hover,.moment-card.selected{border-color:var(--mint);background:#102629}.moment-card span{display:block;font-size:17px;margin-bottom:7px}.moment-card b{display:block;font-size:11px}.moment-card small{display:block;color:var(--muted);font-size:8px;line-height:1.35;margin-top:3px}
    .direct-path{width:100%;border:0;background:transparent;color:var(--blue);font-size:10px;font-weight:780;padding:11px 4px;cursor:pointer}
    .privacy-note{color:var(--muted2);font-size:9px;line-height:1.45;margin:7px 1px 0}
    .status-card{display:flex;align-items:center;gap:11px;border:1px solid #31465c;background:#0d1b2b;border-radius:17px;padding:13px;margin-top:10px}.status-dot{width:10px;height:10px;border-radius:50%;background:var(--muted2);flex:none}.status-card.checking .status-dot{background:var(--warning);box-shadow:0 0 10px rgba(255,199,102,.45)}.status-card.protected .status-dot{background:var(--mint);box-shadow:0 0 10px rgba(91,230,186,.45)}.status-card.unverified .status-dot{background:var(--warning);box-shadow:0 0 10px rgba(255,199,102,.32)}.status-card.disconnected .status-dot{background:var(--danger)}.status-card.setup_needed .status-dot{background:var(--warning)}.status-card .grow{flex:1}.status-card b{display:block;font-size:11px}.status-card small{display:block;color:var(--muted);font-size:9px;line-height:1.45;margin-top:3px}
    .state-legend{display:grid;gap:8px;margin-top:16px}.state-row{display:flex;gap:10px;align-items:start;border:1px solid var(--line);background:#0c1928;border-radius:14px;padding:11px}.state-row i{width:8px;height:8px;border-radius:50%;background:var(--muted2);margin-top:3px;flex:none}.state-row[data-state="protected"] i{background:var(--mint)}.state-row[data-state="checking"] i,.state-row[data-state="limited"] i{background:var(--warning)}.state-row[data-state="setup_needed"] i,.state-row[data-state="disconnected"] i{background:var(--danger)}.state-row b{display:block;font-size:10px}.state-row small{display:block;color:var(--muted);font-size:8px;line-height:1.4;margin-top:2px}
    .empty-catalog{text-align:center;border:1px dashed #31465c;background:#0b1725;border-radius:20px;padding:30px 18px;margin-top:18px}.empty-catalog .flag{margin:0 auto 12px}.empty-catalog b{font-size:14px}.empty-catalog p{color:var(--muted);font-size:10px;line-height:1.55;margin:7px 0 0}
    .balance-split.three{gap:8px}.balance-split.three span{flex:1}.balance-split.three span:nth-child(2){text-align:center}.balance-split.three span:last-child{text-align:right}
    .connect-wrap{padding:8px 0 3px}.connect-orb{width:116px;height:116px}.connect-orb::before{inset:10px}.connect-label{bottom:21px}.power{width:36px;height:36px}
    .runtime-server-list{margin-top:14px}.runtime-server-list .flag{font-size:9px;font-weight:900;display:grid;place-items:center}.runtime-config{width:100%;min-height:190px;resize:vertical;border:1px solid var(--line);border-radius:13px;background:#07111e;color:#d7e5f2;padding:12px;font:9px/1.5 ui-monospace,monospace}.runtime-output{width:100%;border:1px solid var(--line);border-radius:12px;background:#07111e;color:var(--mint);padding:10px;font-size:9px}.state-row[data-pass="true"] i{background:var(--mint)}
    .moment-explorer-cta{width:100%;margin-top:9px}.moment-filters{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.moment-filter{display:grid;gap:5px;color:var(--muted);font-size:8px}.moment-filter select,.moment-filter input{width:100%;border:1px solid var(--line);border-radius:11px;background:#091827;color:var(--text);padding:10px 8px;font-size:9px}.tier-filter{display:flex;gap:6px;overflow:auto;margin:10px 0}.tier-chip{white-space:nowrap;border:1px solid var(--line);border-radius:999px;background:#0b1928;color:var(--muted);padding:7px 10px;font-size:8px}.tier-chip.active{border-color:var(--mint);color:var(--mint);background:#102629}.country-policy{border:1px solid var(--line);border-radius:13px;background:#0b1928;padding:10px;font-size:9px;line-height:1.5}.country-policy.caution{border-color:var(--warning)}.country-policy.restricted{border-color:var(--danger)}.moment-summary{display:flex;justify-content:space-between;align-items:center;margin:13px 0 8px;font-size:9px;color:var(--muted)}.moment-recommendations{display:grid;gap:8px}.recommendation-card{border:1px solid var(--line);border-radius:14px;background:#0b1928;padding:11px}.recommendation-card header{display:flex;gap:8px;align-items:start}.recommendation-rank{display:grid;place-items:center;width:25px;height:25px;border-radius:9px;background:#102629;color:var(--mint);font-size:8px;font-weight:900}.recommendation-card h3{font-size:10px;margin:0}.recommendation-card p{color:var(--muted);font-size:8px;line-height:1.45;margin:4px 0 8px}.recommendation-meta{display:flex;flex-wrap:wrap;gap:5px}.recommendation-meta span{border-radius:999px;background:#132237;color:#b8c7d8;padding:4px 7px;font-size:7px}.recommendation-card button{width:100%;margin-top:9px;border:1px solid var(--blue);border-radius:10px;background:transparent;color:var(--blue);padding:8px;font-size:8px;font-weight:800}.recommendation-card button:disabled{border-color:var(--line);color:var(--muted2)}
    .platform-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin:12px 0}.platform-choice{border:1px solid var(--line);border-radius:13px;background:#0b1928;color:var(--text);padding:10px;text-align:left}.platform-choice.active{border-color:var(--mint);background:#102629}.platform-choice span{display:block;font-size:15px}.platform-choice b{display:block;font-size:9px;margin-top:5px}.platform-flow{display:grid;gap:8px}.platform-card{border:1px solid var(--line);border-radius:15px;background:#0b1928;padding:12px}.platform-card .eyebrow{font-size:7px}.platform-card h3{font-size:11px;margin:5px 0}.platform-card p{font-size:8px;line-height:1.5;color:var(--muted);margin:0}.platform-card .secondary{width:100%;margin-top:10px}.platform-badge{display:flex;align-items:center;justify-content:space-between;border:1px solid #31465c;border-radius:13px;background:#0d1b2b;padding:10px;font-size:9px}.platform-badge strong{color:var(--mint)}.platform-matrix{display:grid;gap:6px;margin-top:10px}.platform-status{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--line);padding:7px 1px;font-size:8px}.platform-status:last-child{border-bottom:0}.platform-status span{color:var(--muted)}
    body.app-mode .page{width:min(1500px,calc(100% - 24px));padding:12px 0}body.app-mode .topbar{margin-bottom:12px}body.app-mode .notes,body.app-mode .storyboard{display:none}body.app-mode .workspace{grid-template-columns:270px minmax(0,1fr);gap:12px}body.app-mode .rail{top:12px;max-height:calc(100vh - 90px);border-radius:20px}body.app-mode .stage{min-height:calc(100vh - 82px);padding:16px;border-radius:22px}body.app-mode .phone{width:min(100%,760px);height:calc(100vh - 114px);min-height:680px;max-height:980px;border-radius:28px;padding:7px}body.app-mode .phone::before{display:none}body.app-mode .viewport{border-radius:21px}body.app-mode .screen{padding:38px 34px 94px}body.app-mode .welcome{padding:48px 36px 28px}body.app-mode .bottom-nav{border-radius:0 0 20px 20px}body.app-mode #appModeToggle{border-color:var(--mint);color:var(--mint)}
    @media(max-width:780px){body.app-mode{background:#081321}body.app-mode .page{width:100%;padding:0}body.app-mode .topbar,body.app-mode .rail,body.app-mode .notes,body.app-mode .storyboard{display:none}body.app-mode .workspace{display:block}body.app-mode .stage{min-height:100dvh;padding:0;border:0;border-radius:0;background:#081321}body.app-mode .phone{width:100%;height:100dvh;min-height:0;max-height:none;border:0;border-radius:0;padding:0;box-shadow:none}body.app-mode .viewport{border-radius:0}body.app-mode .screen{padding:46px 20px 90px}body.app-mode .welcome{padding:64px 24px 26px}body.app-mode .bottom-nav{border-radius:0}}
    .pc-home-grid{display:contents}.pc-desk-banner,.pc-stats,.pc-handoff{display:none}
    @media(min-width:1024px){
      body.pc-wide .page{width:min(1760px,calc(100% - 28px));padding:14px 0 32px}
      body.pc-wide .topbar{margin-bottom:14px}
      body.pc-wide .workspace{grid-template-columns:248px minmax(0,1fr);gap:14px}
      body.pc-wide .notes,body.pc-wide .storyboard{display:none}
      body.pc-wide .rail{top:14px;max-height:calc(100vh - 28px);border-radius:20px}
      body.pc-wide .stage{min-height:calc(100vh - 80px);padding:14px;border-radius:24px;place-items:stretch}
      body.pc-wide .phone{width:100%;height:calc(100vh - 108px);min-height:720px;max-height:1080px;border-radius:26px;padding:7px}
      body.pc-wide .phone::before{display:none}
      body.pc-wide .viewport{border-radius:20px}
      body.pc-wide .screen{padding:34px 38px 40px}
      body.pc-wide [data-screen="home"].active{display:block}
      body.pc-wide [data-screen="home"] .app-head{margin-bottom:12px}
      body.pc-wide .pc-desk-banner{display:flex;align-items:center;justify-content:space-between;gap:20px;border:1px solid #2b4b60;border-radius:17px;background:linear-gradient(110deg,rgba(91,230,186,.11),rgba(120,174,252,.08));padding:14px 16px;margin-bottom:12px}
      body.pc-wide .pc-desk-banner b{font-size:14px}body.pc-wide .pc-desk-banner span{color:var(--muted);font-size:10px;line-height:1.5;text-align:right}
      body.pc-wide .pc-home-grid{display:grid;grid-template-columns:minmax(230px,.75fr) minmax(430px,1.25fr);grid-template-areas:"banner banner" "balance moments" "connection moments" "stats stats" "handoff handoff";gap:14px;align-items:start}
      body.pc-wide #runtimeBanner{grid-area:banner;margin:0}
      body.pc-wide .pc-home-grid>.balance-card{grid-area:balance}
      body.pc-wide .pc-moments{grid-area:moments;border:1px solid var(--line);border-radius:20px;background:rgba(11,25,40,.72);padding:15px}
      body.pc-wide .pc-connection{grid-area:connection;border:1px solid var(--line);border-radius:20px;background:rgba(11,25,40,.72);padding:14px}
      body.pc-wide .pc-stats{display:block;grid-area:stats;border:1px solid var(--line);border-radius:20px;background:rgba(11,25,40,.72);padding:16px}
      body.pc-wide .pc-panel-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:12px}body.pc-wide .pc-panel-head h3{font-size:16px;margin:0}body.pc-wide .pc-panel-head span{font-size:9px;color:var(--muted)}
      body.pc-wide .pc-stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.pc-stat{border:1px solid #233b50;border-radius:14px;background:#0d1b2b;padding:12px}.pc-stat span{display:block;color:var(--muted);font-size:9px}.pc-stat strong{display:block;font-size:19px;margin-top:6px}.pc-stat strong small{font-size:10px;color:var(--muted)}
      body.pc-wide .pc-period{display:grid;grid-template-columns:minmax(220px,.8fr) minmax(360px,1.2fr);gap:12px;margin-top:11px}.pc-period-copy{border-left:3px solid var(--warning);padding:10px 12px;background:#171b22;border-radius:0 12px 12px 0}.pc-period-copy b{font-size:11px}.pc-period-copy p{font-size:9px;line-height:1.5;color:var(--muted);margin:5px 0 0}
      body.pc-wide .pc-period-chart{height:90px;display:grid;grid-template-columns:repeat(7,1fr);gap:8px;align-items:end;border-bottom:1px solid #2a4055;padding:8px 10px}.pc-period-bar{display:grid;gap:5px;align-items:end;height:100%}.pc-period-bar i{display:block;height:3px;border-radius:5px;background:#435568}.pc-period-bar span{text-align:center;color:var(--muted2);font-size:8px}
      body.pc-wide .pc-handoff{display:grid;grid-area:handoff;grid-template-columns:112px 1fr;gap:14px;align-items:center;border:1px solid #2b4b60;border-radius:20px;background:linear-gradient(140deg,rgba(91,230,186,.09),rgba(13,25,41,.86));padding:14px}.pc-handoff img{width:112px;height:112px;border-radius:13px;background:#fff;padding:6px}.pc-handoff h3{font-size:14px;margin:0 0 5px}.pc-handoff p{color:var(--muted);font-size:9px;line-height:1.5;margin:0 0 8px}.pc-handoff a{display:inline-flex;color:var(--mint);font-size:10px;font-weight:800;text-decoration:none}
      body.pc-wide .moment-title{margin:0 0 10px}body.pc-wide .moment-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
      body.pc-wide .moment-card{min-height:112px;padding:14px}body.pc-wide .moment-card b{font-size:12px}body.pc-wide .moment-card small{font-size:9px}
      body.pc-wide .moment-explorer-cta{width:calc(50% - 5px);display:inline-flex;align-items:center;justify-content:center;vertical-align:top;min-height:45px;padding:8px}
      body.pc-wide .connect-wrap{padding:2px 0}body.pc-wide .connect-orb{width:132px;height:132px}
      body.pc-wide .quick-grid{grid-template-columns:repeat(2,1fr)}body.pc-wide [data-screen="home"]>.bottom-nav{display:none}
    }
    @media(min-width:1200px){body.pc-wide .pc-home-grid{grid-template-columns:minmax(180px,.7fr) minmax(340px,1.4fr) minmax(190px,.8fr);grid-template-areas:"banner banner banner" "balance moments connection" "stats stats handoff"}}
"""
    text = replace_once(text, "  </style>", css + "  </style>", "v2 styles")
    text = replace_once(
        text,
        '<button class="ghost" type="button" data-go="welcome">처음부터 보기</button>',
        '<button id="appModeToggle" class="ghost" type="button" aria-pressed="false">PC 앱 모드</button><button class="ghost" type="button" data-go="welcome">처음부터 보기</button>',
        "desktop app mode toggle",
    )

    old_home = """              <div class="demo-ribbon"><strong>시각 프로토타입</strong> — 실제 VPN 연결·결제는 발생하지 않으며 새로고침하면 초기화됩니다.</div>
              <div class="balance-card"><div class="balance-top"><div><small>사용 가능한 데이터</small><div class="balance-number"><b id="balanceValue">3.74</b> <span>GB</span></div></div><strong>8월</strong></div><div class="meter"><span id="balanceMeter"></span></div><div class="balance-split"><span>무료 <b>0.74GB</b></span><span>충전 <b id="paidBalance">3.00GB</b> · 무기한</span></div></div>
              <div class="connect-wrap"><button id="connectOrb" class="connect-orb" type="button" aria-label="VPN 연결 전환"><svg class="power" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v10"/><path d="M6.3 5.7a8 8 0 1 0 11.4 0"/></svg><span id="connectLabel" class="connect-label">눌러서 연결</span></button></div>
              <button id="locationCard" class="location-card" type="button" data-go="locations"><span id="homeFlag" class="flag">🇯🇵</span><span class="grow"><b id="homeLocation">일본 · 도쿄</b><small id="connectionDetail">자동 선택 · 예상 42ms</small></span><span class="chev">›</span></button>
              <div class="quick-grid"><button class="quick" type="button" data-go="topup"><span class="q-icon">＋</span><b>용량 충전</b><small>필요한 만큼만</small></button><button class="quick" type="button" data-go="usage"><span class="q-icon">↗</span><b>사용량</b><small>무료분 우선</small></button></div>"""
    new_home = """              <div class="pc-desk-banner" aria-label="PC 책상형 홈"><b>PC 책상형 홈 · PC-2</b><span>Space / Enter 보호 확인 · ← → 화면 이동 · ? 도움말</span></div>
              <div class="pc-home-grid">
              <div class="demo-ribbon"><strong>알파 준비 화면</strong> — 실제 VPN 서버 0대. 연결·결제·계정 생성은 발생하지 않습니다.</div>
              <div class="balance-card" data-demo="wallet"><div class="balance-top"><div><small>정책 적용 시 시작 잔액 예시</small><div class="balance-number"><b id="balanceValue">1.00</b> <span>GB</span></div></div><strong>8월</strong></div><div class="meter"><span id="balanceMeter" style="width:100%"></span></div><div class="balance-split three"><span data-wallet-bucket="free">무료 <b>1.00GB</b></span><span data-wallet-bucket="earned">보상 <b>0.00GB</b></span><span data-wallet-bucket="paid">충전 <b id="paidBalance">0.00GB</b> · 무기한</span></div></div>
              <div class="pc-moments">
              <div class="moment-title"><b>지금 VPN이 필요한 순간</b><span>선택 사항</span></div>
              <div class="moment-grid" role="group" aria-label="VPN 사용 목적"><button class="moment-card" type="button" data-moment="public-wifi"><span>☕</span><b>공용 Wi‑Fi 보호</b><small>카페·공항에서 잠깐</small></button><button class="moment-card" type="button" data-moment="travel"><span>✈</span><b>여행 중 사용</b><small>낯선 네트워크에서</small></button><button class="moment-card" type="button" data-moment="region-web"><span>◎</span><b>다른 국가의 공개 웹</b><small>지역별 공개 정보 확인</small></button><button class="moment-card" type="button" data-moment="connection-help"><span>↻</span><b>연결 문제 해결</b><small>현재 상태부터 확인</small></button></div>
              <p class="privacy-note">목적 선택은 이 화면 안에서만 사용하며 저장하거나 전송하지 않습니다.</p><button class="secondary moment-explorer-cta" type="button" data-go="moments">30개 사용 순간에서 맞춤 추천 찾기</button><button class="secondary moment-explorer-cta" type="button" data-go="platforms">PC·모바일 모든 기기에서 사용하기</button>
              </div>
              <div class="pc-connection">
              <div class="connect-wrap"><button id="connectOrb" class="connect-orb" type="button" aria-label="VPN 보호 상태 확인"><svg class="power" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v10"/><path d="M6.3 5.7a8 8 0 1 0 11.4 0"/></svg><span id="connectLabel" class="connect-label">보호 확인</span></button><button class="direct-path" type="button" data-direct-check>목적 없이 바로 보호 확인</button></div>
              <div id="statusCard" class="status-card unverified" data-connection-state="limited" data-presentation-state="unverified" role="status" aria-live="polite"><span class="status-dot"></span><span class="grow"><b id="homeLocation">보호 상태 확인 불가</b><small id="connectionDetail">이 페이지는 터널·외부 IP·DNS 확인을 아직 받지 못했습니다.</small></span><button class="text-btn" type="button" data-go="locations">자세히</button></div>
              <div class="quick-grid"><button class="quick" type="button" data-go="topup"><span class="q-icon">＋</span><b>용량 충전</b><small>결제 전 UI만</small></button><button class="quick" type="button" data-go="usage"><span class="q-icon">↗</span><b>잔액 구조</b><small>무료·보상·충전</small></button></div>
              </div>
              <section class="pc-stats" aria-label="PC 대형 통계"><div class="pc-panel-head"><h3>넓게 보는 사용 현황</h3><span>로컬 화면 값 · 계정 API 연결 전</span></div><div class="pc-stat-grid"><div class="pc-stat"><span>현재 화면 잔액</span><strong><b id="pcBalanceValue">1.00</b> <small>GB</small></strong></div><div class="pc-stat"><span>실측 가동 서버</span><strong>0 <small>대</small></strong></div><div class="pc-stat"><span>현재 보호 판정</span><strong id="pcProtectionValue">미확인</strong></div></div><div class="pc-period"><div class="pc-period-copy"><b>최근 7일 ↔ 이전 7일</b><p>계정 API와 실제 사용 영수증이 없어 비교값을 만들지 않습니다. 막대는 0 사용량이 아니라 ‘측정 없음’ 기준선입니다.</p></div><div class="pc-period-chart" role="img" aria-label="최근 7일 측정 없음"><span class="pc-period-bar"><i></i><span>월</span></span><span class="pc-period-bar"><i></i><span>화</span></span><span class="pc-period-bar"><i></i><span>수</span></span><span class="pc-period-bar"><i></i><span>목</span></span><span class="pc-period-bar"><i></i><span>금</span></span><span class="pc-period-bar"><i></i><span>토</span></span><span class="pc-period-bar"><i></i><span>일</span></span></div></div></section>
              <aside class="pc-handoff" aria-label="폰으로 이어서 보기"><img src="data:image/png;base64,__APP_QR_B64__" alt="FreeFlexVPN 정본 주소 QR"><div><h3>폰으로 이어서 보기</h3><p>같은 정본 주소를 휴대폰으로 엽니다. 계정 없이도 같은 공개 앱 셸로 이동합니다.</p><a href="https://hanksleekorea-boop.github.io/FreeFlexVPN/app.html" target="_blank" rel="noopener noreferrer">정본 주소 열기 ↗</a></div></aside>
              </div>"""
    text = replace_once(text, old_home, new_home, "home R3/R4")
    text = text.replace('data-go="locations">자세히</button></div>', 'data-go="protection">자세히</button></div>', 1)

    platforms_screen = """
            <section class="screen" data-screen="platforms" aria-label="모든 기기 지원 화면">
              <div class="app-head"><button class="icon-btn" type="button" data-go="home" aria-label="뒤로">‹</button><div><div class="app-brand">모든 기기에서 사용</div><span class="fine">PC · Mac · Linux · Android · iOS</span></div><span style="width:40px"></span></div>
              <div class="demo-ribbon"><strong>역할을 나눕니다</strong> — FreeFlexVPN 웹앱은 계정·잔액·추천·설정을 관리하고, 실제 VPN 터널은 운영체제의 공식 WireGuard 앱이 실행합니다.</div>
              <div class="platform-badge"><span>감지된 기기</span><strong id="platformDetected">확인 중</strong></div>
              <div class="platform-grid" role="group" aria-label="운영체제 선택"><button class="platform-choice" type="button" data-platform="windows"><span>▣</span><b>Windows</b></button><button class="platform-choice" type="button" data-platform="macos"><span>◇</span><b>Mac</b></button><button class="platform-choice" type="button" data-platform="linux"><span>▤</span><b>Linux</b></button><button class="platform-choice" type="button" data-platform="android"><span>▯</span><b>Android</b></button><button class="platform-choice" type="button" data-platform="ios"><span>▭</span><b>iPhone · iPad</b></button></div>
              <div class="platform-flow">
                <article class="platform-card"><div class="eyebrow">1 · 앱처럼 열기</div><h3 id="platformPwaTitle">FreeFlexVPN 웹앱 설치</h3><p id="platformPwaCopy">기기에 맞는 설치 방법을 확인합니다.</p><button id="platformInstallButton" class="secondary" type="button">이 기기에 FreeFlexVPN 설치</button></article>
                <article class="platform-card"><div class="eyebrow">2 · 실제 VPN 사용</div><h3>공식 WireGuard 연결</h3><p id="platformWireguardCopy">공식 앱을 설치한 뒤 이 기기 전용 구성을 가져옵니다.</p><a id="wireguardInstallLink" class="secondary" href="https://www.wireguard.com/install/" target="_blank" rel="noopener noreferrer">공식 WireGuard 설치 페이지</a><button id="platformConfigButton" class="secondary" type="button" data-go="setup">이 기기 구성 준비</button></article>
              </div>
              <div class="platform-matrix" aria-label="지원 범위"><div class="platform-status"><b>웹·PWA 관리 화면</b><span>지금 사용 가능</span></div><div class="platform-status"><b>PC·모바일 앱 아이콘</b><span id="platformInstallState">설치 가능 여부 확인</span></div><div class="platform-status"><b>실제 VPN 터널</b><span id="platformVpnState">서버·로그인 필요</span></div><div class="platform-status"><b>오프라인</b><span>앱 셸만 · 연결 작업은 인터넷 필요</span></div></div>
              <p class="privacy-note">운영체제 감지는 브라우저가 제공하는 기기 정보로 이 화면에서만 수행하며 서버로 전송하지 않습니다.</p>
              <nav class="bottom-nav" aria-label="하단 메뉴"><button class="nav-btn active" type="button" data-go="home">⌂<span>홈</span></button><button class="nav-btn" type="button" data-go="wallet">▤<span>데이터</span></button><button class="nav-btn" type="button" data-go="referral">♡<span>함께</span></button><button class="nav-btn" type="button" data-go="account">○<span>내 정보</span></button></nav>
            </section>

"""
    moments_screen = """
            <section class="screen" data-screen="moments" aria-label="VPN 순간 추천 화면">
              <div class="app-head"><button class="icon-btn" type="button" data-go="home" aria-label="뒤로">‹</button><div><div class="app-brand">상황별 추천</div><span class="fine">30개 순간 · 국가 · 요금 단계</span></div><span style="width:40px"></span></div>
              <div class="demo-ribbon"><strong>추천은 보장이 아닙니다</strong> — 연결 성공·가격·서비스 이용 가능 여부는 실제 서버와 해당 서비스 약관에 따라 달라집니다.</div>
              <div class="moment-filters">
                <label class="moment-filter">현재 있는 국가<select id="currentCountrySelect"><option value="">선택 안 함</option><option value="KR">대한민국</option><option value="JP">일본</option><option value="CN">중국</option><option value="IN">인도</option><option value="AE">아랍에미리트</option><option value="US">미국</option><option value="GB">영국</option><option value="DE">독일</option><option value="SG">싱가포르</option><option value="TH">태국</option><option value="AR">아르헨티나</option><option value="OTHER">기타</option></select></label>
                <label class="moment-filter">목적 국가·본국<select id="destinationCountrySelect"><option value="">먼저 선택</option><option value="KR">대한민국</option><option value="JP">일본</option><option value="US">미국</option><option value="GB">영국</option><option value="DE">독일</option><option value="SG">싱가포르</option><option value="TH">태국</option><option value="IN">인도</option><option value="AR">아르헨티나</option><option value="AE">아랍에미리트</option><option value="CA">캐나다</option><option value="AU">호주</option><option value="FR">프랑스</option><option value="BR">브라질</option></select></label>
                <label class="moment-filter">사용 목적<select id="momentCategorySelect"><option value="all">전체 목적</option><option value="safety">공공망 보호</option><option value="travel_home">여행·본국</option><option value="work">업무</option><option value="research">조사·QA</option><option value="diagnostic">연결 진단</option><option value="performance">성능</option><option value="content">콘텐츠·구독</option><option value="restricted">제한 국가</option></select></label>
                <label class="moment-filter">검색<input id="momentSearchInput" type="search" placeholder="예: 와이파이, 여행"></label>
              </div>
              <div class="tier-filter" aria-label="요금 단계"><button class="tier-chip active" type="button" data-tier-filter="all">전체</button><button class="tier-chip" type="button" data-tier-filter="free">무료</button><button class="tier-chip" type="button" data-tier-filter="paid">유료 충전</button><button class="tier-chip" type="button" data-tier-filter="premium_planned">프리미엄 예정</button><button class="tier-chip" type="button" data-tier-filter="none">비지원</button></div>
              <div id="countryPolicyBanner" class="country-policy">현재 국가를 선택하면 현지 상황에 맞춘 주의사항을 보여줍니다.</div>
              <div class="moment-summary"><b id="momentRecommendationSummary">30개 순간</b><span>목적 정보는 전송하지 않음</span></div>
              <div id="momentRecommendationList" class="moment-recommendations" aria-live="polite"></div>
              <p class="privacy-note">현재 국가·목적 국가·검색어는 이 화면의 메모리에서만 사용하며 계정이나 서버 API로 전송하거나 저장하지 않습니다.</p>
              <nav class="bottom-nav" aria-label="하단 메뉴"><button class="nav-btn active" type="button" data-go="home">⌂<span>홈</span></button><button class="nav-btn" type="button" data-go="wallet">▤<span>데이터</span></button><button class="nav-btn" type="button" data-go="referral">♡<span>함께</span></button><button class="nav-btn" type="button" data-go="account">○<span>내 정보</span></button></nav>
            </section>

"""
    protection_screen = """
            <section class="screen" data-screen="protection" aria-label="보호 상태 화면">
              <div class="app-head"><button class="icon-btn" type="button" data-go="home" aria-label="뒤로">‹</button><b>보호 상태</b><span style="width:40px"></span></div>
              <div class="demo-ribbon"><strong>실측 전용 화면</strong> — 실제 서버가 없어 어떤 항목도 통과로 표시하지 않습니다.</div>
              <div class="status-card unverified"><span class="status-dot"></span><span class="grow"><b>보호 상태 확인 불가</b><small>각 항목의 실제 확인 결과가 아직 충분하지 않습니다.</small></span></div>
              <div class="state-legend" aria-label="보호 확인 항목">
                <div class="state-row" data-check="tunnel"><i></i><div><b>WireGuard 터널</b><small>확인 불가 · 서버 0대</small></div></div>
                <div class="state-row" data-check="exit-ip"><i></i><div><b>출구 IP</b><small>확인 불가 · 터널 없음</small></div></div>
                <div class="state-row" data-check="dns"><i></i><div><b>DNS 보호</b><small>실기기 검증 전 확인 불가</small></div></div>
                <div class="state-row" data-check="ipv6"><i></i><div><b>IPv6 누수 방지</b><small>실기기 검증 전 확인 불가</small></div></div>
                <div class="state-row" data-check="kill-switch"><i></i><div><b>차단 스위치</b><small>실기기 검증 전 확인 불가</small></div></div>
                <div class="state-row" data-check="checked-at"><i></i><div><b>최근 확인 시각</b><small>확인 성공 기록 없음</small></div></div>
              </div>
              <button class="secondary mt16" type="button" data-protection-retry>보호 상태 다시 확인</button><button class="secondary mt16" type="button" data-go="locations">서버 준비 상태 보기</button>
              <nav class="bottom-nav" aria-label="하단 메뉴"><button class="nav-btn active" type="button" data-go="home">⌂<span>홈</span></button><button class="nav-btn" type="button" data-go="wallet">▤<span>데이터</span></button><button class="nav-btn" type="button" data-go="referral">♡<span>함께</span></button><button class="nav-btn" type="button" data-go="account">○<span>내 정보</span></button></nav>
            </section>

"""
    text = replace_once(
        text,
        '            <section class="screen" data-screen="locations" aria-label="국가 선택 화면">',
        moments_screen + platforms_screen + protection_screen + '            <section class="screen" data-screen="locations" aria-label="국가 선택 화면">',
        "moments platforms and protection screens",
    )

    old_locations = """              <div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>국가 또는 도시 검색</div>
              <div class="region-label">추천</div><div class="server-list">
                <button class="server selected" type="button" data-location="일본 · 도쿄" data-flag="🇯🇵" data-ping="42"><span class="flag">🇯🇵</span><span class="grow"><b>일본 · 도쿄</b><small>가장 빠른 서버</small></span><span class="ping">42ms</span><span class="radio"></span></button>
                <button class="server" type="button" data-location="싱가포르" data-flag="🇸🇬" data-ping="58"><span class="flag">🇸🇬</span><span class="grow"><b>싱가포르</b><small>안정적인 연결</small></span><span class="ping">58ms</span><span class="radio"></span></button>
              </div>
              <div class="region-label">아시아</div><div class="server-list">
                <button class="server" type="button" data-location="대한민국 · 서울" data-flag="🇰🇷" data-ping="64"><span class="flag">🇰🇷</span><span class="grow"><b>대한민국 · 서울</b><small>표준 서버</small></span><span class="ping">64ms</span><span class="radio"></span></button>
                <button class="server" type="button" data-location="홍콩" data-flag="🇭🇰" data-ping="71"><span class="flag">🇭🇰</span><span class="grow"><b>홍콩</b><small>표준 서버</small></span><span class="ping">71ms</span><span class="radio"></span></button>
                <button class="server" type="button" data-location="미국 · 로스앤젤레스" data-flag="🇺🇸" data-ping="146"><span class="flag">🇺🇸</span><span class="grow"><b>미국 · 로스앤젤레스</b><small>장거리 연결</small></span><span class="ping">146ms</span><span class="radio"></span></button>
              </div>
              <p class="fine mt16">표시 지연시간은 화면 구성을 위한 예시이며 실제 측정값이 아닙니다.</p>"""
    new_locations = """              <div class="empty-catalog" data-catalog-source="runtime" data-server-count="0"><span class="flag">∅</span><b>현재 가동 서버가 없습니다</b><p>서버가 준비되면 실제 상태 확인을 통과한 국가와 도시만 이곳에 표시합니다. 예시 위치나 예상 지연시간은 보여주지 않습니다.</p></div>
              <div class="region-label">보호 상태 기준</div><div class="state-legend" aria-label="연결 상태 5종">
                <div class="state-row" data-state="setup_needed"><i></i><div><b>설정 필요</b><small>기기 설정을 먼저 완료해야 합니다.</small></div></div>
                <div class="state-row" data-state="checking"><i></i><div><b>보호 확인 중</b><small>터널과 공개 IP를 확인하는 중입니다.</small></div></div>
                <div class="state-row" data-state="protected"><i></i><div><b>VPN 보호 확인됨</b><small>실제 터널과 외부 확인이 모두 성공한 경우만 표시합니다.</small></div></div>
                <div class="state-row" data-state="limited"><i></i><div><b>보호 상태 확인 불가</b><small>연결 신호만으로는 보호를 확인할 수 없습니다.</small></div></div>
                <div class="state-row" data-state="disconnected"><i></i><div><b>현재 VPN 보호 안 됨</b><small>보호 연결이 없거나 서버가 준비되지 않았습니다.</small></div></div>
              </div>"""
    text = replace_once(text, old_locations, new_locations, "empty server catalog")

    old_amounts = '<div class="amounts"><button class="amount selected" type="button" data-gb="3" data-price="1500"><b>3GB</b><span>맛보기</span><em>1,500원</em></button><button class="amount" type="button" data-gb="10" data-price="3900"><b>10GB</b><span>라이트</span><em>3,900원</em></button><button class="amount" type="button" data-gb="30" data-price="8900"><b>30GB</b><span>스탠다드</span><em>8,900원</em></button><button class="amount" type="button" data-gb="100" data-price="19900"><b>100GB</b><span>빅</span><em>19,900원</em></button><button class="amount" type="button" data-gb="300" data-price="39900" style="grid-column:1/-1"><b>300GB</b><span>벌크</span><em>39,900원</em></button></div>'
    new_amounts = '<div class="amounts"><button class="amount selected" type="button" data-gb="3" data-price="1500"><b>3GB</b><span>가끔 필요한 순간</span><em>1,500원</em></button><button class="amount" type="button" data-gb="10" data-price="3900"><b>10GB</b><span>여행·라이트 사용</span><em>3,900원</em></button><button id="morePack" class="amount" type="button" data-gb="30" data-price="8900" hidden><b>30GB</b><span>더 필요한 경우</span><em>8,900원</em></button></div><button id="showMorePack" class="text-btn mt8" type="button">30GB 옵션 더 보기</button><p class="fine">100GB·300GB는 라이트 사용자 파일럿 수요 확인 전 기본 판매에서 숨깁니다.</p>'
    text = replace_once(text, old_amounts, new_amounts, "light-user price packs")

    wallet_and_referral = """
            <section class="screen" data-screen="wallet" aria-label="데이터 지갑 화면">
              <div class="app-head"><div><div class="app-brand">데이터 지갑</div><span class="fine">무료 → 보상 → 충전 순서</span></div><button class="icon-btn" type="button" data-go="usage" aria-label="사용 기록">↗</button></div>
              <div class="demo-ribbon"><strong>UI 예시</strong> — 로컬 원장 엔진은 검사됐지만 이 공개 화면은 아직 계정 API와 동기화되지 않았습니다.</div>
              <div class="usage-hero"><small>정책 적용 시 시작 잔액 예시</small><div class="big">1.00 <span>GB</span></div></div>
              <div class="region-label">잔액 3종</div>
              <div class="usage-row" data-wallet-view="free"><span class="usage-dot"></span><span class="grow"><b>무료 데이터</b><small>매월 1GB · 해당 월 말까지</small></span><strong>1.00GB</strong></div>
              <div class="usage-row" data-wallet-view="earned"><span class="usage-dot" style="background:var(--violet)"></span><span class="grow"><b>함께 받은 데이터</b><small>추천 보상 · 무기한</small></span><strong>0.00GB</strong></div>
              <div class="usage-row" data-wallet-view="paid"><span class="usage-dot paid"></span><span class="grow"><b>충전 데이터</b><small>일회성 구매 · 무기한</small></span><strong>0.00GB</strong></div>
              <div class="empty-catalog mt16"><span class="flag">↗</span><b>아직 세션 영수증이 없습니다</b><p>실제 터널 사용량이 확정되면 사용 전·후 잔액과 차감 순서를 기록합니다.</p></div>
              <button class="secondary mt16" type="button" data-go="topup">용량 충전 설계 보기</button>
              <nav class="bottom-nav" aria-label="하단 메뉴"><button class="nav-btn" type="button" data-go="home">⌂<span>홈</span></button><button class="nav-btn active" type="button" data-go="wallet">▤<span>데이터</span></button><button class="nav-btn" type="button" data-go="referral">♡<span>함께</span></button><button class="nav-btn" type="button" data-go="account">○<span>내 정보</span></button></nav>
            </section>

            <section class="screen" data-screen="referral" aria-label="친구와 나누기 화면">
              <div class="app-head"><div><div class="app-brand">친구와 나누기</div><span class="fine">양쪽에 500MB</span></div><button class="icon-btn" type="button" data-go="account" aria-label="내 정보">○</button></div>
              <div class="demo-ribbon"><strong>보상 엔진 검증 완료</strong> — 공개 계정 API가 없어 링크·QR 발급과 실제 보상은 아직 비활성입니다.</div>
              <div class="balance-card"><div class="eyebrow">친구와 함께 받기</div><div class="balance-number">500 <span>MB씩</span></div><p class="sub">친구가 첫 실제 보호에 성공하고 누적 100MB를 사용하면 양쪽에 무기한 데이터를 지급합니다.</p></div>
              <div class="region-label">진행 기준</div><div class="state-legend" data-referral-rail>
                <div class="state-row"><i></i><div><b>1. 링크로 신규 가입</b><small>연락처 업로드 없이 공유</small></div></div>
                <div class="state-row"><i></i><div><b>2. 첫 실제 보호 확인</b><small>시뮬레이션 연결은 제외</small></div></div>
                <div class="state-row"><i></i><div><b>3. 누적 100MB 사용</b><small>중복 사용량 사건은 한 번만 계산</small></div></div>
                <div class="state-row"><i></i><div><b>4. 양쪽 500MB 지급</b><small>추천인 월 5건 확정 상한</small></div></div>
              </div>
              <button class="primary mt16" type="button" disabled>계정 API 연결 후 공유 링크 만들기</button>
              <p class="fine" style="text-align:center">가짜 추천 코드나 공유 성공을 만들지 않습니다.</p>
              <nav class="bottom-nav" aria-label="하단 메뉴"><button class="nav-btn" type="button" data-go="home">⌂<span>홈</span></button><button class="nav-btn" type="button" data-go="wallet">▤<span>데이터</span></button><button class="nav-btn active" type="button" data-go="referral">♡<span>함께</span></button><button class="nav-btn" type="button" data-go="account">○<span>내 정보</span></button></nav>
            </section>

"""
    text = replace_once(
        text,
        '            <section class="screen" data-screen="devices" aria-label="기기 관리 화면">',
        wallet_and_referral + '            <section class="screen" data-screen="devices" aria-label="기기 관리 화면">',
        "wallet and referral screens",
    )

    text = replace_once(
        text,
        '<div class="device-count"><div><span>사용 중</span><strong>2 / 2</strong></div><span>활성 기기 한도</span></div>\n              <article class="device"><div class="device-top"><span class="device-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M10 18h4"/></svg></span><span class="grow"><b>내 iPhone</b><small>현재 연결 · 일본 도쿄</small></span><span class="online"></span></div><div class="device-actions"><button class="mini" type="button" data-toast="기기 이름 변경은 프로토타입입니다.">이름 변경</button><button class="mini warn" type="button" data-toast="실제 폐기 요청은 전송되지 않았습니다.">연결 폐기</button></div></article>\n              <article class="device"><div class="device-top"><span class="device-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/></svg></span><span class="grow"><b>여행용 노트북</b><small>3일 전 사용 · 싱가포르</small></span></div><div class="device-actions"><button class="mini" type="button" data-toast="기기 이름 변경은 프로토타입입니다.">이름 변경</button><button class="mini warn" type="button" data-toast="실제 폐기 요청은 전송되지 않았습니다.">연결 폐기</button></div></article>\n              <div class="limit-note">새 기기를 추가하려면 기존 기기 하나를 먼저 폐기해야 합니다. 같은 WireGuard 키를 여러 기기에 복사하면 물리 기기 수를 구분할 수 없습니다.</div>\n              <button class="primary mt16" type="button" disabled>새 기기 추가 · 한도 도달</button>',
        '<div class="device-count"><div><span>등록됨</span><strong>0 / 2</strong></div><span>활성 기기 한도</span></div>\n              <div class="empty-catalog"><span class="flag">▯</span><b>등록된 기기가 없습니다</b><p>실제 계정과 WireGuard 서버가 준비된 뒤, 이 기기에서 생성한 공개키만 등록합니다.</p></div>\n              <div class="limit-note">같은 WireGuard 키를 여러 기기에 복사하면 물리 기기 수를 구분할 수 없습니다. 개인키는 기기 밖으로 전송하지 않습니다.</div>\n              <button class="primary mt16" type="button" disabled>서버 준비 후 기기 추가</button>',
        "truthful device state",
    )

    text = text.replace('<div class="big">0.26 <span>GB</span></div>', '<div class="big">0.00 <span>GB</span></div>')
    text = text.replace('그래프 수치는 화면 구성을 위한 예시입니다.', '실사용 데이터가 없어 모든 값은 0입니다.')
    text = text.replace('<strong>0.74GB</strong>', '<strong>1.00GB</strong>', 1)
    text = text.replace('<div class="usage-row"><span class="usage-dot paid"></span><span class="grow"><b>충전 데이터</b><small>유효기간 없음</small></span><strong id="usagePaid">3.00GB</strong></div>', '<div class="usage-row"><span class="usage-dot" style="background:var(--violet)"></span><span class="grow"><b>보상 데이터</b><small>추천 보상 · 유효기간 없음</small></span><strong id="usageEarned">0.00GB</strong></div><div class="usage-row"><span class="usage-dot paid"></span><span class="grow"><b>충전 데이터</b><small>유효기간 없음</small></span><strong id="usagePaid">0.00GB</strong></div>')
    text = text.replace('현재 충전 잔액</small><strong id="topupCurrent">3.00GB', '현재 충전 잔액</small><strong id="topupCurrent">0.00GB')

    text = text.replace(
        "home:['홈 · 연결과 잔액','앱을 열자마자 남은 데이터와 연결 상태를 동시에 보여줍니다. 라이트 사용자는 복잡한 설정 대신 ‘연결’ 한 번이면 됩니다.'],",
        "home:['홈 · 순간과 보호 상태','공용 Wi‑Fi·여행·지역 공개 웹·연결 문제 중 필요한 순간을 선택하고, 확인된 보호 상태만 표시합니다.'],",
    )
    text = text.replace(
        "locations:['국가 선택 · 속도 우선','가장 빠른 서버를 먼저 제안하고 지연시간이 예시임을 밝혀 미측정 수치를 실제값처럼 보이지 않게 합니다.'],",
        "locations:['서버 상태 · 빈 카탈로그','실제 서버가 0대인 동안 예시 국가와 지연시간을 만들지 않습니다. 다섯 상태의 의미를 같은 화면에서 확인할 수 있습니다.'],",
    )
    text = text.replace(
        "      locations:['서버 상태 · 빈 카탈로그'",
        "      moments:['상황별 추천 · 30개 순간','현재 국가와 목적에 따라 목적 국가·무료·유료·프리미엄 예정 단계를 추천하며 비지원 목적은 연결하지 않습니다.'],\n      platforms:['모든 기기 · 역할 분리','Windows·Mac·Linux·Android·iOS에서 PWA 관리 화면과 공식 WireGuard 터널의 역할을 나눠 안내합니다.'],\n      protection:['보호 상태 · 실측 전용','터널·출구 IP·DNS·최근 확인 시각을 분리하고, 서버와 실기기 증거가 없으면 확인 불가로 유지합니다.'],\n      locations:['서버 상태 · 빈 카탈로그'",
    )
    text = text.replace(
        "      topup:['충전 · 구독 없는 결제'",
        "      wallet:['데이터 지갑 · 세 잔액','무료·추천·구매 잔액과 차감 순서, 세션 영수증의 동기화 경계를 보여줍니다.'],\n      referral:['친구와 나누기 · 양쪽 보상','실제 보호와 100MB 이후 양쪽 500MB를 지급하며 공개 API 전에는 공유를 비활성으로 둡니다.'],\n      topup:['충전 · 구독 없는 결제'",
    )

    # 14화면 탐색: 기존 9화면 정본은 보존하고 v2.2 내비게이션만 확장한다.
    rail_home = '<button class="screen-link active" type="button" data-go="home"><span class="screen-no">04</span><span><b>홈</b><small>순간·보호 상태</small></span><span class="arrow">›</span></button>'
    rail_extra = rail_home + '\n          <button class="screen-link" type="button" data-go="moments"><span class="screen-no">05</span><span><b>상황별 추천</b><small>30개 순간·국가</small></span><span class="arrow">›</span></button>\n          <button class="screen-link" type="button" data-go="platforms"><span class="screen-no">06</span><span><b>모든 기기</b><small>PC·모바일·PWA</small></span><span class="arrow">›</span></button>\n          <button class="screen-link" type="button" data-go="protection"><span class="screen-no">07</span><span><b>보호 상태</b><small>실측 전용</small></span><span class="arrow">›</span></button>'
    text = replace_once(text, rail_home, rail_extra, "rail protection")
    text = text.replace('data-go="locations"><span class="screen-no">05</span>', 'data-go="locations"><span class="screen-no">08</span>', 1)
    rail_topup = '<button class="screen-link" type="button" data-go="topup"><span class="screen-no">06</span><span><b>용량 충전</b><small>자동결제 없음</small></span><span class="arrow">›</span></button>'
    rail_wallet = '<button class="screen-link" type="button" data-go="wallet"><span class="screen-no">09</span><span><b>데이터 지갑</b><small>3잔액·영수증</small></span><span class="arrow">›</span></button>\n          <button class="screen-link" type="button" data-go="topup"><span class="screen-no">10</span><span><b>용량 충전</b><small>자동결제 없음</small></span><span class="arrow">›</span></button>\n          <button class="screen-link" type="button" data-go="referral"><span class="screen-no">11</span><span><b>친구와 나누기</b><small>양쪽 500MB</small></span><span class="arrow">›</span></button>'
    text = replace_once(text, rail_topup, rail_wallet, "rail wallet referral")
    text = text.replace('data-go="devices"><span class="screen-no">07</span>', 'data-go="devices"><span class="screen-no">12</span>', 1)
    text = text.replace('data-go="usage"><span class="screen-no">08</span>', 'data-go="usage"><span class="screen-no">13</span>', 1)
    text = text.replace('data-go="account"><span class="screen-no">09</span>', 'data-go="account"><span class="screen-no">14</span>', 1)

    thumb_home = '<button class="thumb" type="button" data-go="home"><span>04</span><b>홈</b><small>순간과 보호 상태</small></button>'
    text = replace_once(text, thumb_home, thumb_home + '<button class="thumb" type="button" data-go="moments"><span>05</span><b>추천</b><small>30개 순간·국가</small></button><button class="thumb" type="button" data-go="platforms"><span>06</span><b>기기</b><small>PC·모바일·PWA</small></button><button class="thumb" type="button" data-go="protection"><span>07</span><b>보호</b><small>실측 상태 기준</small></button>', "thumb moments platforms protection")
    text = text.replace('data-go="locations"><span>05</span>', 'data-go="locations"><span>08</span>', 1)
    thumb_topup = '<button class="thumb" type="button" data-go="topup"><span>06</span><b>충전</b><small>일회성 결제</small></button>'
    text = replace_once(text, thumb_topup, '<button class="thumb" type="button" data-go="wallet"><span>09</span><b>지갑</b><small>무료·보상·충전</small></button><button class="thumb" type="button" data-go="topup"><span>10</span><b>충전</b><small>일회성 결제</small></button><button class="thumb" type="button" data-go="referral"><span>11</span><b>함께</b><small>양쪽 500MB</small></button>', "thumb wallet referral")
    text = text.replace('data-go="devices"><span>07</span>', 'data-go="devices"><span>12</span>', 1)
    text = text.replace('data-go="usage"><span>08</span>', 'data-go="usage"><span>13</span>', 1)
    text = text.replace('data-go="account"><span>09</span>', 'data-go="account"><span>14</span>', 1)
    text = text.replace('grid-template-columns:repeat(9,minmax(110px,1fr))', 'grid-template-columns:repeat(14,minmax(110px,1fr))')

    old_js = """    const orb=document.getElementById('connectOrb'),label=document.getElementById('connectLabel'),detail=document.getElementById('connectionDetail');
    orb.addEventListener('click',()=>{const on=orb.classList.toggle('connected');label.textContent=on?'연결됨 · 00:01':'눌러서 연결';detail.textContent=on?'보호 중 · 예시 IP 198.51.100.24':'자동 선택 · 예상 42ms';toast(on?'VPN 연결 상태를 시뮬레이션했습니다.':'VPN 연결 해제를 시뮬레이션했습니다.')});
    document.querySelectorAll('.server').forEach(server=>server.addEventListener('click',()=>{document.querySelectorAll('.server').forEach(s=>s.classList.remove('selected'));server.classList.add('selected');document.getElementById('homeLocation').textContent=server.dataset.location;document.getElementById('homeFlag').textContent=server.dataset.flag;const connected=orb.classList.contains('connected');document.getElementById('connectionDetail').textContent=connected?'보호 중 · 예시 IP 198.51.100.24':`자동 선택 · 예상 ${server.dataset.ping}ms`;toast(`${server.dataset.location}을(를) 선택했습니다.`);setTimeout(()=>go('home'),430)}));
    let selectedGb=3,selectedPrice=1500,paid=3;"""
    new_js = """    const orb=document.getElementById('connectOrb'),label=document.getElementById('connectLabel'),detail=document.getElementById('connectionDetail'),statusCard=document.getElementById('statusCard'),statusTitle=document.getElementById('homeLocation');
    const connectionStates={
      setup_needed:{title:'설정 필요',detail:'기기 설정을 먼저 완료해야 합니다.',presentation:'unverified'},
      checking:{title:'보호 확인 중',detail:'터널과 공개 IP를 확인하고 있습니다.',presentation:'checking'},
      protected:{title:'VPN 보호 확인됨',detail:'실제 터널과 외부 확인이 모두 성공했습니다.',presentation:'protected'},
      limited:{title:'보호 상태 확인 불가',detail:'연결 신호만으로는 보호를 확인할 수 없습니다. 터널·외부 IP·DNS 확인이 필요합니다.',presentation:'unverified'},
      disconnected:{title:'현재 VPN 보호 안 됨',detail:'가동 서버가 없어 연결할 수 없습니다.',presentation:'disconnected'}
    };
    function setConnectionState(state){const engineState=connectionStates[state]?state:'limited',copy=connectionStates[engineState];statusCard.dataset.connectionState=engineState;statusCard.dataset.presentationState=copy.presentation;statusCard.className=`status-card ${copy.presentation}`;statusTitle.textContent=copy.title;detail.textContent=copy.detail;label.textContent=engineState==='checking'?'확인 중…':'보호 확인';orb.disabled=engineState==='checking'}
    window.setConnectionState=setConnectionState;
    function checkProtection(){setConnectionState('checking');toast('실제 연결 가능 여부를 확인합니다.');if(document.documentElement.dataset.apiMode==='live'){window.dispatchEvent(new CustomEvent('freeflex:check-protection'));return}setTimeout(()=>{setConnectionState('limited');toast('가동 서버가 없어 보호 연결을 시작하지 않았습니다.')},650)}
    orb.addEventListener('click',checkProtection);
    document.querySelector('[data-direct-check]').addEventListener('click',checkProtection);
    document.querySelectorAll('[data-protection-retry]').forEach(button=>button.addEventListener('click',checkProtection));
    document.querySelectorAll('[data-moment]').forEach(card=>card.addEventListener('click',()=>{document.querySelectorAll('[data-moment]').forEach(item=>item.classList.toggle('selected',item===card));toast(`${card.querySelector('b').textContent} 목적을 이 화면에만 적용했습니다.`)}));
    let selectedGb=3,selectedPrice=1500,paid=0;"""
    text = replace_once(text, old_js, new_js, "truthful connection state")
    text = text.replace(
        "    let selectedGb=3,selectedPrice=1500,paid=0;",
        "    let selectedGb=3,selectedPrice=1500,paid=0;\n    document.getElementById('showMorePack').addEventListener('click',event=>{document.getElementById('morePack').hidden=false;event.currentTarget.hidden=true;toast('30GB 옵션을 펼쳤습니다. 실제 결제는 없습니다.')});",
    )

    text = text.replace(
        "document.getElementById('balanceValue').textContent=(paid+.74).toFixed(2)",
        "document.getElementById('balanceValue').textContent=(paid+1).toFixed(2)",
    )
    text = text.replace(
        "VPN 연결 상태를 시뮬레이션했습니다.",
        "VPN 연결 상태를 확인했습니다.",
    )
    text = text.replace(
        "const targets=[...document.querySelectorAll('[data-screen=\"home\"] .quick[data-go]')];",
        "const targets=[...document.querySelectorAll('[data-screen=\"home\"] .moment-card[data-moment], [data-screen=\"home\"] .quick[data-go]')];",
    )
    text = text.replace("targets.length===2", "targets.length===6")
    text = replace_once(
        text,
        "    document.addEventListener('click',e=>{const target=e.target.closest('[data-go]');if(target)go(target.dataset.go)});",
        """    const appModeToggle=document.getElementById('appModeToggle');
    let appModeMemory=false;
    const readAppMode=()=>{try{return localStorage.getItem('ffvpn-app-mode')==='1'}catch{return appModeMemory}};
    const writeAppMode=value=>{appModeMemory=value;try{localStorage.setItem('ffvpn-app-mode',value?'1':'0')}catch{}};
    function setAppMode(value,{persist=true}={}){const on=Boolean(value);document.body.classList.toggle('app-mode',on);document.documentElement.dataset.appMode=on?'on':'off';appModeToggle.setAttribute('aria-pressed',String(on));appModeToggle.textContent=on?'설계 보기':'PC 앱 모드';if(persist)writeAppMode(on)}
    const appModeRequested=new URLSearchParams(location.search).get('view')==='app'||matchMedia('(display-mode: standalone)').matches||navigator.standalone===true||readAppMode();
    setAppMode(appModeRequested,{persist:false});
    appModeToggle.addEventListener('click',()=>setAppMode(!document.body.classList.contains('app-mode')));
    document.addEventListener('click',e=>{const target=e.target.closest('[data-go]');if(target)go(target.dataset.go)});""",
        "desktop app mode behavior",
    )
    text = replace_once(
        text,
        "    appModeToggle.addEventListener('click',()=>setAppMode(!document.body.classList.contains('app-mode')));",
        """    appModeToggle.addEventListener('click',()=>setAppMode(!document.body.classList.contains('app-mode')));
    const pcWideMedia=matchMedia('(min-width:1024px)');
    function syncPcWide(){const on=pcWideMedia.matches;document.body.classList.toggle('pc-wide',on);document.documentElement.dataset.pcLayout=on?'wide':'mobile'}
    syncPcWide();pcWideMedia.addEventListener?.('change',syncPcWide);""",
        "PC responsive mode",
    )
    text = replace_once(
        text,
        "    document.querySelector('[data-direct-check]').addEventListener('click',checkProtection);",
        """    document.querySelector('[data-direct-check]').addEventListener('click',checkProtection);
    window.addEventListener('keydown',event=>{
      if(!pcWideMedia.matches||event.defaultPrevented||event.repeat||event.altKey||event.ctrlKey||event.metaKey)return;
      const target=event.target instanceof Element?event.target:null;
      if(target?.closest('input,textarea,select,button,a,[contenteditable="true"]'))return;
      if(event.key==='?'){event.preventDefault();toast('단축키: Space / Enter 보호 확인 · ← → 화면 이동 · ? 도움말');return}
      const activeIndex=screens.findIndex(screen=>screen.classList.contains('active'));
      if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
        event.preventDefault();const delta=event.key==='ArrowRight'?1:-1;go(screens[(activeIndex+delta+screens.length)%screens.length].dataset.screen);return
      }
      if((event.key===' '||event.key==='Enter')&&screens[activeIndex]?.dataset.screen==='home'){event.preventDefault();checkProtection()}
    });""",
        "PC keyboard controls",
    )
    text = replace_once(
        text,
        "    window.setConnectionState=setConnectionState;",
        """    window.setConnectionState=setConnectionState;
    const pcBalanceValue=document.getElementById('pcBalanceValue'),pcProtectionValue=document.getElementById('pcProtectionValue');
    function syncPcSummary(){if(pcBalanceValue)pcBalanceValue.textContent=document.getElementById('balanceValue').textContent;if(pcProtectionValue)pcProtectionValue.textContent=document.getElementById('homeLocation').textContent}
    const pcSummaryObserver=new MutationObserver(syncPcSummary);pcSummaryObserver.observe(document.getElementById('balanceValue'),{childList:true,subtree:true,characterData:true});pcSummaryObserver.observe(document.getElementById('homeLocation'),{childList:true,subtree:true,characterData:true});syncPcSummary();""",
        "PC summary synchronization",
    )

    text = replace_once(
        text,
        '  <meta name="theme-color" content="#07101d">',
        '  <meta name="theme-color" content="#07101d">\n  <meta name="referrer" content="no-referrer">\n  <meta name="freeflex-api-base" content="">',
        "runtime API meta",
    )
    text = replace_once(
        text,
        '<div class="demo-ribbon"><strong>알파 준비 화면</strong> — 실제 VPN 서버 0대. 연결·결제·계정 생성은 발생하지 않습니다.</div>',
        '<div id="runtimeBanner" class="demo-ribbon"><strong>알파 준비 화면</strong> — 실제 VPN 서버 0대. 연결·결제·계정 생성은 발생하지 않습니다.</div>',
        "runtime home banner",
    )
    text = replace_once(
        text,
        '<div class="demo-ribbon mt16"><strong>프로토타입 안내</strong> — 실제 수령 링크나 개인키는 생성하지 않습니다.</div>\n              <button class="primary" type="button" data-go="home">설정 흐름 확인 완료</button>',
        '<div id="setupRuntimeBanner" class="demo-ribbon mt16"><strong>서버 연결 전</strong> — 실제 수령 링크가 없으면 개인키나 구성을 만들지 않습니다.</div>\n              <button id="createProfileButton" class="primary" type="button" disabled>서버 선택 후 이 기기 구성 만들기</button>\n              <div id="profilePanel" class="stack mt16" hidden><label class="fine" for="profileConfig">이 기기 전용 WireGuard 구성</label><textarea id="profileConfig" class="runtime-config" readonly spellcheck="false"></textarea><button id="downloadProfileButton" class="secondary" type="button">.conf 파일로 이 기기에 저장</button><p class="fine">개인키가 포함된 파일입니다. 다른 사람에게 보내거나 클라우드에 올리지 마세요.</p></div>',
        "runtime setup controls",
    )
    text = replace_once(
        text,
        '<div class="empty-catalog" data-catalog-source="runtime" data-server-count="0"><span class="flag">∅</span><b>현재 가동 서버가 없습니다</b><p>서버가 준비되면 실제 상태 확인을 통과한 국가와 도시만 이곳에 표시합니다. 예시 위치나 예상 지연시간은 보여주지 않습니다.</p></div>',
        '<div id="serverCatalog" class="empty-catalog" data-catalog-source="runtime" data-server-count="0"><span class="flag">∅</span><b>현재 가동 서버가 없습니다</b><p>서버가 준비되면 실제 상태 확인을 통과한 국가와 도시만 이곳에 표시합니다. 예시 위치나 예상 지연시간은 보여주지 않습니다.</p></div>',
        "runtime server catalog",
    )
    text = replace_once(text, '<div class="demo-ribbon"><strong>UI 예시</strong> — 로컬 원장 엔진은 검사됐지만 이 공개 화면은 아직 계정 API와 동기화되지 않았습니다.</div>', '<div id="walletRuntimeBanner" class="demo-ribbon"><strong>UI 예시</strong> — 로컬 원장 엔진은 검사됐지만 이 공개 화면은 아직 계정 API와 동기화되지 않았습니다.</div>', "wallet runtime banner")
    text = replace_once(text, '<div class="usage-hero"><small>정책 적용 시 시작 잔액 예시</small><div class="big">1.00 <span>GB</span></div></div>', '<div class="usage-hero"><small>현재 사용 가능한 데이터</small><div class="big"><span id="walletTotalValue">1.00</span> <span>GB</span></div></div>', "wallet runtime total")
    text = replace_once(text, '<button class="primary mt16" type="button" disabled>계정 API 연결 후 공유 링크 만들기</button>', '<button id="shareReferralButton" class="primary mt16" type="button" disabled>친구와 500MB씩 받는 링크 만들기</button><input id="shareReferralOutput" class="runtime-output mt8" type="text" readonly hidden aria-label="추천 공유 링크">', "referral runtime control")
    text = replace_once(text, '<div class="device-count"><div><span>등록됨</span><strong>0 / 2</strong></div><span>활성 기기 한도</span></div>', '<div class="device-count"><div><span>등록됨</span><strong id="deviceCountValue">0 / 2</strong></div><span>활성 기기 한도</span></div>', "device runtime count")
    text = replace_once(text, '<div class="empty-catalog"><span class="flag">▯</span><b>등록된 기기가 없습니다</b><p>실제 계정과 WireGuard 서버가 준비된 뒤, 이 기기에서 생성한 공개키만 등록합니다.</p></div>', '<div id="deviceList" class="empty-catalog"><span class="flag">▯</span><b>등록된 기기가 없습니다</b><p>실제 계정과 WireGuard 서버가 준비된 뒤, 이 기기에서 생성한 공개키만 등록합니다.</p></div>', "device runtime list")
    text = replace_once(text, '<button class="primary mt16" type="button" disabled>서버 준비 후 기기 추가</button>', '<button id="addDeviceButton" class="primary mt16" type="button" disabled>새 기기 구성 만들기</button>', "device runtime add")
    text = replace_once(
        text,
        "      const show=()=>{if(!standalone&&!dismissedRecently())banner.hidden=false};",
        "      const show=()=>{if(!standalone&&!dismissedRecently())banner.hidden=false};\n      globalThis.freeflexShowInstallHelp=show;globalThis.freeflexIsStandalone=standalone;",
        "public PWA install help bridge",
    )
    text = replace_once(
        text,
        "      installButton.addEventListener('click',async()=>{if(!deferredPrompt)return;await deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;installButton.hidden=true;hide()});",
        "      globalThis.freeflexRequestInstall=async()=>{if(!deferredPrompt){show();return false}await deferredPrompt.prompt();const choice=await deferredPrompt.userChoice;deferredPrompt=null;installButton.hidden=true;hide();return choice.outcome==='accepted'};\n      installButton.addEventListener('click',globalThis.freeflexRequestInstall);",
        "public PWA install request bridge",
    )
    text = replace_once(text, '  </script>\n</body>', '  </script>\n  <script type="module" src="./pwa_runtime.js"></script>\n</body>', "PWA runtime module")
    text = replace_once(
        text,
        '  <script type="module" src="./pwa_runtime.js"></script>',
        """  <script>
    if(new URLSearchParams(location.search).has('app_layout_probe'))requestAnimationFrame(()=>{
      const phone=document.querySelector('.phone')?.getBoundingClientRect(),stage=document.querySelector('.stage')?.getBoundingClientRect();
      const mobile=innerWidth<781;
      const safe=document.body.classList.contains('app-mode')&&phone&&stage&&(mobile?Math.abs(phone.width-innerWidth)<3&&Math.abs(phone.height-innerHeight)<3:phone.width>=520&&phone.height>=650&&stage.width>phone.width);
      document.documentElement.dataset.appLayoutSafe=safe?'pass':'fail';
    });
  </script>
  <script type="module" src="./pwa_runtime.js"></script>""",
        "desktop app layout probe",
    )

    service_styles = SERVICE_STYLES.read_text(encoding="utf-8")
    service_shell = SERVICE_SHELL.read_text(encoding="utf-8")
    if "data-service-shell" in text:
        raise RuntimeError("서비스 화면은 생성 과정에서 정확히 한 번만 추가해야 합니다")
    text = replace_once(
        text,
        "</head>",
        f'<style data-freeflex-service-theme>\n{service_styles}\n</style>\n</head>',
        "service UI styles",
    )
    text = replace_once(
        text,
        "</body>",
        f"{service_shell}\n</body>",
        "service UI shell",
    )
    service_copy = {
        "FreeFlexVPN 알파 UI · UX v2.5 PC-2·3": "FreeFlexVPN 서비스",
        "ALPHA CANDIDATE": "INTERNAL REVIEW",
        "알파 준비 화면": "서비스 자료 확인 전",
        "서버·결제·계정은 아직 연결되지 않은 알파 UI입니다.": "고객용 서비스 화면의 상세 기능을 내부에서 확인합니다.",
        "FreeFlexVPN · Alpha UI v2.5 · PC-2·3": "FreeFlexVPN · 내부 검토 화면",
    }
    for old, new in service_copy.items():
        text = text.replace(old, new)

    forbidden = ("일본 · 도쿄", "대한민국 · 서울", "예상 42ms", "198.51.100.24", "연결됨 · 00:01")
    remaining = [token for token in forbidden if token in text]
    if remaining:
        raise RuntimeError(f"v2에 금지된 가짜 런타임 데이터가 남음: {remaining}")

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    return TARGET


if __name__ == "__main__":
    path = build()
    print(f"generated {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")
