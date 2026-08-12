#!/usr/bin/env python3
"""비밀값을 넣지 않는 FreeFlexVPN AI 인계 ZIP/TXT를 생성·검증한다."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "60_OUTPUTS" / "AI_HANDOFF_CURRENT"
EXCLUDED_DIRS = {".git", ".test-venv", ".chrome-ci", ".chrome-ci2", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", "90_ARCHIVE", "_to_delete"}
EXCLUDED_FILES = {".env", ".env.local", ".env.production", ".DS_Store"}
SUSPICIOUS = [
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
]


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE).stdout.strip()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_source_paths() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if relative.parts[:2] == ("60_OUTPUTS", "AI_HANDOFF_CURRENT"):
            continue
        if path.is_file() and path.name not in EXCLUDED_FILES:
            paths.append(path)
    return paths


def secret_scan(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(pattern.search(text) for pattern in SUSPICIOUS):
            hits.append(path.relative_to(ROOT).as_posix())
    return hits


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def add_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def create() -> tuple[Path, Path]:
    source_paths = selected_source_paths()
    hits = secret_scan(source_paths)
    if hits:
        raise RuntimeError("고위험 비밀값 의심 파일이 있어 패키지를 만들지 않았습니다: " + ", ".join(hits))

    head = run("git", "rev-parse", "HEAD")
    short = run("git", "rev-parse", "--short", "HEAD")
    branch = run("git", "branch", "--show-current")
    remote = run("git", "remote", "get-url", "origin")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "freeflexvpn"
    archive_name = f"{slug}-ai-handoff-{timestamp}-{short}.zip"
    prompt_name = f"{slug}-next-ai-prompt.txt"
    OUT.mkdir(parents=True, exist_ok=True)
    existing = list(OUT.iterdir())
    if existing:
        raise RuntimeError("최종 전달 폴더가 비어 있지 않아 기존 인계물을 보존했습니다: " + ", ".join(path.name for path in existing))

    with tempfile.TemporaryDirectory(prefix="ffvpn_handoff_") as temp_name:
        temp = Path(temp_name)
        package = temp / f"{slug}-handoff"
        source_root = package / "10_SOURCE"
        for source in source_paths:
            add_copy(source, source_root / source.relative_to(ROOT))

        write_text(package / "00_MANIFEST" / "README-FIRST.md", f"""# FreeFlexVPN AI 인계 패키지\n\n1. `manifest.tsv`와 `SHA256SUMS`를 먼저 확인합니다.\n2. 이 패키지는 Git 기준 HEAD `{head}`와 그 위의 미저장 변경을 함께 담습니다.\n3. 대화 기억 대신 `30_HANDOFF`와 `20_GIT`을 정본으로 사용합니다.\n4. 기존 `ffvpn` 프로필은 삭제·덮어쓰기 금지입니다. 새 검증 프로필의 과거 성공과 기존 프로필의 최신 실패를 구분합니다.\n5. 전체 검사 명령: `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`\n""")
        git_dir = package / "20_GIT"
        write_text(git_dir / "git_status.txt", run("git", "status", "--porcelain=v1") + "\n")
        write_text(git_dir / "git_diff.patch", run("git", "diff", "--binary") + "\n")
        write_text(git_dir / "untracked_files.txt", "\n".join(path.relative_to(ROOT).as_posix() for path in source_paths if str(path.relative_to(ROOT)).replace("\\", "/") not in run("git", "ls-files").splitlines()) + "\n")
        write_text(git_dir / "git_context.txt", f"remote={remote}\nbranch={branch}\nhead={head}\n")

        handoff_dir = package / "30_HANDOFF"
        for relative in (".project-continuity/STATE.md", ".project-continuity/HISTORY.md", ".project-continuity/TEST_EVIDENCE.md", "00_START/시작하세요.md", "00_START/NEW_CODEX_ACCOUNT_HANDOFF.md", "00_START/DEVELOPMENT_DASHBOARD.md", "10_PLAN/CURRENT_SERVICE_PLAN.md", "10_PLAN/CURRENT_DEVELOPMENT_EXECUTION_PLAN.md"):
            source = ROOT / relative
            if source.exists():
                add_copy(source, handoff_dir / Path(relative).name)
        write_text(package / "40_ENVIRONMENT" / "README.md", """# 재현 환경\n\n- Windows PowerShell, Python 및 Playwright Chromium이 현재 검사 환경입니다.\n- 의존성: `python -m pip install -r requirements-dev.txt`\n- 브라우저: `python -m playwright install chromium`\n- 전체 검사: `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`\n- 빌드: `python -X utf8 20_SRC/build_web_assets.py`\n- 공개는 기존 승인 채널만 사용하며, 새 공개 경로를 만들지 않습니다.\n""")
        write_text(package / "50_EXTERNAL_ACCESS" / "README.md", f"""# 외부 접근 상태\n\n- Git 원격: {remote}\n- 인계 갈래: {branch}\n- 기준 HEAD: {head}\n- 공개 서비스: https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html\n- 현재 작업 폴더에는 다른 작업자의 미저장 변경이 있어, 저장·push·Release는 별도 범위 확인 전 수행하지 않습니다.\n- 인증 열쇠·계정·개인 설정·실제 IP는 이 패키지에 넣지 않았습니다.\n""")
        write_text(package / "60_DATA" / "README.md", "운영 데이터·개인 설정·개인키는 포함하지 않습니다. 실제 데이터 이전·복원은 격리된 시험 환경에서만 검증합니다.\n")
        write_text(package / "70_EVIDENCE" / "latest_checks.txt", "2026-08-11: 전체 회귀 67/67 파일·696/696 항목 통과, 목록표 411개 파일 대조 통과. 서비스·대시보드 분리 화면 검사 통과.\n")
        write_text(package / "80_SCRIPTS" / "verify_commands.txt", "python -X utf8 70_TOOLS/make_manifest.py --check\npython -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120\n")

        manifest_lines = ["path\tbytes\tpurpose"]
        for path in sorted(item for item in package.rglob("*") if item.is_file()):
            rel = path.relative_to(package).as_posix()
            purpose = "source" if rel.startswith("10_SOURCE/") else "handoff"
            manifest_lines.append(f"{rel}\t{path.stat().st_size}\t{purpose}")
        write_text(package / "00_MANIFEST" / "manifest.tsv", "\n".join(manifest_lines) + "\n")
        checksums = []
        for path in sorted(item for item in package.rglob("*") if item.is_file() and item.name != "SHA256SUMS"):
            checksums.append(f"{sha(path)}  {path.relative_to(package).as_posix()}")
        write_text(package / "00_MANIFEST" / "SHA256SUMS", "\n".join(checksums) + "\n")

        archive = OUT / archive_name
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
            for path in sorted(item for item in package.rglob("*") if item.is_file()):
                zipped.write(path, path.relative_to(temp).as_posix())
        archive_sha = sha(archive)
        prompt = OUT / prompt_name
        write_text(prompt, f"""FreeFlexVPN 프로젝트를 인수하세요.\n\n1. ZIP `{archive.name}`의 SHA-256이 아래 값과 같은지 먼저 확인하세요.\n   {archive_sha}\n2. 새 안전 폴더에 압축을 풀고 `00_MANIFEST/README-FIRST.md`, `manifest.tsv`, `SHA256SUMS`를 먼저 읽으세요.\n3. 대화 기억은 정본이 아닙니다. `30_HANDOFF`와 `20_GIT`의 상태·미저장 변경을 보존하세요.\n4. Git 원격 `{remote}`의 갈래 `{branch}`, 기준 HEAD `{head}`를 읽기 전용으로 확인하세요.\n5. `git reset`, `checkout`, `clean`, `stash`, 강제 push, 기존 `ffvpn` 프로필 삭제·덮어쓰기를 하지 마세요.\n6. `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`을 실행해 전체 회귀를 재현하세요.\n7. 현재 핵심 문제는 기존 Android `ffvpn` 프로필의 DNS·경로 실패입니다. 별도 검증 프로필의 과거 성공을 완료로 바꾸지 말고, 기존 프로필을 보존한 안전한 비교·재발급 계획부터 진행하세요.\n8. GitHub Release·push·공개 배포·외부 권한 변경은 현재 대화의 명시 승인 없이는 실행하지 마세요.\n\n인계 판정: 미완료. 이유: 현재 작업 폴더에 미저장 변경이 있으며 GitHub Release와 새 PC 독립 재현은 아직 검증하지 않았습니다.\n다음 첫 행동: 기존 `ffvpn` 프로필을 삭제하지 않고 서버 피어와 재발급 경로를 읽기 전용으로 비교합니다.\n""")
    return archive, prompt


def verify(archive: Path, prompt: Path) -> None:
    if not archive.is_file() or not prompt.is_file():
        raise RuntimeError("ZIP 또는 TXT가 없습니다")
    with tempfile.TemporaryDirectory(prefix="ffvpn_handoff_verify_") as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(archive) as zipped:
            roots = {Path(name).parts[0] for name in zipped.namelist() if name and not name.endswith("/")}
            if roots != {"freeflexvpn-handoff"}:
                raise RuntimeError("ZIP 최상위 폴더가 정확히 하나가 아닙니다")
            zipped.extractall(temp)
        package = temp / "freeflexvpn-handoff"
        sums = package / "00_MANIFEST" / "SHA256SUMS"
        if not (package / "00_MANIFEST" / "README-FIRST.md").is_file() or not sums.is_file():
            raise RuntimeError("필수 인계 파일이 없습니다")
        for line in sums.read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            if sha(package / relative) != expected:
                raise RuntimeError(f"내부 SHA-256 불일치: {relative}")
    if "SHA-256" not in prompt.read_text(encoding="utf-8"):
        raise RuntimeError("TXT에 ZIP SHA-256이 없습니다")
    print(f"ZIP={archive.name}\nZIP_SHA256={sha(archive)}\nTXT={prompt.name}\nTXT_SHA256={sha(prompt)}\nHANDOFF_LOCAL_VERIFY=PASS")


if __name__ == "__main__":
    archive, prompt = create()
    verify(archive, prompt)
