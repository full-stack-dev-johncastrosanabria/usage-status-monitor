from __future__ import annotations

import sys
from pathlib import Path

import pytest

from usage_monitor import accounts
from usage_monitor.models import ClaudeAccount

from .conftest import make_account


def test_discover_orders_by_config_and_dedupes(home: Path) -> None:
    make_account(home, None, "main@x.com")
    make_account(home, ".claude-two", "two@x.com")
    make_account(home, ".claude-three", "main@x.com")  # the same account in another folder
    (home / ".claude-not-signed-in").mkdir()

    accs = accounts.discover(order=("two@x.com",))
    assert [(a.number, a.email) for a in accs] == [(1, "two@x.com"), (2, "main@x.com")]
    assert accs[1].config_dir is None  # the first folder wins when none is active


def test_duplicate_prefers_active_dir(home: Path) -> None:
    make_account(home, None, "main@x.com")
    dup = make_account(home, ".claude-three", "main@x.com")
    assert dup is not None
    accounts.set_current(ClaudeAccount(9, "main@x.com", dup))
    assert accounts.discover()[0].config_dir == dup


def test_current_and_switch(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = make_account(home, ".claude-two", "two@x.com")
    assert accounts.current_dir() is None
    accounts.set_current(ClaudeAccount(1, "two@x.com", d))
    assert accounts.current_dir() == d
    accounts.set_current(ClaudeAccount(2, "main@x.com", None))
    assert accounts.current_dir() is None  # an empty file means ~/.claude
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(d) + "/")  # an explicit environment wins
    assert accounts.current_dir() == d == accounts.session_dir()
    assert accounts.selected_dir() is None  # the selection does not depend on the environment


@pytest.mark.skipif(sys.platform == "win32", reason="the Keychain is macOS-only and the hash needs a POSIX path")
def test_keychain_service_names() -> None:
    assert accounts.keychain_service(None) == "Claude Code-credentials"
    # sha256 of the path, first 8 hex digits (checked against real Keychain entries)
    assert accounts.keychain_service(Path("/x")) == "Claude Code-credentials-b3d1db31"
