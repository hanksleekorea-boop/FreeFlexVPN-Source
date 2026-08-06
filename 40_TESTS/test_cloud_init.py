#!/usr/bin/env python3
"""출구 노드 cloud-init의 구조·보안·재생성 계약을 검사한다."""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_SRC"))

from infra.cloud_init import (
    EXAMPLE_ADMIN_CIDR,
    GOOGLE_IAP_TCP_FORWARDING_CIDR,
    ExitNodeSpec,
    build_config,
    parse_rendered,
    render_cloud_config,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))


spec = ExitNodeSpec(EXAMPLE_ADMIN_CIDR, example=True)
text = render_cloud_config(spec)
config = parse_rendered(text)
files = {item["path"]: item for item in config["write_files"]}
nft = files["/etc/nftables.conf"]["content"]
wg = files["/etc/wireguard/wg0.conf"]["content"]
bootstrap = files["/usr/local/sbin/freeflexvpn-bootstrap"]["content"]
health = files["/usr/local/sbin/freeflexvpn-health"]["content"]
ssh = files["/etc/ssh/sshd_config.d/99-freeflexvpn.conf"]["content"]

check("I1 cloud-config 헤더·JSON/YAML 부분집합 왕복", text.startswith("#cloud-config\n") and config == build_config(spec))
check("I2 필수 패키지", set(("wireguard", "nftables", "fail2ban")) <= set(config["packages"]))
check("I3 SSH 비밀번호·root 로그인 차단", config["ssh_pwauth"] is False and config["disable_root"] is True and "PasswordAuthentication no" in ssh and "PermitRootLogin no" in ssh)
check("I4 SSH 단일 /32 제한", f"ip saddr {EXAMPLE_ADMIN_CIDR} tcp dport 22" in nft and "0.0.0.0/0 tcp dport" not in nft)
check("I5 입력·전달 기본 차단", nft.count("policy drop;") >= 2)
check("I6 WireGuard UDP만 공개", "udp dport 51820" in nft and "tcp dport 51820" not in nft)
check("I7 IPv4 forwarding·masquerade", "net.ipv4.ip_forward = 1" in files["/etc/sysctl.d/70-freeflexvpn-routing.conf"]["content"] and "masquerade" in nft)
check("I8 개인키는 서버에서 0600으로 생성", "wg genkey > /etc/wireguard/wg0.key" in bootstrap and "chmod 0600 /etc/wireguard/wg0.key" in bootstrap)
check("I9 WireGuard 설정에 평문 개인키 없음", "PrivateKey =" not in wg and "private-key /etc/wireguard/%i.key" in wg)
check("I10 적용 전 SSH·nft 문법 검사", "sshd -t" in bootstrap and "nft -c -f /etc/nftables.conf" in bootstrap)
check("I11 실제 UFW 규칙 활성 시 안전 중단", "LC_ALL=C ufw status" in bootstrap and "Status: active" in bootstrap and "systemctl is-active --quiet ufw" not in bootstrap and "exit 20" in bootstrap)
check("I12 부팅·주기 건강검사", "freeflexvpn-health.timer" in bootstrap and "OnUnitActiveSec=5min" in files["/etc/systemd/system/freeflexvpn-health.timer"]["content"])
check("I13 건강 상태 원자적 기록", "mktemp /var/lib/freeflexvpn/health/.latest" in health and "mv -f \"$tmp\" /var/lib/freeflexvpn/health/latest.json" in health)
check("I14 비밀값 다운로드 파이프 금지", "curl" not in text and "wget" not in text and "BEGIN PRIVATE KEY" not in text)
check("I15 미치환 대문자 토큰 0", re.search(r"__[A-Z][A-Z0-9_]*__", text) is None)
check("I16 예시 후보 배포금지 고지", "EXAMPLE ONLY" in text and "TEST-NET" in text)

bad_cases = [
    ("0.0.0.0/0", False),
    ("10.0.0.0/8", False),
    (EXAMPLE_ADMIN_CIDR, False),
]
rejected = 0
for cidr, example in bad_cases:
    try:
        ExitNodeSpec(cidr, example=example).validated()
    except ValueError:
        rejected += 1
check("I17 광역·문서용 SSH CIDR 실배포 거부", rejected == len(bad_cases), str(rejected))

with tempfile.TemporaryDirectory(prefix="freeflex_ci_") as tmp:
    out = pathlib.Path(tmp) / "node.yaml"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "70_TOOLS" / "build_exit_node_cloud_init.py"), "--example", "--output", str(out)],
        # 이 Windows 검증 채널에서 Python 무작업 시작이 43초까지 실측되어
        # 제품 생성기 실패와 런타임 시작 지연을 혼동하지 않도록 180초를 허용한다.
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    deterministic = out.is_file() and out.read_text(encoding="utf-8") == text
    check("I18 CLI 생성·결정성", proc.returncode == 0 and deterministic, proc.stdout + proc.stderr)
    check("I19 CLI SHA-256 자체 보고", out.is_file() and hashlib.sha256(out.read_bytes()).hexdigest().upper() in proc.stdout)
check("I20 쿼터 에이전트 Python 런타임", "python3" in config["packages"] and "/opt/freeflexvpn/quota_agent.py" in files)
check("I21 쿼터 차단 nftables 세트", "set quota_blocked_v4" in nft and "ip saddr @quota_blocked_v4 drop" in nft)
check("I22 1분 쿼터 타이머", "freeflexvpn-quota.timer" in bootstrap and "OnUnitActiveSec=1min" in files["/etc/systemd/system/freeflexvpn-quota.timer"]["content"])
check("I23 배포 에이전트가 정본 소스와 바이트 일치", files["/opt/freeflexvpn/quota_agent.py"]["content"] == (ROOT / "20_SRC" / "infra" / "quota_agent.py").read_text(encoding="utf-8"))
check("I24 건강검사에 쿼터 타이머 포함", "probe quota_timer" in health)
check("I25 exit admin 배포·실행 권한 제한", files["/opt/freeflexvpn/exit_admin.py"]["permissions"] == "0750")
check("I26 exit admin이 정본 소스와 바이트 일치", files["/opt/freeflexvpn/exit_admin.py"]["content"] == (ROOT / "20_SRC" / "infra" / "exit_admin.py").read_text(encoding="utf-8"))
check("I27 exit admin 상태 디렉터리 0700", "install -d -m 0700 /var/lib/freeflexvpn/admin" in bootstrap)

iap_text = render_cloud_config(
    ExitNodeSpec(GOOGLE_IAP_TCP_FORWARDING_CIDR, node_id="gcp-usw1-01")
)
iap_nft = {
    item["path"]: item for item in parse_rendered(iap_text)["write_files"]
}["/etc/nftables.conf"]["content"]
check(
    "I28 Google IAP SSH 전용 대역 허용",
    f"ip saddr {GOOGLE_IAP_TCP_FORWARDING_CIDR} tcp dport 22" in iap_nft,
)
try:
    ExitNodeSpec("35.235.0.0/16", node_id="gcp-usw1-01").validated()
    broad_iap_rejected = False
except ValueError:
    broad_iap_rejected = True
check("I29 IAP 이외 광역 SSH 대역 거부", broad_iap_rejected)

failed = [item for item in CHECKS if not item[1]]
if failed:
    for label, _, detail in failed:
        print(f"  FAIL {label} — {detail}")
    raise SystemExit(f"cloud-init 검사 {len(CHECKS)-len(failed)}/{len(CHECKS)} 통과 · 실패 {len(failed)}")
print(f"cloud-init 검사 {len(CHECKS)}/{len(CHECKS)} 통과")
