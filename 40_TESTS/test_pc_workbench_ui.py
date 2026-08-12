#!/usr/bin/env python3
"""F2-3: PC workbench exposes four honest, reachable summary areas."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "20_SRC" / "html_templates" / "service_shell.html").read_text(encoding="utf-8")
CSS = (ROOT / "20_SRC" / "html_templates" / "service_shell.css").read_text(encoding="utf-8")


def contract(text: str, css: str) -> bool:
    return all((
        'svc-desktop-workbench' in text,
        'PC 작업대' in text,
        '기기·보호 상태·사용량·통계를 나란히 봅니다.' in text,
        '보호됨으로 표시하지 않습니다.' in text,
        '실제 사용량 원장이 없으므로' in text,
        'svc-workbench-grid' in css,
        '.svc-workbench-grid{display:grid;grid-template-columns:repeat(4,1fr)' in css,
        '@media(max-width:760px){.svc-desktop-workbench{display:none}}' in css,
    ))


def main() -> None:
    assert contract(SHELL, CSS), 'PC workbench contract broken'
    assert not contract(SHELL.replace('PC 작업대', 'removed', 1), CSS), 'negative control: title removal not detected'
    assert not contract(SHELL, CSS.replace('.svc-workbench-grid{display:grid;grid-template-columns:repeat(4,1fr)', '.svc-workbench-grid{display:grid;grid-template-columns:1fr')), 'negative control: four-column layout removal not detected'
    print('PC workbench UI: 10/10 passed')


if __name__ == '__main__':
    main()
