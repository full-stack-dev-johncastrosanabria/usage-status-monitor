from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from usage_monitor import connect

from .conftest import make_account


def fake_login(monkeypatch: pytest.MonkeyPatch, email: str | None) -> list[list[str]]:
    """Stands in for the browser sign-in: `claude auth login` writes the account's email, or nothing."""
    calls: list[list[str]] = []

    def run(cmd: list[str], env: dict[str, str] | None = None, **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[1:] == ["auth", "login"] and env and email:
            (Path(env["CLAUDE_CONFIG_DIR"]) / ".claude.json").write_text(
                json.dumps({"oauthAccount": {"emailAddress": email}})
            )
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(connect.shutil, "which", lambda name: "/bin/claude")
    monkeypatch.setattr(connect.subprocess, "run", run)
    return calls


Login = Callable[[str | None], list[list[str]]]


@pytest.fixture
def login(home: Path, monkeypatch: pytest.MonkeyPatch) -> Login:
    make_account(home, None, "main@x.com")
    (home / ".claude" / "CLAUDE.md").write_text("shared")
    return lambda email: fake_login(monkeypatch, email)


def test_connects_a_new_account_in_the_next_free_folder(home: Path, login: Login) -> None:
    make_account(home, ".claude-2", "two@x.com")
    calls = login("new@x.com")
    result = connect.run()
    assert result == connect.Result("connected", "new@x.com", 3)
    assert calls[0] == ["/bin/claude", "auth", "login"]
    new = home / ".claude-3"
    assert (new / "CLAUDE.md").resolve() == (home / ".claude" / "CLAUDE.md").resolve()  # synced
    assert oct(new.stat().st_mode & 0o777) == oct(0o700) or os.name == "nt"


def test_an_account_already_connected_is_not_added_twice(home: Path, login: Login) -> None:
    login("main@x.com")
    assert connect.run() == connect.Result("duplicate", "main@x.com", 1)
    assert not (home / ".claude-2").exists()


def test_a_cancelled_sign_in_leaves_nothing_behind(home: Path, login: Login) -> None:
    login(None)
    assert connect.run().status == "cancelled"
    assert not (home / ".claude-2").exists()


def test_without_claude_it_fails_cleanly(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connect.shutil, "which", lambda name: None)
    assert connect.run().status == "failed" and not (home / ".claude-2").exists()


def test_a_duplicate_is_found_even_when_the_new_folder_sorts_first(home: Path, login: Login) -> None:
    make_account(home, ".claude-3", "b@x.com")  # .claude-2 is free, and sorts before .claude-3
    login("b@x.com")
    assert connect.run() == connect.Result("duplicate", "b@x.com", 2)
    assert not (home / ".claude-2").exists()
