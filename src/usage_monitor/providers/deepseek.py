"""DeepSeek API balance (the key opencode stores, or DEEPSEEK_API_KEY)."""

from __future__ import annotations

import json
import os
from typing import Any

from ..config import HOME
from ..http import request_json
from ..i18n import tr
from ..models import Balance, Credits, ProviderError

URL = "https://api.deepseek.com/user/balance"
OPENCODE_AUTH = HOME / ".local" / "share" / "opencode" / "auth.json"


def parse(data: dict[str, Any]) -> Credits:
    balances = tuple(
        Balance(
            currency=b.get("currency", "?"),
            total=float(b.get("total_balance") or 0),
            granted=float(b.get("granted_balance") or 0),
            topped_up=float(b.get("topped_up_balance") or 0),
        )
        for b in data.get("balance_infos") or []
    )
    return Credits(bool(data.get("is_available")), balances)


def api_key() -> str | None:
    if key := os.environ.get("DEEPSEEK_API_KEY"):
        return key
    if OPENCODE_AUTH.exists():
        key = (json.loads(OPENCODE_AUTH.read_text(encoding="utf-8")).get("deepseek") or {}).get("key")
        return str(key) if key else None
    return None


def fetch() -> Credits:
    key = api_key()
    if not key:
        raise ProviderError(tr("no API key; add it with `opencode auth login` or DEEPSEEK_API_KEY"))
    return parse(request_json(URL, {"Authorization": "Bearer " + key, "Accept": "application/json"}))
