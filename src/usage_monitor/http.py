"""Minimal HTTP client (stdlib) that turns failures into messages for the user."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .i18n import tr
from .models import ProviderError

USER_AGENT = "usage-monitor"


def _hint(code: int, reason: str) -> str:
    hints = {
        401: tr("invalid token; open the tool once to refresh it"),
        403: tr("access denied"),
        429: tr("too many requests; wait a few minutes"),
    }
    return hints.get(code, reason)


def request_json(url: str, headers: dict[str, str], body: dict[str, Any] | None = None, timeout: float = 20) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"User-Agent": USER_AGENT, **headers}
    if data is not None:
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ProviderError(f"HTTP {e.code} — {_hint(e.code, str(e.reason))}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError(tr("no connection ({reason})", reason=getattr(e, "reason", e))) from None
