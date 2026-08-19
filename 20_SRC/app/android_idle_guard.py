"""Choose at most one safe idle Android test device without mutating either phone."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence


SCHEMA = "FreeFlexVPNAndroidIdleGuardV1"
SERIAL = re.compile(r"^[A-Za-z0-9._:-]{4,128}$")
WAKEFULNESS = re.compile(r"mWakefulness=(Awake|Asleep|Dozing|Dreaming)")
MODEL = re.compile(r"\bmodel:([^\s]+)")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


Runner = Callable[[Sequence[str]], CommandResult]


def _run(argv: Sequence[str]) -> CommandResult:
    completed = subprocess.run(
        list(argv), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=20
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _fingerprint(serial: str) -> str:
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()[:16]


def _validate_serial(serial: str) -> str:
    if not SERIAL.fullmatch(serial):
        raise ValueError("invalid Android serial")
    return serial


def parse_devices(raw: str) -> list[dict[str, str]]:
    """Parse ``adb devices -l`` and retain only non-sensitive model/state metadata."""
    devices: list[dict[str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[:2]
        if not SERIAL.fullmatch(serial):
            continue
        model = MODEL.search(line)
        devices.append({"serial": serial, "state": state, "model": model.group(1) if model else "unknown"})
    return devices


def _wakefulness(raw: str) -> str:
    match = WAKEFULNESS.search(raw)
    return match.group(1).lower() if match else "unknown"


def _bool_setting(raw: str) -> bool:
    return raw.strip().lower() not in {"", "null", "0", "false", "none"}


def _read_only(argv: Sequence[str]) -> bool:
    """Allow only the ADB queries this guard needs; reject all mutation-capable forms."""
    if len(argv) == 3 and list(argv[1:]) == ["devices", "-l"]:
        return True
    if len(argv) < 6 or argv[1] != "-s" or argv[3] != "shell":
        return False
    if not SERIAL.fullmatch(argv[2]):
        return False
    return tuple(argv[4:]) in {
        ("dumpsys", "power"),
        ("dumpsys", "window", "windows"),
        ("settings", "get", "secure", "always_on_vpn_app"),
        ("settings", "get", "secure", "always_on_vpn_lockdown"),
    }


def inspect_devices(*, adb: str, runner: Runner = _run) -> list[dict[str, object]]:
    """Return redacted, read-only device observations; no app title or serial is emitted."""
    listing_command = (adb, "devices", "-l")
    if not _read_only(listing_command):
        raise ValueError("Android read-only command policy rejected listing")
    listing = runner(listing_command)
    if listing.returncode:
        return []

    observations: list[dict[str, object]] = []
    for device in parse_devices(listing.stdout):
        serial = _validate_serial(device["serial"])
        state = device["state"]
        if state != "device":
            observations.append({
                "device_fingerprint": _fingerprint(serial), "model": device["model"], "adb_state": state,
                "wakefulness": "unknown", "foreground_interactive": None, "always_on_configured": None,
                "lockdown_enabled": None, "eligible": False, "reason": "adb_not_ready",
            })
            continue

        def query(*parts: str) -> CommandResult:
            command = (adb, "-s", serial, "shell", *parts)
            if not _read_only(command):
                raise ValueError("Android read-only command policy rejected query")
            return runner(command)

        power = query("dumpsys", "power")
        window = query("dumpsys", "window", "windows")
        always_on = query("settings", "get", "secure", "always_on_vpn_app")
        lockdown = query("settings", "get", "secure", "always_on_vpn_lockdown")
        wakefulness = _wakefulness(power.stdout) if power.returncode == 0 else "unknown"
        foreground_interactive = bool(re.search(r"mCurrentFocus=|mFocusedApp=", window.stdout)) if window.returncode == 0 else None
        always_on_configured = _bool_setting(always_on.stdout) if always_on.returncode == 0 else None
        lockdown_enabled = _bool_setting(lockdown.stdout) if lockdown.returncode == 0 else None
        if wakefulness != "asleep":
            reason = "not_idle_screen_awake_or_unknown"
        elif always_on_configured is not False or lockdown_enabled is not False:
            reason = "existing_vpn_protection_present_or_unknown"
        else:
            reason = "idle_candidate"
        observations.append({
            "device_fingerprint": _fingerprint(serial), "model": device["model"], "adb_state": state,
            "wakefulness": wakefulness, "foreground_interactive": foreground_interactive,
            "always_on_configured": always_on_configured, "lockdown_enabled": lockdown_enabled,
            "eligible": reason == "idle_candidate", "reason": reason,
        })
    return observations


def select_one_idle_device(observations: list[dict[str, object]], *, checked_at: datetime | None = None) -> dict[str, object]:
    """Fail closed unless exactly one device is sleeping and has no protected VPN setting."""
    checked_at = checked_at or datetime.now(timezone.utc)
    eligible = [item for item in observations if item.get("eligible") is True]
    status = "selected" if len(eligible) == 1 else (
        "blocked_no_idle_device" if not eligible else "blocked_multiple_idle_devices"
    )
    selected = eligible[0]["device_fingerprint"] if status == "selected" else None
    return {
        "schema": SCHEMA,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "mutation_count": 0,
        "contains_serial": False,
        "contains_vpn_profile_name": False,
        "device_count": len(observations),
        "eligible_count": len(eligible),
        "status": status,
        "selected_device_fingerprint": selected,
        "devices": observations,
        "next_action": "manual_user_confirmation_then_test" if status == "selected" else "do_not_touch_any_phone",
    }


def write_new_json(path: pathlib.Path, payload: dict[str, object]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
