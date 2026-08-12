#!/usr/bin/env python3
"""깨끗하고 원격과 일치하는 FreeFlexVPN 소스에서 AI 인계 ZIP/TXT를 만든다."""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "60_OUTPUTS" / "AI_HANDOFF_CURRENT"
EXCLUDED_DIRS = {
    ".git",
    ".test-venv",
    ".chrome-ci",
    ".chrome-ci2",
    ".tools",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "90_ARCHIVE",
    "_to_delete",
}
EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".DS_Store",
    "debug.log",
    "inst_user_settings.tmp",
}
SUSPICIOUS = [
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
]
PUBLIC_APP = "https://storage.googleapis.com/freeflexvpn-live-20260810-a31d7f/app.html"


@dataclass(frozen=True)
class GitSnapshot:
    head: str
    short: str
    branch: str
    remote: str
    upstream: str


def run(*args: str) -> str:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
    ).stdout.strip()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if relative.parts[:2] == ("60_OUTPUTS", "AI_HANDOFF_CURRENT"):
        return True
    if relative.parts[:2] == (".project-continuity", "local"):
        return True
    if relative.parts and relative.parts[0] == ".project-continuity":
        if relative.name.startswith("LOCK") and relative.suffix.lower() == ".json":
            return True
    if relative.name in EXCLUDED_FILES or relative.suffix.lower() in {".log", ".tmp"}:
        return True
    return False


def selected_source_paths() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if is_excluded(relative):
            continue
        if path.is_file():
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


def git_snapshot() -> GitSnapshot:
    status = run("git", "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise RuntimeError(
            "작업 폴더가 깨끗하지 않아 인계물을 만들지 않았습니다. 먼저 변경 소유와 검사를 확인해 저장 기록으로 남기세요."
        )
    upstream = run("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    ahead_behind = run("git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD").split()
    if ahead_behind != ["0", "0"]:
        raise RuntimeError(
            f"로컬과 원격 기준이 다릅니다(ahead/behind={ahead_behind}). push 또는 동기화 검증 뒤 다시 실행하세요."
        )
    return GitSnapshot(
        head=run("git", "rev-parse", "HEAD"),
        short=run("git", "rev-parse", "--short", "HEAD"),
        branch=run("git", "branch", "--show-current"),
        remote=run("git", "remote", "get-url", "origin"),
        upstream=upstream,
    )


def latest_regression_summary() -> str:
    dashboard = ROOT / "00_START" / "DEVELOPMENT_DASHBOARD.md"
    if not dashboard.is_file():
        return "최신 검사 수치는 인계 증거 문서에서 확인"
    text = dashboard.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"전체 회귀\s+(\d+/\d+)\s*파일[· ]+(\d+/\d+)\s*항목", text)
    if not match:
        return "최신 검사 수치는 인계 증거 문서에서 확인"
    return f"전체 회귀 {match.group(1)} 파일·{match.group(2)} 항목 통과"


def github_release_url(remote: str, tag: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError("GitHub Release URL을 만들 수 없는 원격 주소입니다")
    return f"https://github.com/{match.group(1)}/{match.group(2)}/releases/tag/{tag}"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def add_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def prepare_output(replace_current: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    existing = list(OUT.iterdir())
    if not existing:
        return
    if not replace_current:
        raise RuntimeError(
            "최종 전달 폴더가 비어 있지 않아 기존 인계물을 보존했습니다. 교체하려면 --replace-current를 사용하세요: "
            + ", ".join(path.name for path in existing)
        )
    unexpected = [
        path.name
        for path in existing
        if path.is_dir()
        or not (
            (path.name.startswith("freeflexvpn-ai-handoff-") and path.suffix == ".zip")
            or path.name == "freeflexvpn-next-ai-prompt.txt"
        )
    ]
    if unexpected:
        raise RuntimeError("교체 대상이 아닌 파일이 있어 중단했습니다: " + ", ".join(unexpected))
    for path in existing:
        path.unlink()


def create(replace_current: bool = False) -> tuple[Path, Path]:
    snapshot = git_snapshot()
    source_paths = selected_source_paths()
    hits = secret_scan(source_paths)
    if hits:
        raise RuntimeError("고위험 비밀값 의심 파일이 있어 패키지를 만들지 않았습니다: " + ", ".join(hits))
    prepare_output(replace_current)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "freeflexvpn"
    archive_name = f"{slug}-ai-handoff-{timestamp}-{snapshot.short}.zip"
    prompt_name = f"{slug}-next-ai-prompt.txt"
    release_tag = f"handoff-{timestamp}-{snapshot.short}"
    release_url = github_release_url(snapshot.remote, release_tag)
    tracked = set(run("git", "ls-files").splitlines())
    regression = latest_regression_summary()

    with tempfile.TemporaryDirectory(prefix="ffvpn_handoff_") as temp_name:
        temp = Path(temp_name)
        package = temp / f"{slug}-handoff"
        source_root = package / "10_SOURCE"
        for source in source_paths:
            add_copy(source, source_root / source.relative_to(ROOT))

        write_text(
            package / "00_MANIFEST" / "README-FIRST.md",
            f"""# FreeFlexVPN AI 인계 패키지

1. `manifest.tsv`와 `SHA256SUMS`를 먼저 확인합니다.
2. 이 패키지는 원격과 일치하고 미저장 변경이 없는 Git 기준 HEAD `{snapshot.head}`의 소스입니다.
3. 대화 기억 대신 `30_HANDOFF`와 `20_GIT`을 정본으로 사용합니다.
4. 기존 `ffvpn` 프로필은 삭제·덮어쓰기 금지입니다. 새 검증 프로필의 과거 성공과 기존 프로필의 최신 실패를 구분합니다.
5. 전체 검사 명령: `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`
""",
        )
        git_dir = package / "20_GIT"
        write_text(git_dir / "git_status.txt", "")
        write_text(git_dir / "git_diff.patch", "")
        write_text(git_dir / "untracked_files.txt", "")
        write_text(
            git_dir / "git_context.txt",
            f"remote={snapshot.remote}\nbranch={snapshot.branch}\nupstream={snapshot.upstream}\nhead={snapshot.head}\nahead=0\nbehind=0\n",
        )

        handoff_dir = package / "30_HANDOFF"
        handoff_files = (
            ".project-continuity/STATE.md",
            ".project-continuity/HISTORY.md",
            ".project-continuity/TEST_EVIDENCE.md",
            "00_START/시작하세요.md",
            "00_START/NEW_CODEX_ACCOUNT_HANDOFF.md",
            "00_START/DEVELOPMENT_DASHBOARD.md",
            "10_PLAN/CURRENT_SERVICE_PLAN.md",
            "10_PLAN/CURRENT_DEVELOPMENT_EXECUTION_PLAN.md",
        )
        for relative in handoff_files:
            source = ROOT / relative
            if source.exists():
                add_copy(source, handoff_dir / Path(relative).name)
        write_text(
            package / "40_ENVIRONMENT" / "README.md",
            """# 재현 환경

- Windows PowerShell, Python 및 Playwright Chromium이 현재 검사 환경입니다.
- 의존성: `python -m pip install -r requirements-dev.txt`
- 브라우저: `python -m playwright install chromium`
- 전체 검사: `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`
- 빌드: `python -X utf8 20_SRC/build_web_assets.py`
- 공개는 기존 승인 채널만 사용하며, 새 공개 경로를 만들지 않습니다.
""",
        )
        write_text(
            package / "50_EXTERNAL_ACCESS" / "README.md",
            f"""# 외부 접근 상태

- Git 원격: {snapshot.remote}
- 인계 갈래: {snapshot.branch}
- 기준 HEAD: {snapshot.head}
- 공개 서비스: {PUBLIC_APP}
- 예상 비공개 인계 Release: {release_url}
- 예상 Release 태그: {release_tag}
- 생성 시점에 작업 폴더는 깨끗했고 `{snapshot.upstream}`과 ahead/behind 0/0으로 일치했습니다.
- GitHub Release는 이 기준 HEAD와 ZIP 이름·SHA-256이 일치하는지 확인해야 합니다.
- 인증 열쇠·계정·개인 설정·실제 IP·활성 잠금·기기별 로컬 원장은 패키지에 넣지 않았습니다.
""",
        )
        write_text(
            package / "60_DATA" / "README.md",
            "운영 데이터·개인 설정·개인키는 포함하지 않습니다. 실제 데이터 이전·복원은 격리된 시험 환경에서만 검증합니다.\n",
        )
        write_text(
            package / "70_EVIDENCE" / "latest_checks.txt",
            f"패키지 생성 전 대시보드 최신 증거: {regression}. 받는 환경에서 전체 회귀를 다시 실행해야 합니다.\n",
        )
        write_text(
            package / "80_SCRIPTS" / "verify_commands.txt",
            "python -X utf8 70_TOOLS/make_manifest.py --check\npython -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120\n",
        )

        untracked = [
            path.relative_to(ROOT).as_posix()
            for path in source_paths
            if path.relative_to(ROOT).as_posix() not in tracked
        ]
        if untracked:
            raise RuntimeError("Git 검사 뒤 새 미추적 파일이 발견되어 중단했습니다: " + ", ".join(untracked))

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
        write_text(
            prompt,
            f"""FreeFlexVPN 프로젝트를 인수하세요.

1. ZIP `{archive.name}`의 SHA-256이 아래 값과 같은지 먼저 확인하세요.
   {archive_sha}
2. 새 안전 폴더에 압축을 풀고 `00_MANIFEST/README-FIRST.md`, `manifest.tsv`, `SHA256SUMS`를 먼저 읽으세요.
3. 대화 기억은 정본이 아닙니다. `30_HANDOFF`와 `20_GIT`의 상태를 정본으로 사용하세요.
4. Git 원격 `{snapshot.remote}`의 갈래 `{snapshot.branch}`, 기준 HEAD `{snapshot.head}`를 읽기 전용으로 확인하세요.
5. `git reset`, `checkout`, `clean`, `stash`, 강제 push, 기존 `ffvpn` 프로필 삭제·덮어쓰기를 하지 마세요.
6. `python -X utf8 70_TOOLS/run_all_tests.py --jobs 4 --timeout 120`을 실행해 전체 회귀를 재현하세요.
7. 현재 핵심 문제는 기존 Android `ffvpn` 프로필의 DNS·경로 실패입니다. 별도 검증 프로필의 과거 성공을 완료로 바꾸지 말고, 기존 프로필을 보존한 안전한 비교·재발급 계획부터 진행하세요.
8. Release 자산의 ZIP·TXT SHA-256과 기준 HEAD를 확인하고, 결과를 연속성 기록에 남기세요.

예상 비공개 인계 Release: {release_url}
예상 Release 태그: {release_tag}

인계 패키지 판정: 로컬 검증 준비 완료. 생성 시점에 소스는 깨끗했고 원격과 일치했습니다. 새 PC 독립 재현과 받는 AI의 수락은 받는 환경에서 확인해야 합니다.
다음 첫 행동: 기존 `ffvpn` 프로필을 삭제하지 않고 서버 피어와 재발급 경로를 읽기 전용으로 비교합니다.
""",
        )
    return archive, prompt


def verify(archive: Path, prompt: Path) -> None:
    if not archive.is_file() or not prompt.is_file():
        raise RuntimeError("ZIP 또는 TXT가 없습니다")
    archive_sha = sha(archive)
    prompt_text = prompt.read_text(encoding="utf-8")
    if archive_sha not in prompt_text:
        raise RuntimeError("TXT의 ZIP SHA-256이 실제 파일과 다릅니다")
    with tempfile.TemporaryDirectory(prefix="ffvpn_handoff_verify_") as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(archive) as zipped:
            names = [name for name in zipped.namelist() if name and not name.endswith("/")]
            roots = {Path(name).parts[0] for name in names}
            if roots != {"freeflexvpn-handoff"}:
                raise RuntimeError("ZIP 최상위 폴더가 정확히 하나가 아닙니다")
            forbidden = [
                name
                for name in names
                if "/.project-continuity/local/" in name
                or re.search(r"/\.project-continuity/LOCK[^/]*\.json$", name)
                or "/.tools/" in name
            ]
            if forbidden:
                raise RuntimeError("ZIP에 제외 대상이 있습니다: " + ", ".join(forbidden))
            zipped.extractall(temp)
        package = temp / "freeflexvpn-handoff"
        sums = package / "00_MANIFEST" / "SHA256SUMS"
        if not (package / "00_MANIFEST" / "README-FIRST.md").is_file() or not sums.is_file():
            raise RuntimeError("필수 인계 파일이 없습니다")
        for line in sums.read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            if sha(package / relative) != expected:
                raise RuntimeError(f"내부 SHA-256 불일치: {relative}")
        for relative in ("git_status.txt", "git_diff.patch", "untracked_files.txt"):
            if (package / "20_GIT" / relative).read_text(encoding="utf-8"):
                raise RuntimeError(f"깨끗한 Git 기준이 아닙니다: {relative}")
    print(
        f"ZIP={archive.name}\nZIP_SHA256={archive_sha}\nTXT={prompt.name}\n"
        f"TXT_SHA256={sha(prompt)}\nHANDOFF_LOCAL_VERIFY=PASS"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace-current",
        action="store_true",
        help="AI_HANDOFF_CURRENT 안의 기존 정식 ZIP/TXT 두 파일만 교체합니다.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    archive_path, prompt_path = create(replace_current=args.replace_current)
    verify(archive_path, prompt_path)
