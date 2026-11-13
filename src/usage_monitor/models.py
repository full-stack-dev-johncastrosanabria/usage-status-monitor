"""Domain types shared by the providers, the server and every interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class ProviderError(Exception):
    """A provider failure whose message is fit to show to the user."""


@dataclass(frozen=True, slots=True)
class Window:
    """One usage limit window (5-hour session, weekly, a model's quota…)."""

    label: str
    used: float  # % used, 0-100
    resets_at: datetime | None = None
    group: str | None = None  # visual grouping (the model's vendor in Antigravity)
    blocking: bool = True  # running out blocks all use (Claude's per-model caps do not)

    @property
    def free(self) -> float:
        return max(0.0, 100.0 - self.used)

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "used": self.used,
            "free": self.free,
            "reset": self.resets_at.isoformat() if self.resets_at else None,
            "group": self.group,
            "blocking": self.blocking,
        }


@dataclass(frozen=True, slots=True)
class Usage:
    plan: str
    windows: tuple[Window, ...]

    @property
    def score(self) -> float:
        """% free in the tightest blocking window: how much room is really left."""
        vals = [w.free for w in self.windows if w.blocking]
        return min(vals) if vals else 0.0

    def hottest(self, threshold: float) -> Window | None:
        """The most used blocking window at or above `threshold`, if any."""
        hot = [w for w in self.windows if w.blocking and w.used >= threshold]
        return max(hot, key=lambda w: w.used) if hot else None


@dataclass(frozen=True, slots=True)
class Balance:
    currency: str
    total: float
    granted: float
    topped_up: float


@dataclass(frozen=True, slots=True)
class Credits:
    """Prepaid API balance (money, not a percentage)."""

    available: bool
    balances: tuple[Balance, ...]


@dataclass(frozen=True, slots=True)
class ClaudeAccount:
    number: int
    email: str
    config_dir: Path | None  # None = the default folder (~/.claude, no CLAUDE_CONFIG_DIR)


@dataclass(slots=True)
class AccountStatus:
    account: ClaudeAccount
    usage: Usage | None = None
    error: str | None = None
    current: bool = False


@dataclass(slots=True)
class Snapshot:
    """Everything at one point in time; what the CLI, the panel and the app consume."""

    updated: datetime
    claude: list[AccountStatus] = field(default_factory=list)
    codex: Usage | str | None = None
    antigravity: Usage | str | None = None
    deepseek: Credits | str | None = None
    copilot: Usage | str | None = None

    def best(self) -> AccountStatus | None:
        """The non-active Claude account with the most room, or None if none has any."""
        ok = [s for s in self.claude if not s.current and s.usage and s.usage.score > 0]
        return max(ok, key=lambda s: s.usage.score if s.usage else 0) if ok else None

    def current(self) -> AccountStatus | None:
        return next((s for s in self.claude if s.current), None)
