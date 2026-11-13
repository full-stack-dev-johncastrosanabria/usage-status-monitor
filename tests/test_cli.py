from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from usage_monitor import accounts, cli
from usage_monitor.config import Config
from usage_monitor.models import ClaudeAccount

from .conftest import make_account


class FakeClaude:
    """Stands in for subprocess.Popen: `script(proc)` runs on every poll; setting `proc.code` ends the run."""

    def __init__(self, cmd: list[str], env: dict[str, str], script: Callable[[FakeClaude], None]) -> None:
        self.cmd, self.env, self.script = cmd, env, script
        self.code: int | None = None
        self.ticks = 0
        self.terminated_at: int | None = None

    def poll(self) -> int | None:
        if self.code is None:
            self.ticks += 1
            self.script(self)
        return self.code

    def terminate(self) -> None:
        self.terminated_at, self.code = self.ticks, -15

    kill = terminate

    def wait(self, timeout: float | None = None) -> int | None:
        return self.code


def fake_claude(monkeypatch: pytest.MonkeyPatch, *scripts: Callable[[FakeClaude], None]) -> list[FakeClaude]:
    """Each launch of `claude` runs the next script; returns the launches."""
    runs: list[FakeClaude] = []
    todo = iter(scripts)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/bin/claude" if name == "claude" else None)
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, env: runs.append(FakeClaude(cmd, env, next(todo))) or runs[-1])
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    return runs


def exits(code: int) -> Callable[[FakeClaude], None]:
    def script(proc: FakeClaude) -> None:
        proc.code = code

    return script


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    runs = fake_claude(monkeypatch, *[exits(7)] * 5)

    def last() -> None:
        seen.update(cmd=runs[-1].cmd, config_dir=runs[-1].env.get("CLAUDE_CONFIG_DIR"))

    seen["_refresh"] = last
    return seen


def test_claude_launcher_uses_the_selected_account(home: Path, launched: dict[str, Any]) -> None:
    d = make_account(home, ".claude-two", "two@x.com")
    accounts.set_current(ClaudeAccount(1, "two@x.com", d))
    assert cli.main(["claude", "--continue", "-p", "hello"]) == 7  # returns claude's exit code
    launched.pop("_refresh")()
    assert launched == {"cmd": ["/bin/claude", "--continue", "-p", "hello"], "config_dir": str(d)}


def test_claude_launcher_respects_explicit_env_and_default(
    home: Path, launched: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    cli.main(["claude"])
    launched["_refresh"]()
    assert launched["config_dir"] is None  # nothing selected: the default one
    d = make_account(home, ".claude-two", "two@x.com")
    accounts.set_current(ClaudeAccount(1, "two@x.com", d))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/other")
    cli.main(["claude"])
    launched["_refresh"]()
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


def hook(monkeypatch: pytest.MonkeyPatch, proc: FakeClaude, event: str) -> None:
    """What the plugin does inside the session: report it to the launcher that started it."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "abc-123", "hook_event_name": event})))
    monkeypatch.setenv(cli.LAUNCHER, proc.env[cli.LAUNCHER])
    cli.cmd_notice(argparse.Namespace(), Config(port=1))


def switch_to_b(home: Path) -> None:
    accounts.set_current(ClaudeAccount(2, "b@x", home / ".claude-b"))


def test_launcher_switches_between_replies(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def session(proc: FakeClaude) -> None:
        if proc.ticks == 1:
            hook(monkeypatch, proc, "UserPromptSubmit")  # Claude is answering…
        elif proc.ticks == 2:
            switch_to_b(home)  # …when the automatic switch happens
        elif proc.ticks == 4:
            hook(monkeypatch, proc, "Stop")  # the reply ends

    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr(cli, "_exhausted", lambda d: False)
    runs = fake_claude(monkeypatch, session, exits(0))
    accounts.set_current(ClaudeAccount(1, "a@x", home / ".claude-a"))

    assert cli.launch_claude(["--resume", "5d2e", "--chrome"]) == 0
    assert runs[0].terminated_at == 4  # right after the reply ended, not while it was answering
    assert [(r.cmd[1:], r.env["CLAUDE_CONFIG_DIR"]) for r in runs] == [
        (["--resume", "5d2e", "--chrome"], str(home / ".claude-a")),
        (["--resume", "abc-123", "--chrome"], str(home / ".claude-b")),
    ]


def test_launcher_resumes_a_reply_cut_short_by_exhaustion(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def session(proc: FakeClaude) -> None:
        if proc.ticks == 1:
            hook(monkeypatch, proc, "UserPromptSubmit")
            switch_to_b(home)  # no Stop ever comes: the account ran out mid-reply

    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setattr(cli, "_exhausted", lambda d: d == home / ".claude-a")
    runs = fake_claude(monkeypatch, session, exits(0))
    accounts.set_current(ClaudeAccount(1, "a@x", home / ".claude-a"))

    assert cli.launch_claude([]) == 0
    assert runs[1].cmd[1:] == ["--resume", "abc-123", cli.CONTINUE]


def test_launcher_leaves_a_pinned_folder_alone(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def session(proc: FakeClaude) -> None:
        switch_to_b(home)
        proc.code = 0 if proc.ticks == 3 else None

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / ".claude-a"))
    runs = fake_claude(monkeypatch, session)
    assert cli.launch_claude([]) == 0
    assert len(runs) == 1 and runs[0].terminated_at is None


def test_launcher_without_a_reported_session_starts_over(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def session(proc: FakeClaude) -> None:
        switch_to_b(home)  # still on a startup dialog: the hook has not reported any conversation

    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    runs = fake_claude(monkeypatch, session, exits(0))
    accounts.set_current(ClaudeAccount(1, "a@x", home / ".claude-a"))
    assert cli.launch_claude(["--chrome", "hola"]) == 0
    assert runs[1].cmd[1:] == ["--chrome", "hola"] and runs[1].env["CLAUDE_CONFIG_DIR"] == str(home / ".claude-b")


def test_reopen_args_keep_options_and_drop_the_prompt_and_the_session() -> None:
    args = ["--model", "haiku", "--resume", "5d2e", "--chrome", "-c", "--effort", "max", "Responde: hola"]
    assert cli._reopen_args(args) == ["--model", "haiku", "--chrome", "--effort", "max"]
    args = ["--disallowedTools", "Bash(rm:*)", "Edit", "-w", "feat", "--add-dir", "a", "b", "do it"]
    assert cli._reopen_args(args) == ["--disallowedTools", "Bash(rm:*)", "Edit", "-w", "feat", "--add-dir", "a", "b"]
    assert cli._reopen_args(["--resume", "5d2e"]) == [] and cli._reopen_args(["-w"]) == ["-w"]


def test_a_claude_run_inside_the_session_cannot_take_over_the_report(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(cli.LAUNCHER, "4242")
    launch = cli._launch_file()
    assert launch is not None

    def hook(sid: str, event: str, source: str | None = None) -> dict[str, object]:
        payload = {"session_id": sid, "hook_event_name": event, "source": source}
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        cli.cmd_notice(argparse.Namespace(), Config(port=1))
        return cli._launch_state(launch)

    assert hook("parent", "UserPromptSubmit") == {"session": "parent", "busy": True}
    assert hook("child", "SessionStart", "startup") == {"session": "parent", "busy": True}  # `claude -p` from Bash
    assert hook("child", "Stop") == {"session": "parent", "busy": True}
    assert hook("parent", "Stop") == {"session": "parent", "busy": False}
    assert hook("after-clear", "SessionStart", "clear") == {"session": "after-clear", "busy": False}
