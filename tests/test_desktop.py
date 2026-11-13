from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from usage_monitor import desktop
from usage_monitor.alerts import Alert

ALERT = Alert('Claude #1: "Sesión" at 96%', "a@x. Switch to `the other`; $(rm -rf ~)")


def test_notifications_never_interpolate_text_into_a_shell() -> None:
    mac, _ = desktop.notify_command(ALERT, "darwin")
    assert (
        mac[:2] == ["osascript", "-e"] and '\\"Sesión\\" at 96%' in mac[2]
    )  # quotes escaped, accents kept: AppleScript has no \\uXXXX

    linux, _ = desktop.notify_command(ALERT, "linux")
    assert linux[0] == "notify-send" and linux[-3:] == ["--", ALERT.title, ALERT.message]

    win, env = desktop.notify_command(ALERT, "win32")
    assert win[0] == "powershell" and ALERT.message not in win[-1]
    assert env == {"USAGE_MONITOR_TITLE": ALERT.title, "USAGE_MONITOR_MESSAGE": ALERT.message}


def test_autostart_entry_per_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    cmd = ["/opt/my app/usage", "panel"]

    path, content = desktop.autostart_entry(cmd, "darwin", tmp_path)
    assert path == tmp_path / "Library" / "LaunchAgents" / "dev.usage-monitor.plist"
    assert plistlib.loads(content.encode()) == {
        "Label": "dev.usage-monitor",
        "ProgramArguments": cmd,
        "RunAtLoad": True,
    }

    path, content = desktop.autostart_entry(cmd, "linux", tmp_path)
    assert path == tmp_path / ".config" / "autostart" / "usage-monitor.desktop"
    assert "Exec='/opt/my app/usage' panel\n" in content

    path, content = desktop.autostart_entry(cmd, "win32", tmp_path)
    assert path.name == "usage-monitor.cmd" and "Startup" in path.parts
    assert 'start "" "/opt/my app/usage" panel' in content


def test_set_autostart_writes_and_removes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    path = desktop.set_autostart(True, ["usage", "panel"])
    assert path.is_file() and tmp_path in path.parents
    assert desktop.set_autostart(False, ["usage", "panel"]) == path and not path.exists()
    desktop.set_autostart(False, ["usage", "panel"])  # turning it off twice is fine


def test_chromium_lookup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)
    assert desktop.chromium("linux") == "/usr/bin/chromium"

    edge = tmp_path / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.touch()
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        monkeypatch.delenv(var, raising=False)
    assert desktop.chromium("win32") is None
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    assert desktop.chromium("win32") == str(edge)
