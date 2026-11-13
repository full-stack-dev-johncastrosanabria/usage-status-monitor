"""Connecting another Claude account: a new config folder signed in with `claude auth login`.

The browser does the sign-in; nothing here sees the password or the tokens.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import accounts, config, sync
from .system import QUIET

log = logging.getLogger(__name__)
LOGIN_TIMEOUT = 600  # seconds the browser sign-in may take


@dataclass(frozen=True, slots=True)
class Result:
    status: str  # "connected" | "duplicate" | "cancelled" | "failed"
    email: str | None = None
    number: int | None = None  # of the account it duplicates, or of the new one
    error: str | None = None


def next_dir() -> Path:
    """The first free ~/.claude-N (N from 2: ~/.claude is the first account)."""
    n = 2
    while (config.HOME / f".claude-{n}").exists():
        n += 1
    return config.HOME / f".claude-{n}"


def _forget(directory: Path) -> None:
    """Removes a folder this module created, and on macOS the Keychain entry Claude Code made for it."""
    shutil.rmtree(directory, ignore_errors=True)
    if sys.platform == "darwin":
        subprocess.run(
            ["security", "delete-generic-password", "-s", accounts.keychain_service(directory)],
            capture_output=True,
            check=False,
            timeout=15,
        )


def run(order: tuple[str, ...] = (), interactive: bool = False) -> Result:
    """Signs a new folder in. `interactive` lets `claude auth login` use the terminal (the CLI)."""
    if not (exe := shutil.which("claude")):
        return Result("failed", error="`claude` is not on the PATH")
    directory = next_dir()
    directory.mkdir(mode=0o700)
    env = os.environ | {"CLAUDE_CONFIG_DIR": str(directory)}
    quiet = {} if interactive else {"stdin": subprocess.DEVNULL, "capture_output": True, **QUIET}
    try:
        subprocess.run([exe, "auth", "login"], env=env, timeout=LOGIN_TIMEOUT, check=False, **quiet)
    except (OSError, subprocess.TimeoutExpired) as e:
        _forget(directory)
        return Result("failed", error=str(e))

    email = accounts.email_of(directory)
    if not email:  # the browser was closed, or the sign-in failed
        _forget(directory)
        return Result("cancelled")
    folders = [None, *(d for d in sorted(config.HOME.glob(".claude-*")) if d.is_dir() and d != directory)]
    if any(accounts.email_of(d) == email for d in folders):  # every folder: discover() keeps one per email
        _forget(directory)
        number = next((a.number for a in accounts.discover(order) if a.email == email), None)
        return Result("duplicate", email, number)
    try:
        sync.sync_account(directory)  # same CLAUDE.md, settings, plugins and shared conversations
    except (OSError, ValueError) as e:  # the account works anyway; `usage sync` can retry
        log.warning("could not sync %s: %s", directory, e)
    number = next((a.number for a in accounts.discover(order) if a.config_dir == directory), None)
    return Result("connected", email, number)
