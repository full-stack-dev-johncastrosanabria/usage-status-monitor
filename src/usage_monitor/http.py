"""Minimal HTTP client (stdlib) that turns failures into messages for the user."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from typing import Any

from .i18n import tr
from .models import ProviderError

USER_AGENT = "usage-monitor"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Requests carry credentials, and urllib would copy the Authorization header to wherever a redirect
    points. A redirect is therefore never followed: it surfaces as an HTTP error."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_opener = urllib.request.build_opener(_NoRedirect)


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
        with _opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ProviderError(f"HTTP {e.code} — {_hint(e.code, str(e.reason))}") from None
    except ValueError:  # 200 with a body that is not JSON (a captive portal, a maintenance page)
        raise ProviderError(tr("unexpected response from the server")) from None
    except (OSError, http.client.HTTPException) as e:  # URLError and timeouts are OSError
        raise ProviderError(tr("no connection ({reason})", reason=getattr(e, "reason", None) or e)) from None
