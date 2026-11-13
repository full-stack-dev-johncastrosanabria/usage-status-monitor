"""GitHub Copilot monthly quotas, with the token the Copilot extensions or `gh` already store."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import config
from ..http import request_json
from ..i18n import tr
from ..models import ProviderError, Usage, Window
from ..system import QUIET

URL = "https://api.github.com/copilot_internal/user"  # what the official extensions call; undocumented
BLOCKING = "premium_interactions"  # the scarce monthly allowance; chat and completions only inform


def _config_dir() -> Path:
    if sys.platform == "win32" and (local := os.environ.get("LOCALAPPDATA")):
        return Path(local) / "github-copilot"
    return config.HOME / ".config" / "github-copilot"


def _gh_token() -> str | None:
    if not (gh := shutil.which("gh")):
        return None
    try:
        out = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, timeout=10, check=False, **QUIET)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (out.stdout.strip() or None) if out.returncode == 0 else None


def token() -> str | None:
    for name in ("apps.json", "hosts.json"):
        try:
            data = json.loads((_config_dir() / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in data.values() if isinstance(data, dict) else ():
            if isinstance(entry, dict) and isinstance(t := entry.get("oauth_token"), str) and t:
                return t
    return _gh_token()


def _reset(value: Any) -> datetime | None:
    """GitHub sends a bare date (2026-12-01), read as midnight UTC."""
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC) if isinstance(value, str) else None
    except ValueError:
        return None


def parse(data: dict[str, Any]) -> Usage:
    snaps = data.get("quota_snapshots") or {}
    resets = _reset(data.get("quota_reset_date"))
    labels = {"premium_interactions": tr("Premium requests"), "chat": tr("Chat"), "completions": tr("Completions")}
    windows = tuple(
        Window(label, 100.0 - float(q.get("percent_remaining") or 0), resets, blocking=key == BLOCKING)
        for key, label in labels.items()
        if isinstance(q := snaps.get(key), dict) and not q.get("unlimited")
    )
    return Usage(str(data.get("copilot_plan", "?")), windows or (Window(tr("Unlimited"), 0.0, None, blocking=False),))


def fetch() -> Usage:
    if not (t := token()):
        raise ProviderError(tr("not signed in; run `gh auth login` or sign in to Copilot in your editor"))
    data = request_json(URL, {"Authorization": "token " + t, "Accept": "application/json"})
    if not isinstance(data, dict):
        raise ProviderError(tr("unexpected response from the server"))
    return parse(data)
