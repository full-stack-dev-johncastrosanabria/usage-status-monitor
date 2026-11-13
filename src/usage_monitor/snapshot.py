"""Collects every provider in parallel and serialises the result for the interfaces."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from typing import Any

from . import accounts, demo, i18n, settings
from .config import Config
from .i18n import tr
from .models import AccountStatus, ClaudeAccount, Credits, ProviderError, Snapshot, Usage
from .providers import antigravity, claude, codex, deepseek

log = logging.getLogger(__name__)


def _safe[T](fn: Callable[[], T]) -> T | str:
    """One source being down must never hide the others."""
    try:
        return fn()
    except ProviderError as e:
        return str(e)
    except Exception as e:  # any failure of a source is shown, not raised
        log.exception("a provider failed unexpectedly")
        return tr("unexpected error: {error}", error=f"{type(e).__name__}: {e}")


def _status(acc: ClaudeAccount, res: Usage | str, current: bool) -> AccountStatus:
    return AccountStatus(
        acc,
        usage=res if isinstance(res, Usage) else None,
        error=res if isinstance(res, str) else None,
        current=current,
    )


def collect_current(cfg: Config) -> Snapshot:
    """Only the active Claude account (a single request): for `usage current`."""
    accs = [a for a in accounts.discover(cfg.claude_order) if accounts.is_current(a)]
    statuses = [_status(a, _safe(partial(claude.fetch, a)), current=True) for a in accs]
    return Snapshot(datetime.now(UTC), statuses)


def collect(cfg: Config) -> Snapshot:
    if demo.ENABLED:
        return demo.snapshot()
    accs = accounts.discover(cfg.claude_order)
    current = accounts.current_dir()
    with ThreadPoolExecutor(max_workers=len(accs) + 3) as pool:
        claude_jobs = [(a, pool.submit(_safe, partial(claude.fetch, a))) for a in accs]
        codex_job = pool.submit(_safe, codex.fetch)
        ag_job = pool.submit(_safe, antigravity.fetch)
        ds_job = pool.submit(_safe, deepseek.fetch)
        statuses = [_status(acc, job.result(), acc.config_dir == current) for acc, job in claude_jobs]
        return Snapshot(datetime.now(UTC), statuses, codex_job.result(), ag_job.result(), ds_job.result())


def _usage_json(u: Usage | str | None) -> dict[str, Any]:
    if isinstance(u, Usage):
        return {"plan": u.plan, "rows": [w.to_json() for w in u.windows], "score": u.score}
    return {"error": u or tr("no data")}


def _credits_json(c: Credits | str | None) -> dict[str, Any]:
    if isinstance(c, Credits):
        return {
            "available": c.available,
            "balances": [
                {"currency": b.currency, "total": b.total, "granted": b.granted, "topped_up": b.topped_up}
                for b in c.balances
            ],
        }
    return {"error": c or tr("no data")}


def to_json(snap: Snapshot, cfg: Config) -> dict[str, Any]:
    best = snap.best()
    claude_items = []
    for s in snap.claude:
        item: dict[str, Any] = {"n": s.account.number, "email": s.account.email, "current": s.current}
        item.update(_usage_json(s.usage if s.usage else s.error))
        claude_items.append(item)
    try:
        # read every time: /model changes it too
        cfg_settings: dict[str, Any] = demo.settings_json() if demo.ENABLED else settings.read().to_json()
    except (OSError, ValueError, AttributeError) as e:  # missing, not JSON, or not an object
        cfg_settings = {"error": str(e)}
    return {
        "updated": snap.updated.isoformat(),
        "claude": claude_items,
        "codex": _usage_json(snap.codex),
        "antigravity": _usage_json(snap.antigravity),
        "deepseek": _credits_json(snap.deepseek),
        "best": best.account.number if best else None,
        "alert_at": cfg.alert_at,
        "every": cfg.refresh_seconds,
        "settings": cfg_settings,
        "auto_switch": cfg.auto_switch,
        "lang": i18n.language(),
        "demo": demo.ENABLED,
        "languages": i18n.LANGUAGES,
    }
