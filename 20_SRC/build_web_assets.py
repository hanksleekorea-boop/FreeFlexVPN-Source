#!/usr/bin/env python3
"""FreeFlexVPN 단일 파일 PWA 후보를 템플릿에서 재생성한다."""
from __future__ import annotations

import base64
import json
import re
import shutil
import sys
from pathlib import Path

import cost_model
import build_app_v2

try:
    from icons import encoded_icons as _generated_icons
except ImportError:
    _generated_icons = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Path(__file__).resolve().parent / "html_templates"
OUTPUT = ROOT / "30_DEPLOY"
PROTOTYPE_OUTPUT = ROOT / "60_OUTPUTS" / "prototype" / "FreeFlexVPN_service_v2.6.html"
PUBLIC_ASSETS = ROOT / "20_SRC" / "github_pages"
APP_SOURCE = ROOT / "20_SRC" / "app"
SERVICE_GLOBAL_STYLES = TEMPLATES / "service_global.css"
APP_MODULES = ("client_keygen.js", "pwa_api_client.js", "moment_catalog.js", "platform_support.js", "pc_readiness.js", "mobile_readiness.js", "commercial_readiness.js", "protection_evidence.js", "profile_lifecycle.js", "error_recovery.js", "pwa_runtime.js")
RUNTIME_SCRIPT_TAG = '<script type="module" src="./pwa_runtime.js"></script>'


def encoded_icons() -> dict[int, str]:
    """화면 라이브러리가 막힌 PC에서도 이미 검증한 PNG 아이콘으로 안전하게 재생성한다."""
    if _generated_icons is not None:
        return _generated_icons()
    result: dict[int, str] = {}
    for size in (192, 512):
        source = PUBLIC_ASSETS / f"icon-{size}.png"
        if not source.is_file() or source.stat().st_size <= 0:
            raise RuntimeError(f"아이콘 생성 라이브러리와 기존 아이콘을 모두 사용할 수 없습니다: {source}")
        result[size] = base64.b64encode(source.read_bytes()).decode("ascii")
    return result

SERVICE_GLOBAL_NAV = """<header class="ff-global"><div class="ff-global-in"><a class="ff-global-brand" href="index.html"><span class="ff-global-mark">FF</span>FreeFlexVPN</a><nav class="ff-global-links" aria-label="서비스 이동"><a href="app.html">서비스 열기</a><a href="index.html">제품 소개</a><a href="development-dashboard.html">개발 현황</a></nav></div></header>"""

ASSETS = {
    "landing.html": ("index.html", "공식 시작"),
    "app_v2.html": ("app.html", "알파 UI v2.5 PC-2·3"),
    "development_dashboard.html": ("development-dashboard.html", "개발 진행 현황"),
    "simple.html": ("FreeFlexVPN_비용계산서.html", "비용 계산서"),
    "d1_tpl.html": ("FreeFlexVPN_1일오픈_체크리스트.html", "1일 오픈 체크리스트"),
    "country_tpl.html": ("VPN_국가별_서버비용_50개국.html", "국가별 서버 비용"),
    "template.html": ("VPN_1000명_비용기간_대시보드.html", "비용·기간 대시보드"),
    "opt_tpl.html": ("VPN_20개국_분산_비용최적화.html", "20개국 비용 최적화"),
    "price_tpl.html": ("종량제_VPN_가격패키지_설계.html", "가격 패키지 설계"),
}


def manifest(label: str, icons: dict[int, str], start_url: str = ".") -> str:
    data = {
        "name": f"{cost_model.PRODUCT_NAME} · {label}",
        "short_name": cost_model.PRODUCT_NAME,
        "start_url": start_url,
        "id": "./app.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#0f1115",
        "theme_color": "#0f1420",
        "icons": [
            {
                "src": f"data:image/png;base64,{icons[size]}",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any maskable",
            }
            for size in (192, 512)
        ],
    }
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def bundled_runtime() -> str:
    """브라우저 모듈을 배포 HTML 안에 넣어 단일 파일 계약을 유지한다."""
    api_client = (APP_SOURCE / "pwa_api_client.js").read_text(encoding="utf-8")
    keygen = (APP_SOURCE / "client_keygen.js").read_text(encoding="utf-8")
    moment_catalog = (APP_SOURCE / "moment_catalog.js").read_text(encoding="utf-8")
    platform_support = (APP_SOURCE / "platform_support.js").read_text(encoding="utf-8")
    pc_readiness = (APP_SOURCE / "pc_readiness.js").read_text(encoding="utf-8")
    mobile_readiness = (APP_SOURCE / "mobile_readiness.js").read_text(encoding="utf-8")
    commercial_readiness = (APP_SOURCE / "commercial_readiness.js").read_text(encoding="utf-8")
    protection_evidence = (APP_SOURCE / "protection_evidence.js").read_text(encoding="utf-8")
    profile_lifecycle = (APP_SOURCE / "profile_lifecycle.js").read_text(encoding="utf-8")
    error_recovery = (APP_SOURCE / "error_recovery.js").read_text(encoding="utf-8")
    runtime = (APP_SOURCE / "pwa_runtime.js").read_text(encoding="utf-8")
    api_client = re.sub(r"(?m)^export\s+", "", api_client)
    keygen = re.sub(r"(?m)^export\s+", "", keygen)
    moment_catalog = re.sub(r"(?m)^export\s+", "", moment_catalog)
    platform_support = re.sub(r"(?m)^export\s+", "", platform_support)
    pc_readiness = re.sub(r"(?m)^export\s+", "", pc_readiness)
    mobile_readiness = re.sub(r"(?m)^export\s+", "", mobile_readiness)
    commercial_readiness = re.sub(r"(?m)^export\s+", "", commercial_readiness)
    protection_evidence = re.sub(r"(?m)^export\s+", "", protection_evidence)
    profile_lifecycle = re.sub(r"(?m)^export\s+", "", profile_lifecycle)
    error_recovery = re.sub(r"(?m)^export\s+", "", error_recovery)
    runtime = re.sub(r'(?m)^import\s+.*?\s+from\s+"\./[^\"]+";\s*$', "", runtime)
    return (
        '<script type="module" data-freeflex-runtime="inline">\n'
        f"// pwa_api_client.js\n{api_client}\n"
        f"// client_keygen.js\n{keygen}\n"
        f"// moment_catalog.js\n{moment_catalog}\n"
        f"// platform_support.js\n{platform_support}\n"
        f"// pc_readiness.js\n{pc_readiness}\n"
        f"// mobile_readiness.js\n{mobile_readiness}\n"
        f"// commercial_readiness.js\n{commercial_readiness}\n"
        f"// protection_evidence.js\n{protection_evidence}\n"
        f"// profile_lifecycle.js\n{profile_lifecycle}\n"
        f"// error_recovery.js\n{error_recovery}\n"
        f"// pwa_runtime.js\n{runtime}\n"
        "</script>"
    )


def apply_service_document_theme(text: str, output_name: str) -> str:
    """고객 앱 밖의 운영 자료도 같은 서비스 시각 언어와 이동 경로를 사용한다."""
    if output_name in {"index.html", "app.html", "development-dashboard.html"}:
        return text
    text = text.replace('data-theme="dark"', 'data-theme="light"', 1)
    text = text.replace('id="themeBtn">라이트</button>', 'id="themeBtn">다크</button>', 1)
    text = text.replace(
        '<meta name="theme-color" content="#0f1420">',
        '<meta name="theme-color" content="#f6f6f3">',
        1,
    )
    styles = SERVICE_GLOBAL_STYLES.read_text(encoding="utf-8")
    if text.count("</head>") != 1:
        raise RuntimeError(f"공통 디자인 head 경계가 올바르지 않습니다: {output_name}")
    text = text.replace("</head>", f'<style data-freeflex-global-theme>\n{styles}\n</style>\n</head>', 1)
    body_match = re.search(r"<body(?P<attrs>[^>]*)>", text)
    if not body_match:
        raise RuntimeError(f"공통 디자인 body 경계가 없습니다: {output_name}")
    attrs = body_match.group("attrs")
    if 'class="' in attrs:
        attrs = attrs.replace('class="', 'class="service-doc ', 1)
    else:
        attrs += ' class="service-doc"'
    replacement = f"<body{attrs}>\n{SERVICE_GLOBAL_NAV}"
    return text[: body_match.start()] + replacement + text[body_match.end() :]


def build() -> list[Path]:
    build_app_v2.build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    icons = encoded_icons()
    written = []
    for template_name, (output_name, label) in ASSETS.items():
        text = (TEMPLATES / template_name).read_text(encoding="utf-8")
        text = text.replace("__ICON192__", icons[192])
        text = text.replace("__ICON512__", icons[512])
        start_url = "./app.html?view=app" if output_name == "app.html" else "."
        text = text.replace("__MANIFEST_B64__", manifest(label, icons, start_url))
        if output_name == "app.html":
            qr_b64 = base64.b64encode((PUBLIC_ASSETS / "app-qr.png").read_bytes()).decode("ascii")
            text = text.replace("__APP_QR_B64__", qr_b64)
            if text.count(RUNTIME_SCRIPT_TAG) != 1:
                raise RuntimeError("PWA 런타임 진입점은 정확히 하나여야 합니다")
            text = text.replace(RUNTIME_SCRIPT_TAG, bundled_runtime())
        text = apply_service_document_theme(text, output_name)
        if "__ICON" in text or "__MANIFEST_B64__" in text or "__APP_QR_B64__" in text:
            raise RuntimeError(f"미치환 플레이스홀더: {template_name}")
        target = OUTPUT / output_name
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
        if output_name == "app.html":
            PROTOTYPE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            PROTOTYPE_OUTPUT.write_text(text, encoding="utf-8", newline="\n")
            written.append(PROTOTYPE_OUTPUT)
    qr_target = OUTPUT / "app-qr.png"
    shutil.copy2(PUBLIC_ASSETS / "app-qr.png", qr_target)
    written.append(qr_target)
    for name in APP_MODULES:
        target = OUTPUT / name
        shutil.copy2(APP_SOURCE / name, target)
        written.append(target)
    return written


if __name__ == "__main__":
    for path in build():
        print(f"generated {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")
