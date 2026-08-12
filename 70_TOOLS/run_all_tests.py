#!/usr/bin/env python3
"""모든 test_*.py를 제한 병렬 실행하고 후보 단위 결과를 집계한다."""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib
import importlib.metadata
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUMMARY = re.compile(r"(\d+)/(\d+)(?:\s*(?:통과|PASS))?")
# These tests rebuild shared 30_DEPLOY assets.  Keep every writer out of the
# parallel pool so a fast machine cannot read a half-written app shell.
SERIAL_FIRST = (
    "test_app_v2_contract.py",
    "test_first_use_recovery_ui.py",
    "test_github_pages.py",
    "test_protection_evidence_ui.py",
    "test_protection_status_ui.py",
    "test_service_ui_v2_6.py",
    "test_service_ui_v3.py",
    "test_server_usage_empty_ui.py",
)
REQUIRED_MODULES = {
    "playwright": "브라우저 계약 검사",
    "cv2": "QR 디코딩 검사",
    "numpy": "QR 이미지 검사",
    "qrcode": "QR 생성 검사",
    "PIL": "QR PNG 생성 검사",
}
VERSION_RULES = {
    "cv2": ((4, 8), (6, 0), "OpenCV 4.8 이상 6 미만"),
    "qrcode": ((8, 0), (9, 0), "qrcode 8 이상 9 미만"),
    "PIL": ((9, 1), None, "Pillow 9.1 이상"),
}


def missing_test_dependencies() -> list[tuple[str, str]]:
    """전체 회귀를 시작하기 전에 필수 검사 모듈 누락을 빠르게 알린다."""
    return [
        (module, purpose)
        for module, purpose in REQUIRED_MODULES.items()
        if importlib.util.find_spec(module) is None
    ]


def _installed_version(module: str) -> tuple[int, ...]:
    imported = importlib.import_module(module)
    value = getattr(imported, "__version__", None)
    if value is None and module == "qrcode":
        value = importlib.metadata.version("qrcode")
    match = re.match(r"^(\d+)(?:\.(\d+))?", str(value or ""))
    if not match:
        raise ValueError(f"{module} 버전을 읽을 수 없습니다")
    return tuple(int(part or 0) for part in match.groups())


def incompatible_test_dependencies() -> list[tuple[str, str]]:
    issues = []
    for module, (minimum, maximum, description) in VERSION_RULES.items():
        if importlib.util.find_spec(module) is None:
            continue
        try:
            installed = _installed_version(module)
        except (ImportError, ValueError, importlib.metadata.PackageNotFoundError) as exc:
            issues.append((module, f"{description} 필요; 버전 확인 실패: {type(exc).__name__}"))
            continue
        if installed < minimum or (maximum is not None and installed >= maximum):
            issues.append((module, f"{description} 필요; 현재 {'.'.join(map(str, installed))}"))
    return issues


def print_result(result: dict[str, object]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(
        f"{status} {result['file']} {result['passed']}/{result['total']} {result['seconds']:.1f}s",
        flush=True,
    )
    if not result["ok"]:
        print(result["output"], flush=True)


def write_json_new(path: pathlib.Path, payload: dict[str, object]) -> None:
    """부분 결과나 기존 증거를 덮지 않고 완료된 집계만 원자 저장한다."""
    if path.exists():
        raise FileExistsError(f"기존 회귀 증거는 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run_one(path: pathlib.Path, timeout: int) -> dict[str, object]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", str(path)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout + completed.stderr
        matches = list(SUMMARY.finditer(output))
        passed, total = (int(matches[-1].group(1)), int(matches[-1].group(2))) if matches else (0, 0)
        return {
            "file": path.name, "ok": completed.returncode == 0,
            "passed": passed, "total": total, "seconds": time.monotonic() - started,
            "output": output,
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return {
            "file": path.name, "ok": False, "passed": 0, "total": 0,
            "seconds": time.monotonic() - started, "output": output + f"\nTIMEOUT {timeout}s",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--json-output", help="새 회귀 증거 JSON 경로(기존 파일 덮어쓰기 금지)")
    args = parser.parse_args()
    if not 1 <= args.jobs <= 6 or not 60 <= args.timeout <= 900:
        parser.error("jobs는 1..6, timeout은 60..900초여야 합니다")
    missing = missing_test_dependencies()
    incompatible = incompatible_test_dependencies()
    if missing or incompatible:
        print("전체 회귀를 시작하지 않았습니다: 현재 Python 검사 의존성이 불완전하거나 버전 범위를 벗어났습니다.", flush=True)
        for module, purpose in missing + incompatible:
            print(f"- {module}: {purpose}", flush=True)
        print(f"Python: {sys.executable}", flush=True)
        print("의존성이 설치된 프로젝트 검사 환경으로 다시 실행하세요.", flush=True)
        return 2
    files = sorted((ROOT / "40_TESTS").glob("test_*.py"))
    started = time.monotonic()
    by_name = {path.name: path for path in files}
    serial_files = [by_name[name] for name in SERIAL_FIRST if name in by_name]
    parallel_files = [path for path in files if path.name not in SERIAL_FIRST]
    results = []
    for path in serial_files:
        result = run_one(path, args.timeout)
        results.append(result)
        print_result(result)
        if not result["ok"]:
            break
    if any(not result["ok"] for result in results):
        parallel_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_one, path, args.timeout): path for path in parallel_files}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print_result(result)
    results.sort(key=lambda result: str(result["file"]))
    passed = sum(int(result["passed"]) for result in results)
    total = sum(int(result["total"]) for result in results)
    failed_files = [str(result["file"]) for result in results if not result["ok"]]
    elapsed = time.monotonic() - started
    print(
        f"전체 회귀 파일 {len(files)-len(failed_files)}/{len(files)} · 검사 {passed}/{total} · "
        f"실패 파일 {len(failed_files)} · {elapsed:.1f}s",
        flush=True,
    )
    if args.json_output:
        output = pathlib.Path(args.json_output)
        if not output.is_absolute():
            output = (pathlib.Path.cwd() / output).resolve()
        write_json_new(
            output,
            {
                "schema": "FreeFlexVPNRegressionEvidenceV1",
                "status": "passed" if not failed_files and passed == total and total > 0 else "failed",
                "files_passed": len(files) - len(failed_files),
                "files_total": len(files),
                "checks_passed": passed,
                "checks_total": total,
                "failed_files": failed_files,
                "elapsed_seconds": round(elapsed, 3),
                "results": [
                    {
                        key: round(float(value), 3) if key == "seconds" else value
                        for key, value in result.items() if key != "output"
                    }
                    for result in results
                ],
            },
        )
        print(f"회귀 증거: {output}", flush=True)
    return 1 if failed_files or passed != total or total == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
