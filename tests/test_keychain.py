from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

from usage_monitor import keychain


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="secret\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_macos_uses_the_keychain(calls: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    assert keychain.read_secret("svc") == "secret"
    assert keychain.read_secret("svc", "account") == "secret"
    assert calls == [
        ["security", "find-generic-password", "-s", "svc", "-w"],
        ["security", "find-generic-password", "-s", "svc", "-a", "account", "-w"],
    ]


def test_linux_uses_secret_service(calls: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert keychain.read_secret("svc", "account") == "secret"
    assert calls == [["secret-tool", "lookup", "service", "svc", "username", "account"]]


def test_missing_tool_is_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_binary(*_: Any, **__: Any) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "run", no_binary)
    assert keychain.read_secret("svc") is None


def test_real_store_returns_none_for_an_unknown_entry() -> None:
    """No mocks: exercises each system's real store (on Windows, the CredReadW call)."""
    assert keychain.read_secret("usage-monitor-test-missing", "nobody") is None
