"""Claude subscription usage (Pro/Max) through the OAuth endpoint Claude Code itself uses."""

from __future__ import annotations

import contextlib
import json
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import config
from ..accounts import keychain_service
from ..config import HOME
from ..http import request_json
from ..i18n import tr
from ..keychain import read_secret
from ..models import ClaudeAccount, ProviderError, Usage, Window
from ..system import atomic_write_text
from . import parse_iso

URL = "https://api.anthropic.com/api/oauth/usage"


def _label(kind: str, model: str | None) -> str:
    if model:
        return tr("Weekly ({model})", model=model)
    return {"session": tr("Session (5h)"), "weekly_all": tr("Weekly (all models)")}.get(kind, kind)


def parse(data: dict[str, Any], plan: str = "?") -> Usage:
    windows: list[Window] = []
    for lim in data.get("limits") or []:
        model = ((lim.get("scope") or {}).get("model") or {}).get("display_name")
        windows.append(
            Window(
                label=_label(lim.get("kind", "?"), model),
                used=float(lim.get("percent") or 0),
                resets_at=parse_iso(lim.get("resets_at")),
                blocking=not model,  # one model's cap does not stop you using the others
            )
        )
    if not windows:  # older response without `limits`
        for key, kind in (("five_hour", "session"), ("seven_day", "weekly_all")):
            if w := data.get(key):
                used = float(w.get("utilization") or 0)
                windows.append(Window(_label(kind, None), used, parse_iso(w.get("resets_at"))))
    return Usage(plan, tuple(windows))


def credentials(account: ClaudeAccount) -> dict[str, Any] | None:
    raw = read_secret(keychain_service(account.config_dir))
    if not raw:
        path = (account.config_dir or HOME / ".claude") / ".credentials.json"
        raw = path.read_text(encoding="utf-8") if path.exists() else "{}"
    result: dict[str, Any] | None = json.loads(raw).get("claudeAiOauth")
    return result


def launch_command(account: ClaudeAccount) -> str:
    if account.config_dir is None:
        # `command` skips a `claude` shell function/alias (the `usage claude` one opens the selected account)
        return "claude" if sys.platform == "win32" else "command claude"
    return f"CLAUDE_CONFIG_DIR={str(account.config_dir).replace(str(HOME), '~')} claude"


def _last_file(account: ClaudeAccount) -> Path:
    return config.CONFIG_DIR / "last-usage" / (keychain_service(account.config_dir) + ".json")


def _idle(account: ClaudeAccount) -> Usage | None:
    """The last usage seen, for an account whose token expired because nobody has used it: Claude Code only renews
    the token while it runs, and an unused account's usage does not change. Windows that have reset since are 0%."""
    try:
        last = json.loads(_last_file(account).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    usage = parse(last["data"], plan=tr("{plan} · idle", plan=last["plan"]))
    now = datetime.now(UTC)
    return replace(
        usage,
        windows=tuple(w if w.resets_at is None or w.resets_at > now else replace(w, used=0.0) for w in usage.windows),
    )


def fetch(account: ClaudeAccount) -> Usage:
    creds = credentials(account)
    if not isinstance(creds, dict) or not isinstance(creds.get("accessToken"), str):
        raise ProviderError(tr("not signed in; open `{cmd}` and run /login", cmd=launch_command(account)))
    if (creds.get("expiresAt") or 0) / 1000 < time.time():
        if idle := _idle(account):
            return idle
        raise ProviderError(tr("token expired; open `{cmd}` to refresh it", cmd=launch_command(account)))
    headers = {"Authorization": "Bearer " + creds["accessToken"], "anthropic-beta": "oauth-2025-04-20"}
    data = request_json(URL, headers)
    plan = str(creds.get("subscriptionType", "?"))
    with contextlib.suppress(OSError):  # only a fallback: the fresh numbers are shown regardless
        atomic_write_text(_last_file(account), json.dumps({"plan": plan, "data": data}))
    return parse(data, plan=plan)
