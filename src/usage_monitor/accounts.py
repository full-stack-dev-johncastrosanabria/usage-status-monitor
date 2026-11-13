"""Claude Code accounts: one per config folder (CLAUDE_CONFIG_DIR).

Everything here is local (no network): the email comes from each folder's `.claude.json`.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from . import config
from .models import ClaudeAccount
from .system import atomic_write_text


def _norm(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().absolute()


def session_dir() -> Path | None:
    """Folder of the Claude Code session running us (None = the default one, ~/.claude)."""
    return _norm(os.environ.get("CLAUDE_CONFIG_DIR"))


def selected_dir() -> Path | None:
    """The account chosen with `usage switch` or the panel (empty or missing file = ~/.claude)."""
    try:
        return _norm(config.active_file().read_text(encoding="utf-8").strip())
    except OSError:
        return None


def current_dir() -> Path | None:
    """An explicit CLAUDE_CONFIG_DIR wins; otherwise the selected account."""
    return session_dir() if os.environ.get("CLAUDE_CONFIG_DIR") else selected_dir()


def set_current(account: ClaudeAccount) -> None:
    atomic_write_text(config.active_file(), str(account.config_dir or ""))


def keychain_service(config_dir: Path | None) -> str:
    """Claude Code uses the bare service for the default folder and sha256(path)[:8] for the others."""
    if config_dir is None:
        return "Claude Code-credentials"
    return "Claude Code-credentials-" + hashlib.sha256(str(config_dir).encode()).hexdigest()[:8]


def _state_file(config_dir: Path | None) -> Path:
    return config.HOME / ".claude.json" if config_dir is None else config_dir / ".claude.json"


def email_of(config_dir: Path | None) -> str | None:
    try:
        data = json.loads(_state_file(config_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return (data.get("oauthAccount") or {}).get("emailAddress")


def discover(order: tuple[str, ...] = ()) -> list[ClaudeAccount]:
    """~/.claude plus every signed-in ~/.claude-*; deduplicated by email and numbered following `order`."""
    candidates: list[Path | None] = [None]
    candidates += sorted(p for p in config.HOME.glob(".claude-*") if p.is_dir())
    cur = current_dir()
    if cur and cur not in candidates:
        candidates.append(cur)

    by_email: dict[str, Path | None] = {}
    for d in candidates:
        email = email_of(d)
        if not email:
            continue
        if email not in by_email or d == cur:  # same account in two folders: the active one wins
            by_email[email] = d

    def rank(email: str) -> tuple[int, int]:
        pos = list(by_email).index(email)
        return (order.index(email), pos) if email in order else (len(order), pos)

    emails = sorted(by_email, key=rank)
    return [ClaudeAccount(i, e, by_email[e]) for i, e in enumerate(emails, 1)]


def is_current(account: ClaudeAccount) -> bool:
    return account.config_dir == current_dir()
