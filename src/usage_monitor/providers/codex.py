"""ChatGPT plan usage (Plus/Pro) with the token Codex CLI stores."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..config import HOME
from ..http import request_json
from ..i18n import tr
from ..models import ProviderError, Usage, Window
from . import from_epoch

URL = "https://chatgpt.com/backend-api/wham/usage"
FIVE_HOURS, ONE_WEEK = 5 * 3600, 7 * 24 * 3600


def _label(seconds: int) -> str:
    if seconds <= FIVE_HOURS:
        return tr("Session (5h)")
    if seconds >= ONE_WEEK:
        return tr("Weekly")
    return tr("{hours}h window", hours=seconds // 3600)


def parse(data: dict[str, Any]) -> Usage:
    rl = data.get("rate_limit") or {}
    windows = tuple(
        Window(
            _label(w.get("limit_window_seconds") or 0),
            float(w.get("used_percent") or 0),
            from_epoch(w.get("reset_at")),
        )
        for key in ("primary_window", "secondary_window")
        if (w := rl.get(key))
    )
    return Usage(str(data.get("plan_type", "?")), windows)


def fetch() -> Usage:
    path = Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "auth.json"
    if not path.exists():
        raise ProviderError(tr("not signed in; run `codex login`"))
    tokens = json.loads(path.read_text(encoding="utf-8")).get("tokens") or {}
    if not tokens.get("access_token"):
        raise ProviderError(tr("Codex uses an API key, not a ChatGPT login: there are no plan limits"))
    headers = {"Authorization": "Bearer " + tokens["access_token"], "ChatGPT-Account-Id": tokens.get("account_id", "")}
    return parse(request_json(URL, headers))
