"""Usage providers: each module exposes `fetch()` and a pure, testable `parse()`.

They only read credentials. They never refresh a token themselves: refresh tokens rotate, and
that would sign out the tool that owns the session.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def from_epoch(value: float | None) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None
