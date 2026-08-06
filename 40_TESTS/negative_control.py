#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""음성 대조 — 일부러 틀린 입력을 넣어 각 검사가 '실제로 실패하는지' 확인한다.

통과만 확인한 검사는 '무엇이든 통과시키는 검사'일 수 있다.
여기서 실패하지 않는 검사는 검사 개수에 세면 안 된다.

    python3 40_TESTS/negative_control.py
"""
import base64, json, os, re, shutil, subprocess, sys, tempfile, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "70_TOOLS"))
import fkvpaths

SRC = fkvpaths.root()
RESULTS = []
ONLY = os.environ.get("FKV_NC_ONLY", "").strip()

def sandbox():
    d = pathlib.Path(tempfile.mkdtemp(prefix="fkv_nc_"))
    dst = d / "proj"
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("__pycache__", "*.zip"))
    return dst

def run(root, *args):
    env = dict(os.environ, FKV_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1",
               PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, *args], cwd=root, env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return p.returncode, (p.stdout + p.stderr)

def case(name, mutate, cmd, expect_fail=True):
    if ONLY and not name.startswith(ONLY):
        return
    root = sandbox()
    try:
        mutate(root)
        rc, out = run(root, *cmd)
        failed = rc != 0
        ok = failed if expect_fail else not failed
        RESULTS.append((name, ok, f"rc={rc} " + out.strip().splitlines()[-1][:90] if out.strip() else f"rc={rc}"))
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)

# NC1 계약 원장 수치 1개 변조 → 왕복 검사가 실패해야 한다
def m1(r):
    p = r / "10_STATE" / "CONTRACTS.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["dist20"]["safe_krw"] += 1
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
case("NC1 계약 원장 1원 변조 → 계약 검사 FAIL", m1, ["40_TESTS/test_contracts.py"])

# NC2 모델 상수 변조 → 문서 수치 불일치가 드러나야 한다
def m2(r):
    p = r / "20_SRC" / "cost_model.py"
    p.write_text(p.read_text(encoding="utf-8").replace('"usd": 1470.0', '"usd": 1480.0'), encoding="utf-8")
case("NC2 환율 상수 변조 → 계약 검사 FAIL", m2, ["40_TESTS/test_contracts.py"])

# NC3 배포 HTML 에 런타임 에러 주입 → 실렌더 검사가 잡아야 한다
def m3(r):
    f = sorted((r / "30_DEPLOY").glob("*.html"))[0]
    f.write_text(f.read_text(encoding="utf-8").replace("</body>",
                 "<script>window.__nc__.boom()</script></body>"), encoding="utf-8")
case("NC3 런타임 에러 주입 → 실렌더 검사 FAIL", m3, ["40_TESTS/render_check.py"])

# NC4 아이콘 크기 위조(192 → 64) → IHDR 실측 검사가 잡아야 한다
def m4(r):
    f = sorted((r / "30_DEPLOY").glob("*.html"))[0]
    t = f.read_text(encoding="utf-8")
    m = re.search(r'<link rel="manifest" href="data:application/manifest\+json;base64,([^"]+)"', t)
    mf = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    for ic in mf["icons"]:
        if ic["sizes"] == "192x192":
            raw = bytearray(base64.b64decode(ic["src"].split("base64,")[1]))
            raw[16:24] = (64).to_bytes(4, "big") + (64).to_bytes(4, "big")   # IHDR 위조
            ic["src"] = "data:image/png;base64," + base64.b64encode(bytes(raw)).decode()
    nb = base64.b64encode(json.dumps(mf, ensure_ascii=False, separators=(",", ":")).encode()).decode()
    f.write_text(t[:m.start(1)] + nb + t[m.end(1):], encoding="utf-8")
case("NC4 아이콘 IHDR 위조 → 실렌더 검사 FAIL", m4, ["40_TESTS/render_check.py"])

# NC5 파일 1바이트 변조 → MANIFEST 왕복 대조가 잡아야 한다
def m5(r):
    (r / "20_SRC" / "cost_model.py").write_bytes(
        (r / "20_SRC" / "cost_model.py").read_bytes() + b"\n# nc\n")
case("NC5 파일 1바이트 추가 → MANIFEST 대조 FAIL", m5,
     ["70_TOOLS/make_manifest.py", "--check"])

# NC5b 중첩 검사 산출물 제외 규칙을 약화 → MANIFEST 대조가 추가 파일을 잡아야 한다
def m5b(r):
    p = r / "70_TOOLS" / "make_manifest.py"
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace('"60_OUTPUTS/checks/**/*"', '"60_OUTPUTS/checks/*"'),
                 encoding="utf-8")
case("NC5b 중첩 검사 산출물 제외 약화 → MANIFEST 대조 FAIL", m5b,
     ["70_TOOLS/make_manifest.py", "--check"])

# NC6 비밀값 삽입 → 스캔이 잡아야 한다
def m6(r):
    (r / "20_SRC" / "nc_leak.py").write_text(
        'TOKEN = "sk-ant-' + "A" * 40 + '"\n', encoding="utf-8")
case("NC6 가짜 API 키 삽입 → 비밀값 스캔 FAIL", m6, ["70_TOOLS/scan_secrets.py"])

# NC7 표식 폴더 제거 → 경로 해석이 조용히 넘어가지 않고 즉시 죽어야 한다
def m7(r):
    shutil.rmtree(r / "10_STATE")
case("NC7 표식 폴더 삭제 → 경로 해석 즉시 종료", m7, ["70_TOOLS/fkvpaths.py"])

# NC8 충전분 차감 방향 변조 → 쿼터 원장 검사가 실제로 실패해야 한다
def m8(r):
    p = r / "20_SRC" / "app" / "quota_ledger.py"
    t = p.read_text(encoding="utf-8")
    before = 'candidate["paid_bytes"] = int(candidate["paid_bytes"]) - from_paid'
    after = 'candidate["paid_bytes"] = int(candidate["paid_bytes"]) + from_paid'
    if before not in t:
        raise RuntimeError("NC8 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, after, 1), encoding="utf-8")
case("NC8 충전분 차감 방향 변조 → 쿼터 원장 검사 FAIL", m8,
     ["40_TESTS/test_quota_ledger.py"])

# NC9 Pages 배포 권한 약화 → 공개 묶음 검사가 실패해야 한다
def m9(r):
    p = r / "20_SRC" / "github_pages" / "pages.yml"
    t = p.read_text(encoding="utf-8")
    before = "pages: write"
    if before not in t:
        raise RuntimeError("NC9 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "pages: read", 1), encoding="utf-8")
case("NC9 Pages 배포 권한 약화 → GitHub Pages 검사 FAIL", m9,
     ["40_TESTS/test_github_pages.py"])

# NC10 공개 HTTP 반복 횟수 약화 → GitHub Pages 검사가 실패해야 한다
def m10(r):
    p = r / "20_SRC" / "github_pages" / "pages.yml"
    t = p.read_text(encoding="utf-8")
    before = "for probe in 1 2 3"
    if before not in t:
        raise RuntimeError("NC10 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "for probe in 1", 1), encoding="utf-8")
case("NC10 공개 HTTP 반복 횟수 약화 → GitHub Pages 검사 FAIL", m10,
     ["40_TESTS/test_github_pages.py"])

# NC11 QR 바이트 손상 → 공개 QR 검사가 실패해야 한다
def m11(r):
    targets = list((r / "60_OUTPUTS").glob("FreeFlexVPN_PUBLIC_QR_*.png"))
    if len(targets) != 1:
        raise RuntimeError(f"NC11 QR 대상을 하나로 고정하지 못했습니다: {len(targets)}")
    targets[0].write_bytes(b"not-a-png")
case("NC11 QR 바이트 손상 → 공개 QR 검사 FAIL", m11,
     ["40_TESTS/test_public_qr.py"])

# NC12 관리자 SSH를 전 세계에 개방 → cloud-init 검사가 실패해야 한다
def m12(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = "ip saddr {spec.admin_ssh_cidr} tcp dport {spec.ssh_port} ct state new accept"
    after = "ip saddr 0.0.0.0/0 tcp dport {spec.ssh_port} ct state new accept"
    if before not in t:
        raise RuntimeError("NC12 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, after, 1), encoding="utf-8")
case("NC12 SSH 전면 개방 → cloud-init 검사 FAIL", m12,
     ["40_TESTS/test_cloud_init.py"])

# NC13 nftables 기본 차단을 허용으로 약화 → cloud-init 검사가 실패해야 한다
def m13(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    if t.count("policy drop;") < 2:
        raise RuntimeError("NC13 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace("policy drop;", "policy accept;", 2), encoding="utf-8")
case("NC13 방화벽 기본 차단 약화 → cloud-init 검사 FAIL", m13,
     ["40_TESTS/test_cloud_init.py"])

# NC14 WireGuard 개인키 파일 로드를 평문 필드로 변경 → cloud-init 검사가 실패해야 한다
def m14(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = '"PostUp = wg set %i private-key /etc/wireguard/%i.key\\n"'
    after = '"PrivateKey = intentionally-invalid-inline-value\\n"'
    if before not in t:
        raise RuntimeError("NC14 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, after, 1), encoding="utf-8")
case("NC14 평문 WireGuard 키 필드 → cloud-init 검사 FAIL", m14,
     ["40_TESTS/test_cloud_init.py"])

# NC15 쿼터 차단 세트를 허용 규칙으로 변조 → cloud-init 검사가 실패해야 한다
def m15(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = "ip saddr @quota_blocked_v4 drop"
    if before not in t:
        raise RuntimeError("NC15 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "ip saddr @quota_blocked_v4 accept", 1), encoding="utf-8")
case("NC15 쿼터 차단 규칙 허용으로 변조 → cloud-init 검사 FAIL", m15,
     ["40_TESTS/test_cloud_init.py"])

# NC16 WireGuard 누적 카운터 차분을 덧셈으로 변조 → 쿼터 에이전트 검사가 실패해야 한다
def m16(r):
    p = r / "20_SRC" / "infra" / "quota_agent.py"
    t = p.read_text(encoding="utf-8")
    before = "delta = current_total - previous if current_total >= previous else current_total"
    after = "delta = current_total + previous if current_total >= previous else current_total"
    if before not in t:
        raise RuntimeError("NC16 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, after, 1), encoding="utf-8")
case("NC16 누적 카운터 차분 방향 변조 → 쿼터 에이전트 검사 FAIL", m16,
     ["40_TESTS/test_quota_agent.py"])

# NC17 개인키 묶음의 프로젝트 내부 출력 금지를 제거 → 피어 묶음 검사가 실패해야 한다
def m17(r):
    p = r / "20_SRC" / "infra" / "peer_bundle.py"
    t = p.read_text(encoding="utf-8")
    before = 'raise ValueError("개인키 묶음은 프로젝트·Git 저장소 내부에 만들 수 없습니다")'
    if before not in t:
        raise RuntimeError("NC17 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "return resolved", 1), encoding="utf-8")
case("NC17 프로젝트 내부 개인키 출력 허용 → 피어 묶음 검사 FAIL", m17,
     ["40_TESTS/test_peer_bundle.py"])

# NC18 IPv6 터널 경로를 제거 → 피어 묶음 검사가 실패해야 한다
def m18(r):
    p = r / "20_SRC" / "infra" / "peer_bundle.py"
    t = p.read_text(encoding="utf-8")
    before = '"AllowedIPs = 0.0.0.0/0, ::/0\\n"'
    if before not in t:
        raise RuntimeError("NC18 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, '"AllowedIPs = 0.0.0.0/0\\n"', 1), encoding="utf-8")
case("NC18 IPv6 터널 경로 제거 → 피어 묶음 검사 FAIL", m18,
     ["40_TESTS/test_peer_bundle.py"])

# NC19 폐기 상태를 무시하고 모든 피어를 복원 → 쿼터 에이전트 검사가 실패해야 한다
def m19(r):
    p = r / "20_SRC" / "infra" / "quota_agent.py"
    t = p.read_text(encoding="utf-8")
    before = 'if peer["enrolled"] and peer.get("block_reason") != "revoked"'
    if before not in t:
        raise RuntimeError("NC19 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "if True", 1), encoding="utf-8")
case("NC19 폐기 피어 재부팅 복원 → 쿼터 에이전트 검사 FAIL", m19,
     ["40_TESTS/test_quota_agent.py"])

# NC20 일회용 수령권 원문을 상태 키로 저장 → Telegram 검사가 실패해야 한다
def m20(r):
    p = r / "20_SRC" / "app" / "telegram_onboarding.py"
    t = p.read_text(encoding="utf-8")
    before = 'state["claims"][digest] = {'
    if before not in t:
        raise RuntimeError("NC20 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, 'state["claims"][token] = {', 1), encoding="utf-8")
case("NC20 수령권 원문 저장 → Telegram 온보딩 검사 FAIL", m20,
     ["40_TESTS/test_telegram_onboarding.py"])

# NC21 동의 확인을 우회 → Telegram 검사가 실패해야 한다
def m21(r):
    p = r / "20_SRC" / "app" / "telegram_onboarding.py"
    t = p.read_text(encoding="utf-8")
    before = 'if not user or not user.get("consent"):'
    if before not in t:
        raise RuntimeError("NC21 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "if False:", 1), encoding="utf-8")
case("NC21 동의 확인 우회 → Telegram 온보딩 검사 FAIL", m21,
     ["40_TESTS/test_telegram_onboarding.py"])

# NC22 사용된 수령권을 다시 사용 가능하게 유지 → Telegram 검사가 실패해야 한다
def m22(r):
    p = r / "20_SRC" / "app" / "telegram_onboarding.py"
    t = p.read_text(encoding="utf-8")
    before = 'claim["used"] = True'
    if before not in t:
        raise RuntimeError("NC22 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, 'claim["used"] = False', 1), encoding="utf-8")
case("NC22 수령권 재사용 허용 → Telegram 온보딩 검사 FAIL", m22,
     ["40_TESTS/test_telegram_onboarding.py"])

# NC23 원문 Telegram ID를 가명 대신 저장 → Telegram 검사가 실패해야 한다
def m23(r):
    p = r / "20_SRC" / "app" / "telegram_onboarding.py"
    t = p.read_text(encoding="utf-8")
    before = 'return hmac.new(self.identity_secret, str(telegram_user_id).encode("ascii"), hashlib.sha256).hexdigest()'
    if before not in t:
        raise RuntimeError("NC23 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, 'return str(telegram_user_id)', 1), encoding="utf-8")
case("NC23 원문 Telegram ID 저장 → Telegram 온보딩 검사 FAIL", m23,
     ["40_TESTS/test_telegram_onboarding.py"])

# NC24 Telegram으로 클라이언트 개인키 전송 허용 → Telegram 검사가 실패해야 한다
def m24(r):
    p = r / "20_SRC" / "infra" / "telegram_bot_config.py"
    t = p.read_text(encoding="utf-8")
    before = '"private_key_delivery": "forbidden_in_telegram"'
    if before not in t:
        raise RuntimeError("NC24 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, '"private_key_delivery": "allowed"', 1), encoding="utf-8")
case("NC24 Telegram 개인키 전송 허용 → Telegram 온보딩 검사 FAIL", m24,
     ["40_TESTS/test_telegram_onboarding.py"])

# NC25 SMTP/25 전달 차단 삭제 → 남용 방지 검사가 실패해야 한다
def m25(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = '    iifname "wg0" tcp dport 25 counter reject with tcp reset\n'
    if before not in t:
        raise RuntimeError("NC25 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "", 1), encoding="utf-8")
case("NC25 SMTP 25 차단 삭제 → 남용 방지 검사 FAIL", m25,
     ["40_TESTS/test_abuse_controls.py"])

# NC26 계정당 활성 기기 한도를 3대로 완화 → 남용 방지 검사가 실패해야 한다
def m26(r):
    p = r / "20_SRC" / "infra" / "quota_agent.py"
    t = p.read_text(encoding="utf-8")
    before = "MAX_ACTIVE_PEERS_PER_ACCOUNT = 2"
    if before not in t:
        raise RuntimeError("NC26 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "MAX_ACTIVE_PEERS_PER_ACCOUNT = 3", 1), encoding="utf-8")
case("NC26 활성 기기 3대 허용 → 남용 방지 검사 FAIL", m26,
     ["40_TESTS/test_abuse_controls.py"])

# NC27 fail2ban 건강검사 삭제 → 남용 방지 검사가 실패해야 한다
def m27(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = "probe fail2ban systemctl is-active --quiet fail2ban\n"
    if before not in t:
        raise RuntimeError("NC27 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "", 1), encoding="utf-8")
case("NC27 fail2ban 건강검사 삭제 → 남용 방지 검사 FAIL", m27,
     ["40_TESTS/test_abuse_controls.py"])

# NC28 포트 휴리스틱을 P2P 완전 차단으로 과장 → 남용 방지 검사가 실패해야 한다
def m28(r):
    p = r / "20_SRC" / "infra" / "cloud_init.py"
    t = p.read_text(encoding="utf-8")
    before = "완전 차단을 주장하지 않는다"
    if before not in t:
        raise RuntimeError("NC28 변조 지점을 찾지 못했습니다")
    p.write_text(t.replace(before, "모든 P2P를 완전 차단한다", 1), encoding="utf-8")
case("NC28 P2P 완전 차단 과장 → 남용 방지 검사 FAIL", m28,
     ["40_TESTS/test_abuse_controls.py"])

# NC0 대조군: 변조 없음 → 전부 통과해야 한다 (검사가 무조건 실패하지는 않는지)
case("NC0 대조군(무변조) → 계약 검사 PASS", lambda r: None,
     ["40_TESTS/test_contracts.py"], expect_fail=False)

n = len(RESULTS)
bad = [r for r in RESULTS if not r[1]]
for name, ok, detail in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'} {name}  · {detail}")
if bad:
    raise SystemExit(f"음성 대조 {n-len(bad)}/{n} — {len(bad)}건이 기대대로 동작하지 않음")
print(f"음성 대조 {n}/{n} 통과 — 모든 검사가 틀린 입력에서 실제로 실패함")
