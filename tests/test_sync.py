from __future__ import annotations

import json
from pathlib import Path

from usage_monitor import sync


def test_sync_links_backs_up_and_is_idempotent(tmp_path: Path) -> None:
    main, acc = tmp_path / ".claude", tmp_path / ".claude-two"
    main.mkdir()
    acc.mkdir()
    (main / "CLAUDE.md").write_text("rules")
    (main / "settings.json").write_text('{"model": "opus"}')
    (main / "skills").mkdir()
    (main / "projects").mkdir()
    main_state = tmp_path / ".claude.json"
    main_state.write_text(json.dumps({"mcpServers": {"serena": {"command": "s"}, "mine": {"command": "main"}}}))
    (acc / "settings.json").write_text('{"theme": "dark"}')
    own = {"oauthAccount": {"emailAddress": "two@x"}, "mcpServers": {"mine": {"command": "own"}}}
    (acc / ".claude.json").write_text(json.dumps(own))

    done = sync.sync_account(acc, main, main_state)

    assert done == ["CLAUDE.md", "settings.json", "skills", "projects", "mcpServers: serena"]
    assert (acc / "settings.json").resolve() == (main / "settings.json").resolve()
    assert (acc / "CLAUDE.md").read_text() == "rules"
    backups = list(acc.glob("backup-sync-*"))
    assert len(backups) == 1 and (backups[0] / "settings.json").read_text() == '{"theme": "dark"}'
    state = json.loads((acc / ".claude.json").read_text())
    assert state["oauthAccount"] == {"emailAddress": "two@x"}  # the login is left alone
    assert state["mcpServers"] == {"mine": {"command": "own"}, "serena": {"command": "s"}}  # the account's own wins

    assert sync.sync_account(acc, main, main_state) == []


def test_sync_never_moves_existing_transcripts(tmp_path: Path) -> None:
    main, acc = tmp_path / ".claude", tmp_path / ".claude-two"
    (main / "projects").mkdir(parents=True)
    (acc / "projects" / "p").mkdir(parents=True)
    (tmp_path / ".claude.json").write_text("{}")
    (acc / ".claude.json").write_text("{}")

    done = sync.sync_account(acc, main, tmp_path / ".claude.json")

    assert done == ["projects: not linked (the account has its own history)"]
    assert (acc / "projects" / "p").is_dir() and not list(acc.glob("backup-sync-*"))


def test_shares_transcripts(home: Path) -> None:
    main, acc = home / ".claude", home / ".claude-two"
    (main / "projects").mkdir(parents=True)
    acc.mkdir()
    assert not sync.shares_transcripts(None, acc)
    (acc / "projects").symlink_to(main / "projects")
    assert sync.shares_transcripts(None, acc) and sync.shares_transcripts(acc, None)
