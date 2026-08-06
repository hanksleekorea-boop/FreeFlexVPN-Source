#!/usr/bin/env python3
"""검증된 30_DEPLOY 산출물만 별도 GitHub Pages 저장소로 복사한다."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_REPO = ROOT.parent / "FreeFlexVPN-Pages"
DEPLOY = ROOT / "30_DEPLOY"
SOURCE = ROOT / "20_SRC" / "github_pages"
STATIC_FILES = ("sw.js", "app-qr.png", "app-qr-evidence.json", "icon-192.png", "icon-512.png")
TOOL_FILES = ("verify_app.py", "build_public_manifest.py", "check_inline_js.mjs", "build_app_qr.py")


def build() -> dict[str, object]:
    PUBLIC_REPO.mkdir(parents=True, exist_ok=True)
    workflow_dir = PUBLIC_REPO / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    expected = {source.name for source in DEPLOY.glob("*.html")}
    for existing in PUBLIC_REPO.glob("*.html"):
        if existing.name not in expected:
            existing.unlink()
    for source in sorted(DEPLOY.glob("*.html")):
        target = PUBLIC_REPO / source.name
        shutil.copy2(source, target)
    for source in sorted(DEPLOY.glob("*.js")):
        shutil.copy2(source, PUBLIC_REPO / source.name)
    shutil.copy2(SOURCE / "pages.yml", workflow_dir / "pages.yml")
    shutil.copy2(SOURCE / "README.md", PUBLIC_REPO / "README.md")
    shutil.copy2(SOURCE / ".gitignore", PUBLIC_REPO / ".gitignore")
    for name in STATIC_FILES:
        shutil.copy2(SOURCE / name, PUBLIC_REPO / name)
    public_tools = PUBLIC_REPO / "tools"
    public_tools.mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        shutil.copy2(SOURCE / "tools" / name, public_tools / name)
    (PUBLIC_REPO / ".nojekyll").write_text("", encoding="utf-8")

    if not (PUBLIC_REPO / "index.html").exists():
        raise RuntimeError("GitHub Pages 진입점 index.html이 없습니다")

    manifest_path = PUBLIC_REPO / "PUBLIC_MANIFEST.json"
    files = [
        path
        for path in PUBLIC_REPO.rglob("*")
        if path.is_file() and ".git" not in path.parts and path != manifest_path
    ]
    manifest = {
        path.relative_to(PUBLIC_REPO).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(files)
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"repo": str(PUBLIC_REPO), "html": len(expected), "files": len(manifest) + 1}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
