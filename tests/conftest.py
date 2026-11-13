from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from usage_monitor import config, i18n, sync


@pytest.fixture(autouse=True)
def english() -> Iterator[None]:
    """Tests assert on the English text; whatever a test changes is undone."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated HOME: nothing a test does touches the real configuration."""
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".config" / "usage-monitor")
    monkeypatch.setattr(sync, "HOME", tmp_path)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return tmp_path


def make_account(home: Path, name: str | None, email: str) -> Path | None:
    """Creates a signed-in Claude Code folder (None = the main one, ~/.claude)."""
    state = json.dumps({"oauthAccount": {"emailAddress": email}})
    if name is None:
        (home / ".claude").mkdir(exist_ok=True)
        (home / ".claude.json").write_text(state)
        return None
    d = home / name
    d.mkdir()
    (d / ".claude.json").write_text(state)
    return d
