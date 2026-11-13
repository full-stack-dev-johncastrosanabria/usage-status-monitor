"""User configuration and shared paths.

Personal data (emails, account order) lives in ~/.config/usage-monitor, never in the code.
config.toml is edited by hand; prefs.json is written by the panel and the CLI and takes precedence.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("USAGE_MONITOR_HOME", HOME / ".config" / "usage-monitor"))

EXAMPLE = """\
# Order of the Claude accounts (by email); unlisted ones go last.
claude_order = []

# % used that triggers an alert (and the automatic switch).
alert_at = 95

# Local port of the panel, and how often usage is fetched (seconds, minimum 60).
port = 8787
refresh_seconds = 300

# Interface language: "en", "es" or "zh". Also: `usage lang es`.
language = "en"

# Move to the account with the most room when the active one reaches alert_at. Also: `usage autoswitch on`.
auto_switch = false
"""


def config_file() -> Path:
    return CONFIG_DIR / "config.toml"


def prefs_file() -> Path:
    return CONFIG_DIR / "prefs.json"


def active_file() -> Path:
    """The selected Claude Code config folder; shells read it too (empty = ~/.claude)."""
    return CONFIG_DIR / "active_claude_dir"


@dataclass(frozen=True, slots=True)
class Config:
    claude_order: tuple[str, ...] = ()
    alert_at: float = 95.0
    port: int = 8787
    refresh_seconds: int = 300
    language: str = "en"
    auto_switch: bool = False


def _prefs() -> dict[str, Any]:
    try:
        data = json.loads(prefs_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config() -> Config:
    path = config_file()
    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data |= _prefs()
    return Config(
        claude_order=tuple(data.get("claude_order", ())),
        alert_at=float(data.get("alert_at", 95)),
        port=int(data.get("port", 8787)),
        # at least 60 s: the usage endpoints answer 429 when polled often
        refresh_seconds=max(60, int(data.get("refresh_seconds", 300))),
        language=str(data.get("language", "en")),
        auto_switch=bool(data.get("auto_switch", False)),
    )


def save_prefs(**changes: Any) -> None:
    path = prefs_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_prefs() | changes, indent=2), encoding="utf-8")
    tmp.replace(path)
