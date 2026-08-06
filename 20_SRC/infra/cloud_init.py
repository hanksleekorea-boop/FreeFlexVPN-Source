#!/usr/bin/env python3
"""전용 Ubuntu 출구 노드용 cloud-init을 비밀값 없이 생성한다.

cloud-config 본문은 JSON으로 직렬화한다. JSON은 YAML의 부분집합이므로 cloud-init의
YAML 로더가 읽을 수 있고, 생성 환경에서는 추가 YAML 의존성 없이 왕복 검증할 수 있다.
"""
from __future__ import annotations

import ipaddress
import json
import pathlib
import re
from dataclasses import dataclass

PRODUCT_NAME = "FreeFlexVPN"
VPN_NETWORK = "10.66.0.0/24"
VPN_SERVER_ADDRESS = "10.66.0.1/24"
DEFAULT_WG_PORT = 51820
DEFAULT_SSH_PORT = 22
EXAMPLE_ADMIN_CIDR = "203.0.113.10/32"
GOOGLE_IAP_TCP_FORWARDING_CIDR = "35.235.240.0/20"


def _quota_agent_source() -> str:
    return (pathlib.Path(__file__).with_name("quota_agent.py")).read_text(encoding="utf-8")


def _exit_admin_source() -> str:
    return (pathlib.Path(__file__).with_name("exit_admin.py")).read_text(encoding="utf-8")


@dataclass(frozen=True)
class ExitNodeSpec:
    admin_ssh_cidr: str
    wg_port: int = DEFAULT_WG_PORT
    ssh_port: int = DEFAULT_SSH_PORT
    node_id: str = "exit-01"
    example: bool = False

    def validated(self) -> "ExitNodeSpec":
        try:
            network = ipaddress.ip_network(self.admin_ssh_cidr, strict=True)
        except ValueError as exc:
            raise ValueError("관리자 SSH 주소는 정확한 IPv4 /32 CIDR이어야 합니다") from exc
        iap_network = ipaddress.ip_network(GOOGLE_IAP_TCP_FORWARDING_CIDR)
        if network.version != 4 or (network.prefixlen != 32 and network != iap_network):
            raise ValueError(
                "관리자 SSH 주소는 IPv4 /32 또는 Google IAP TCP 전달 전용 대역이어야 합니다"
            )
        address = network.network_address
        if address.is_unspecified or address.is_multicast or address.is_loopback:
            raise ValueError("관리자 SSH 주소로 미지정·멀티캐스트·루프백 주소를 쓸 수 없습니다")
        if network == ipaddress.ip_network(EXAMPLE_ADMIN_CIDR) and not self.example:
            raise ValueError("문서용 TEST-NET 주소는 --example에서만 허용됩니다")
        if not 1024 <= int(self.wg_port) <= 65535:
            raise ValueError("WireGuard UDP 포트는 1024~65535여야 합니다")
        if not 1 <= int(self.ssh_port) <= 65535:
            raise ValueError("SSH 포트는 1~65535여야 합니다")
        if int(self.wg_port) == int(self.ssh_port):
            raise ValueError("WireGuard와 SSH 포트는 같을 수 없습니다")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?", self.node_id):
            raise ValueError("node-id는 1~32자의 소문자·숫자·하이픈만 허용합니다")
        return self


def _nftables(spec: ExitNodeSpec) -> str:
    return f"""#!/usr/sbin/nft -f
flush ruleset

table inet freeflex_filter {{
  set quota_blocked_v4 {{
    type ipv4_addr
  }}

  chain input {{
    type filter hook input priority filter; policy drop;
    iifname \"lo\" accept
    ct state invalid drop
    ct state established,related accept
    ip protocol icmp accept
    ip6 nexthdr ipv6-icmp accept
    ip saddr {spec.admin_ssh_cidr} tcp dport {spec.ssh_port} ct state new accept
    udp dport {spec.wg_port} ct state new accept
  }}

  chain forward {{
    type filter hook forward priority filter; policy drop;
    ip saddr @quota_blocked_v4 drop
    # SMTP 스팸 방지: VPN 클라이언트의 외부 TCP/25 전달을 기본 거부한다.
    iifname "wg0" tcp dport 25 counter reject with tcp reset
    # P2P 휴리스틱 기준선: 대표 BitTorrent 포트만 막으며 완전 차단을 주장하지 않는다.
    iifname "wg0" tcp dport {{ 6881-6999, 51413 }} counter reject with tcp reset
    iifname "wg0" udp dport {{ 6881-6999, 51413 }} counter drop
    iifname \"wg0\" oifname != \"wg0\" accept
    iifname != \"wg0\" oifname \"wg0\" ct state established,related accept
  }}

  chain output {{
    type filter hook output priority filter; policy accept;
  }}
}}

table ip freeflex_nat {{
  chain postrouting {{
    type nat hook postrouting priority srcnat; policy accept;
    ip saddr {VPN_NETWORK} oifname != \"wg0\" masquerade
  }}
}}
"""


def _bootstrap() -> str:
    return """#!/usr/bin/env bash
set -Eeuo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

if LC_ALL=C ufw status 2>/dev/null | grep -Fqx 'Status: active'; then
  echo 'FATAL: ufw가 활성 상태입니다. 콘솔에서 방화벽 소유권을 확인하십시오.' >&2
  exit 20
fi

install -d -m 0700 /etc/wireguard
install -d -m 0750 /etc/freeflexvpn /var/lib/freeflexvpn/health
install -d -m 0700 /var/lib/freeflexvpn/admin
if [[ ! -s /etc/wireguard/wg0.key ]]; then
  umask 077
  wg genkey > /etc/wireguard/wg0.key
fi
wg pubkey < /etc/wireguard/wg0.key > /etc/wireguard/wg0.pub
chmod 0600 /etc/wireguard/wg0.key
chmod 0644 /etc/wireguard/wg0.pub

sshd -t
nft -c -f /etc/nftables.conf
sysctl --system
systemctl daemon-reload
systemctl enable --now nftables
systemctl enable --now fail2ban
systemctl enable --now wg-quick@wg0
systemctl enable --now freeflexvpn-health.timer
systemctl enable --now freeflexvpn-quota.timer
systemctl restart ssh
/usr/local/sbin/freeflexvpn-health
touch /var/lib/freeflexvpn/bootstrap-complete
"""


def _health() -> str:
    return """#!/usr/bin/env bash
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
failures=''

probe() {
  local label="$1"; shift
  if ! "$@" >/dev/null 2>&1; then failures="${failures}${label},"; fi
}

probe ip_forward test "$(sysctl -n net.ipv4.ip_forward 2>/dev/null)" = 1
probe nftables systemctl is-active --quiet nftables
probe fail2ban systemctl is-active --quiet fail2ban
probe wireguard systemctl is-active --quiet wg-quick@wg0
probe wg_interface wg show wg0
probe key_mode test "$(stat -c '%a' /etc/wireguard/wg0.key 2>/dev/null)" = 600
probe quota_timer systemctl is-active --quiet freeflexvpn-quota.timer

status=ok
exit_code=0
if [[ -n "$failures" ]]; then status=degraded; exit_code=1; fi
checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
install -d -m 0750 /var/lib/freeflexvpn/health
tmp="$(mktemp /var/lib/freeflexvpn/health/.latest.XXXXXX)" || exit 2
printf '{"status":"%s","checked_at":"%s","failures":"%s"}\n' \
  "$status" "$checked_at" "${failures%,}" > "$tmp"
chmod 0640 "$tmp"
mv -f "$tmp" /var/lib/freeflexvpn/health/latest.json

if [[ $exit_code -ne 0 ]]; then
  logger -t freeflexvpn-health "degraded: ${failures%,}"
fi
exit "$exit_code"
"""


def build_config(spec: ExitNodeSpec) -> dict:
    spec = spec.validated()
    return {
        "package_update": True,
        "package_upgrade": True,
        "packages": ["wireguard", "nftables", "fail2ban", "jq", "python3"],
        "ssh_pwauth": False,
        "disable_root": True,
        "write_files": [
            {
                "path": "/etc/ssh/sshd_config.d/99-freeflexvpn.conf",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "PasswordAuthentication no\n"
                    "KbdInteractiveAuthentication no\n"
                    "PermitRootLogin no\n"
                    "PubkeyAuthentication yes\n"
                    "X11Forwarding no\n"
                    "AllowTcpForwarding no\n"
                ),
            },
            {
                "path": "/etc/sysctl.d/70-freeflexvpn-routing.conf",
                "owner": "root:root",
                "permissions": "0644",
                "content": "net.ipv4.ip_forward = 1\nnet.ipv6.conf.all.forwarding = 0\n",
            },
            {
                "path": "/etc/freeflexvpn/node.env",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    f"PRODUCT_NAME={PRODUCT_NAME}\nNODE_ID={spec.node_id}\n"
                    f"VPN_NETWORK={VPN_NETWORK}\nWG_PORT={spec.wg_port}\n"
                    f"ADMIN_SSH_CIDR={spec.admin_ssh_cidr}\n"
                ),
            },
            {
                "path": "/etc/wireguard/wg0.conf",
                "owner": "root:root",
                "permissions": "0600",
                "content": (
                    "[Interface]\n"
                    f"Address = {VPN_SERVER_ADDRESS}\n"
                    f"ListenPort = {spec.wg_port}\n"
                    "PostUp = wg set %i private-key /etc/wireguard/%i.key\n"
                    "SaveConfig = false\n"
                ),
            },
            {
                "path": "/etc/nftables.conf",
                "owner": "root:root",
                "permissions": "0644",
                "content": _nftables(spec),
            },
            {
                "path": "/etc/fail2ban/jail.d/freeflexvpn-sshd.local",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "[sshd]\nenabled = true\nbackend = systemd\n"
                    "maxretry = 5\nfindtime = 10m\nbantime = 1h\nusedns = no\n"
                ),
            },
            {
                "path": "/opt/freeflexvpn/quota_agent.py",
                "owner": "root:root",
                "permissions": "0750",
                "content": _quota_agent_source(),
            },
            {
                "path": "/opt/freeflexvpn/exit_admin.py",
                "owner": "root:root",
                "permissions": "0750",
                "content": _exit_admin_source(),
            },
            {
                "path": "/usr/local/sbin/freeflexvpn-bootstrap",
                "owner": "root:root",
                "permissions": "0750",
                "content": _bootstrap(),
            },
            {
                "path": "/usr/local/sbin/freeflexvpn-health",
                "owner": "root:root",
                "permissions": "0750",
                "content": _health(),
            },
            {
                "path": "/etc/systemd/system/freeflexvpn-quota.service",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "[Unit]\nDescription=FreeFlexVPN WireGuard quota enforcement\n"
                    "After=wg-quick@wg0.service nftables.service\n"
                    "Requires=wg-quick@wg0.service nftables.service\n\n"
                    "[Service]\nType=oneshot\n"
                    "ExecStart=/usr/bin/python3 /opt/freeflexvpn/quota_agent.py poll\n"
                ),
            },
            {
                "path": "/etc/systemd/system/freeflexvpn-quota.timer",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "[Unit]\nDescription=Poll FreeFlexVPN peer quota every minute\n\n"
                    "[Timer]\nOnBootSec=3min\nOnUnitActiveSec=1min\nPersistent=true\n\n"
                    "[Install]\nWantedBy=timers.target\n"
                ),
            },
            {
                "path": "/etc/systemd/system/freeflexvpn-health.service",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "[Unit]\nDescription=FreeFlexVPN exit-node health probe\nAfter=network-online.target wg-quick@wg0.service\n\n"
                    "[Service]\nType=oneshot\nExecStart=/usr/local/sbin/freeflexvpn-health\n"
                ),
            },
            {
                "path": "/etc/systemd/system/freeflexvpn-health.timer",
                "owner": "root:root",
                "permissions": "0644",
                "content": (
                    "[Unit]\nDescription=Run FreeFlexVPN health probe periodically\n\n"
                    "[Timer]\nOnBootSec=2min\nOnUnitActiveSec=5min\nPersistent=true\n\n"
                    "[Install]\nWantedBy=timers.target\n"
                ),
            },
        ],
        "runcmd": [["/usr/local/sbin/freeflexvpn-bootstrap"]],
        "final_message": "FreeFlexVPN exit-node bootstrap finished. Verify /var/lib/freeflexvpn/health/latest.json from the provider console before closing it.",
    }


def render_cloud_config(spec: ExitNodeSpec) -> str:
    config = build_config(spec)
    warning = (
        "# EXAMPLE ONLY: TEST-NET SSH 주소입니다. 서버에 투입하지 마십시오.\n"
        if spec.example
        else "# DEPLOY CANDIDATE: 전용 신규 Ubuntu 서버와 공급자 콘솔 복구 경로에서만 사용하십시오.\n"
    )
    return "#cloud-config\n" + warning + json.dumps(config, ensure_ascii=False, indent=2) + "\n"


def parse_rendered(text: str) -> dict:
    if not text.startswith("#cloud-config\n"):
        raise ValueError("cloud-config 헤더가 없습니다")
    start = text.find("{")
    if start < 0:
        raise ValueError("cloud-config 본문이 없습니다")
    return json.loads(text[start:])
