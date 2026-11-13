"""Desktop integration on macOS, Linux and Windows: notifications, the panel window and start at login."""

from __future__ import annotations

import json
import logging
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import IO, Any

from .alerts import Alert
from .i18n import tr
from .system import QUIET, atomic_write_text

log = logging.getLogger(__name__)
LABEL = "dev.usage-monitor"
MAC_APP = "UsageMonitor.app"

# Windows PowerShell 5.1; the text arrives through environment variables so nothing is interpolated in the script.
_TOAST = (
    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]>$null;"
    "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
    "$n=$t.GetElementsByTagName('text');"
    "$n.Item(0).AppendChild($t.CreateTextNode($env:USAGE_MONITOR_TITLE))>$null;"
    "$n.Item(1).AppendChild($t.CreateTextNode($env:USAGE_MONITOR_MESSAGE))>$null;"
    "$id='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show("
    "[Windows.UI.Notifications.ToastNotification]::new($t))"
)


# ---------- notifications ----------


def notify_command(alert: Alert, platform: str = sys.platform) -> tuple[list[str], dict[str, str]]:
    """The command (and extra environment) that shows a native notification."""
    if platform == "darwin":
        # json.dumps yields a valid AppleScript string literal; ensure_ascii=False because it has no \uXXXX
        message, title = (json.dumps(s, ensure_ascii=False) for s in (alert.message, alert.title))
        script = f'display notification {message} with title {title} sound name "Glass"'
        return ["osascript", "-e", script], {}
    if platform == "win32":
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", _TOAST]
        return cmd, {"USAGE_MONITOR_TITLE": alert.title, "USAGE_MONITOR_MESSAGE": alert.message}
    return ["notify-send", "--app-name=usage-monitor", "--urgency=critical", "--", alert.title, alert.message], {}


def notify(alert: Alert) -> None:
    cmd, env = notify_command(alert)
    try:
        subprocess.run(cmd, env={**os.environ, **env}, capture_output=True, check=False, timeout=20, **QUIET)
    except (OSError, subprocess.TimeoutExpired) as e:  # no notify-send, no PowerShell…: the panel still shows it
        log.warning("could not notify (%s): %s", e, alert.title)


# ---------- processes and the panel window ----------


def spawn_detached(cmd: list[str], log_file: IO[Any] | None = None) -> None:
    """Starts a process that outlives the terminal that launched it."""
    out = log_file or subprocess.DEVNULL
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": out, "stderr": out}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def mac_app() -> Path | None:
    return next((p for d in (Path.home() / "Applications", Path("/Applications")) if (p := d / MAC_APP).exists()), None)


def chromium(platform: str = sys.platform) -> str | None:
    """A Chromium-based browser: it can open the panel as its own window (`--app=`)."""
    if platform == "win32":
        roots = [os.environ.get(v) for v in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        rels = ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe")
        found = (Path(root) / rel for root in roots if root for rel in rels)
        return next((str(p) for p in found if p.exists()), None)
    if platform == "darwin":
        apps = ("Google Chrome", "Microsoft Edge", "Brave Browser", "Chromium")
        found = (Path(f"/Applications/{a}.app/Contents/MacOS/{a}") for a in apps)
        return next((str(p) for p in found if p.exists()), None)
    names = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser")
    return next((p for n in names if (p := shutil.which(n))), None)


def open_panel(url: str) -> str:
    """Opens the panel and says where: the native app (macOS), its own window, or a browser tab."""
    if sys.platform == "darwin" and (app := mac_app()):
        subprocess.run(["open", "-a", str(app)], check=False)
        return tr("the app")
    if browser := chromium():
        spawn_detached([browser, f"--app={url}", "--window-size=1280,880"])
        return tr("its own window")
    webbrowser.open(url)
    return tr("the browser")


# ---------- start at login ----------


def autostart_entry(command: list[str], platform: str = sys.platform, home: Path | None = None) -> tuple[Path, str]:
    """The file (path and content) that makes `command` run when the user logs in."""
    home = home or Path.home()
    if platform == "darwin":
        plist = {"Label": LABEL, "ProgramArguments": command, "RunAtLoad": True}
        return home / "Library" / "LaunchAgents" / f"{LABEL}.plist", plistlib.dumps(plist).decode()
    if platform == "win32":
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup / "usage-monitor.cmd", f'@echo off\r\nstart "" {subprocess.list2cmdline(command)}\r\n'
    entry = (
        "[Desktop Entry]\nType=Application\nName=Usage Monitor\n"
        f"Exec={shlex.join(command)}\nX-GNOME-Autostart-enabled=true\n"
    )
    return home / ".config" / "autostart" / "usage-monitor.desktop", entry


def set_autostart(enabled: bool, command: list[str]) -> Path:
    path, content = autostart_entry(command)
    if enabled:
        atomic_write_text(path, content)
    else:
        path.unlink(missing_ok=True)
    return path
