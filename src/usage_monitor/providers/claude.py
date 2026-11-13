"""Claude subscription usage (Pro/Max) through the OAuth endpoint Claude Code itself uses."""

from __future__ import annotations

import json
import time
from typing import Any

from ..accounts import keychain_service
from ..config import HOME
from ..http import request_json
from ..i18n import tr
from ..keychain import read_secret
from ..models import ClaudeAccount, ProviderError, Usage, Window
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
        return "claude"
    return f"CLAUDE_CONFIG_DIR={str(account.config_dir).replace(str(HOME), '~')} claude"


def fetch(account: ClaudeAccount) -> Usage:
    creds = credentials(account)
    if not creds:
        raise ProviderError(tr("not signed in; open `{cmd}` and run /login", cmd=launch_command(account)))
    if creds.get("expiresAt", 0) / 1000 < time.time():
        raise ProviderError(tr("token expired; open `{cmd}` to refresh it", cmd=launch_command(account)))
    headers = {"Authorization": "Bearer " + creds["accessToken"], "anthropic-beta": "oauth-2025-04-20"}
    return parse(request_json(URL, headers), plan=str(creds.get("subscriptionType", "?")))
