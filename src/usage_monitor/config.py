"""User configuration and shared paths.

Personal data (emails, account order) lives in ~/.config/usage-monitor, never in the code.
config.toml is edited by hand; prefs.json is written by the panel and the CLI and takes precedence.
A mistake in either file must never take the program down: bad values fall back to the defaults.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .system import atomic_write_text

log = logging.getLogger(__name__)
HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("USAGE_MONITOR_HOME") or HOME / ".config" / "usage-monitor").expanduser()
_prefs_lock = threading.Lock()

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


def _toml() -> dict[str, Any]:
    path = config_file()
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:  # unreadable, not UTF-8, or not valid TOML
        log.warning("ignoring %s: %s", path, e)
        return {}


def _prefs() -> dict[str, Any]:
    try:
        data = json.loads(prefs_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _value[T](data: dict[str, Any], key: str, default: T, convert: Callable[[Any], T]) -> T:
    if key not in data:
        return default
    try:
        return convert(data[key])
    except (TypeError, ValueError):
        log.warning("ignoring %s = %r in the configuration (using %r)", key, data[key], default)
        return default


def _order(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):  # a single email written without the brackets
        return (value,)
    if not isinstance(value, list | tuple) or not all(isinstance(v, str) for v in value):
        raise TypeError
    return tuple(value)


def _flag(value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError
    return value


def load_config() -> Config:
    data = _toml() | _prefs()
    d = Config()
    return Config(
        claude_order=_value(data, "claude_order", d.claude_order, _order),
        alert_at=min(100.0, max(1.0, _value(data, "alert_at", d.alert_at, float))),
        port=_value(data, "port", d.port, int),
        # at least 60 s: the usage endpoints answer 429 when polled often
        refresh_seconds=max(60, _value(data, "refresh_seconds", d.refresh_seconds, int)),
        language=_value(data, "language", d.language, str),
        auto_switch=_value(data, "auto_switch", d.auto_switch, _flag),
    )


def save_prefs(**changes: Any) -> None:
    with _prefs_lock:  # read-modify-write: two requests must not lose each other's change
        atomic_write_text(prefs_file(), json.dumps(_prefs() | changes, indent=2))
