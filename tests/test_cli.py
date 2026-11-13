from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from usage_monitor import accounts, cli
from usage_monitor.config import Config
from usage_monitor.models import ClaudeAccount

from .conftest import make_account


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake_call(cmd: list[str], env: dict[str, str]) -> int:
        seen.update(cmd=cmd, config_dir=env.get("CLAUDE_CONFIG_DIR"))
        return 7

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/bin/claude" if name == "claude" else None)
    monkeypatch.setattr(subprocess, "call", fake_call)
    return seen


def test_claude_launcher_uses_the_selected_account(home: Path, launched: dict[str, Any]) -> None:
    d = make_account(home, ".claude-two", "two@x.com")
    accounts.set_current(ClaudeAccount(1, "two@x.com", d))
    assert cli.main(["claude", "--continue", "-p", "hello"]) == 7  # returns claude's exit code
    assert launched == {"cmd": ["/bin/claude", "--continue", "-p", "hello"], "config_dir": str(d)}


def test_claude_launcher_respects_explicit_env_and_default(
    home: Path, launched: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    cli.main(["claude"])
    assert launched["config_dir"] is None  # nothing selected: the default one
    d = make_account(home, ".claude-two", "two@x.com")
    accounts.set_current(ClaudeAccount(1, "two@x.com", d))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/other")
    cli.main(["claude"])
    assert launched["config_dir"] == "/other"


def test_hook_notices_account_switch_once_per_session(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_account(home, None, "main@x.com")
    d = make_account(home, ".claude-two", "two@x.com")
    accounts.set_current(ClaudeAccount(2, "two@x.com", d))  # the user switched; this session is still on ~/.claude
    monkeypatch.setattr(cli.sys, "stdin", __import__("io").StringIO(json.dumps({"session_id": "s1"})))

    assert cli.cmd_notice(None, Config(port=1)) == 0  # type: ignore[arg-type]
    message = json.loads(capsys.readouterr().out)["systemMessage"]
    assert "You switched to Claude #2 (two@x.com)" in message and "still on #1" in message

    monkeypatch.setattr(cli.sys, "stdin", __import__("io").StringIO(json.dumps({"session_id": "s1"})))
    cli.cmd_notice(None, Config(port=1))  # type: ignore[arg-type]
    assert capsys.readouterr().out == ""  # not repeated on every message


def test_hook_is_silent_when_session_matches_selection(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_account(home, None, "main@x.com")
    monkeypatch.setattr(cli.sys, "stdin", __import__("io").StringIO("not json"))
    assert cli.cmd_notice(None, Config(port=1)) == 0  # type: ignore[arg-type]
    assert capsys.readouterr().out == ""


def test_commands_speak_the_configured_language(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["switch", "9"]) == 1
    assert capsys.readouterr().out == "There is no account #9.\n"
    assert cli.main(["lang", "es"]) == 0
    capsys.readouterr()
    assert cli.main(["switch", "9"]) == 1
    assert capsys.readouterr().out == "No hay cuenta #9.\n"


def test_autoswitch_command_persists(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from usage_monitor import config

    assert cli.main(["autoswitch", "on"]) == 0 and config.load_config().auto_switch is True
    assert "on (at 95%" in capsys.readouterr().out
    assert cli.main(["autoswitch", "off"]) == 0 and config.load_config().auto_switch is False


def test_launcher_reopens_the_conversation_after_an_account_change(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs: list[tuple[list[str], str | None]] = []

    def fake_call(cmd: list[str], env: dict[str, str]) -> int:
        runs.append((cmd[1:], env.get("CLAUDE_CONFIG_DIR")))
        if len(runs) == 1:  # the hook records the session; the automatic switch happens while it runs
            monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "abc-123"}'))
            monkeypatch.setenv(cli.LAUNCHER, env[cli.LAUNCHER])
            cli.cmd_notice(argparse.Namespace(), Config())
            accounts.set_current(ClaudeAccount(2, "b@x", home / ".claude-b"))
        return 0

    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/bin/claude")
    monkeypatch.setattr(subprocess, "call", fake_call)
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    accounts.set_current(ClaudeAccount(1, "a@x", home / ".claude-a"))

    assert cli.launch_claude(["--resume", "5d2e", "--chrome"]) == 0
    assert runs == [
        (["--resume", "5d2e", "--chrome"], str(home / ".claude-a")),
        (["--resume", "abc-123", "--chrome"], str(home / ".claude-b")),
    ]
