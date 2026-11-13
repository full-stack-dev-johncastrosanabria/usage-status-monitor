"""Canned data, for screenshots and for working on the interfaces on a machine with no accounts.

Enabled with USAGE_MONITOR_DEMO=1. Nothing is read from, or written to, the real accounts and settings.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import settings
from .models import AccountStatus, Balance, ClaudeAccount, Credits, Snapshot
from .providers import antigravity, claude, codex

ENABLED = bool(os.environ.get("USAGE_MONITOR_DEMO"))
_state = {"current": 1, "model": "opus", "effort": "high"}

# (email, session %, weekly %, weekly Fable %) — the first one is over the threshold on purpose
_ACCOUNTS = (
    ("ada@example.com", 96, 41, 12),
    ("grace@example.com", 8, 17, 34),
    ("linus@example.com", 52, 63, 27),
    ("margaret@example.com", 0, 88, 100),
)
_MODELS = (
    ("Gemini 3 Flash", "GOOGLE", 0.92),
    ("Gemini 2.5 Pro", "GOOGLE", 0.4),
    ("Claude Sonnet 4.6", "ANTHROPIC", 0.15),
    ("Claude Opus 4.6", "ANTHROPIC", 0.71),
    ("GPT-OSS 120B", "OPENAI", 1.0),
)


def _in(hours: float) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)


def snapshot() -> Snapshot:
    """Built through the real parsers, so labels follow the interface language."""
    statuses = []
    for n, (email, session, weekly, fable) in enumerate(_ACCOUNTS, 1):
        raw = {
            "limits": [
                {"kind": "session", "percent": session, "resets_at": _in(1.5 + n).isoformat()},
                {"kind": "weekly_all", "percent": weekly, "resets_at": _in(30 * n).isoformat()},
                {
                    "kind": "weekly_scoped",
                    "percent": fable,
                    "resets_at": _in(30 * n).isoformat(),
                    "scope": {"model": {"display_name": "Fable"}},
                },
            ]
        }
        account = ClaudeAccount(n, email, Path(f"demo-{n}"))
        statuses.append(AccountStatus(account, claude.parse(raw, plan="max"), current=n == _state["current"]))
    codex_usage = codex.parse(
        {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {"used_percent": 27, "limit_window_seconds": 18000, "reset_at": _in(3).timestamp()},
                "secondary_window": {
                    "used_percent": 61,
                    "limit_window_seconds": 604800,
                    "reset_at": _in(80).timestamp(),
                },
            },
        }
    )
    models = {
        name: {
            "displayName": name,
            "modelProvider": f"MODEL_PROVIDER_{vendor}",
            "quotaInfo": {"remainingFraction": left, "resetTime": _in(120).isoformat()},
        }
        for name, vendor, left in _MODELS
    }
    ag_usage = antigravity.parse({"models": models}, plan="ada@example.com · Google AI Pro")
    balance = Credits(True, (Balance("USD", 12.4, 2.0, 10.4),))
    return Snapshot(datetime.now(UTC), statuses, codex_usage, ag_usage, balance)


def select(number: int) -> None:
    _state["current"] = number


def settings_json() -> dict[str, Any]:
    base = settings._from_dict({"model": _state["model"], "effortLevel": _state["effort"]})
    return base.to_json()


def set_settings(model: str | None, effort: str | None) -> None:
    if model:
        _state["model"] = model
    if effort:
        _state["effort"] = effort
