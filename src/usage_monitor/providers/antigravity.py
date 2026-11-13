"""Per-model quota of Google Antigravity (Gemini, Claude and GPT served by Google)."""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import time
from typing import Any

from ..config import HOME
from ..http import request_json
from ..i18n import tr
from ..keychain import read_secret
from ..models import ProviderError, Usage, Window
from . import parse_iso

BASE = "https://cloudcode-pa.googleapis.com/v1internal:"
AGY = HOME / ".gemini" / "bin" / "agy"
VENDORS = {
    "MODEL_PROVIDER_GOOGLE": "Gemini",
    "MODEL_PROVIDER_ANTHROPIC": "Anthropic",
    "MODEL_PROVIDER_OPENAI": "GPT",
}
_project: dict[str, str | None] = {}


def parse(data: dict[str, Any], plan: str = "Antigravity") -> Usage:
    """One row per visible name; internal models (no displayName) are dropped."""
    other = tr("Other")
    order = [*VENDORS.values(), other]
    best: dict[str, Window] = {}
    for m in (data.get("models") or {}).values():
        name, quota = m.get("displayName"), m.get("quotaInfo")
        if not name or quota is None:
            continue
        # proto3 omits zero values: a missing remainingFraction means exhausted, not full
        used = max(0.0, 100 - float(quota.get("remainingFraction", 0)) * 100)
        win = Window(name, used, parse_iso(quota.get("resetTime")), VENDORS.get(m.get("modelProvider"), other))
        if name not in best or win.used > best[name].used:  # several ids share a name: keep the most used
            best[name] = win
    rows = sorted(best.values(), key=lambda w: (order.index(w.group or other), w.label))
    return Usage(plan, tuple(rows))


def _session() -> dict[str, Any]:
    raw = read_secret("gemini", "antigravity")
    if not raw:
        raise ProviderError(tr("not signed in; open `agy` and sign in"))
    try:
        # go-keyring stores base64 on macOS and the plain JSON on Linux and Windows
        text = base64.b64decode(raw.split(":", 1)[1]) if raw.startswith("go-keyring-base64:") else raw
        session: dict[str, Any] = json.loads(text)
        session["token"]["access_token"]  # check the minimum shape
    except (ValueError, KeyError, TypeError):
        raise ProviderError(tr("cannot read the session saved by `agy`")) from None
    return session


def _expired(session: dict[str, Any]) -> bool:
    expiry = parse_iso(session["token"].get("expiry"))
    return expiry is None or expiry.timestamp() < time.time() + 60


def _token() -> tuple[str, str]:
    session = _session()
    if _expired(session) and AGY.exists():
        # agy renews its own token when it runs, so we never touch the refresh token
        subprocess.run(
            [str(AGY), "models"],
            cwd=tempfile.gettempdir(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
            check=False,
        )
        session = _session()
    if _expired(session):
        raise ProviderError(tr("token expired; open `agy` to refresh it"))
    return session["token"]["access_token"], session.get("id_token_email", "?")


def fetch() -> Usage:
    token, email = _token()
    headers = {"Authorization": "Bearer " + token, "User-Agent": "antigravity"}
    if "project" not in _project:
        info = request_json(BASE + "loadCodeAssist", headers, {"metadata": {"ideType": "ANTIGRAVITY"}})
        tier = info.get("paidTier") or info.get("currentTier") or {}
        _project.update(project=info.get("cloudaicompanionProject"), tier=tier.get("name", "?"))
    body = {"project": _project["project"]} if _project["project"] else {}
    return parse(request_json(BASE + "fetchAvailableModels", headers, body), plan=f"{email} · {_project['tier']}")
