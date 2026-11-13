"""Shares ~/.claude's configuration with every ~/.claude-* account through symlinks.

Idempotent: what is already linked is skipped, and what an account had is moved to
<account>/backup-sync-<date>/ (never deleted). What belongs to each account (its login, its
history) is left alone; from its .claude.json only the user-level MCP servers are merged.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .config import HOME
from .i18n import tr

SHARED = ("CLAUDE.md", "settings.json", "settings.local.json", "agents", "skills", "hooks", "plugins", "commands")
# Conversations: sharing them is what lets `claude --continue` work under another account.
TRANSCRIPTS = "projects"


def sync_account(account_dir: Path, main: Path | None = None, main_state: Path | None = None) -> list[str]:
    main = main or HOME / ".claude"
    main_state = main_state or HOME / ".claude.json"
    backup = account_dir / f"backup-sync-{time.strftime('%Y%m%d-%H%M%S')}"
    done: list[str] = []

    for name in (*SHARED, TRANSCRIPTS):
        src, dst = main / name, account_dir / name
        if name == TRANSCRIPTS and dst.is_dir() and not dst.is_symlink() and any(dst.iterdir()):
            # existing conversation history is never moved
            done.append(tr("{name}: not linked (the account has its own history)", name=name))
            continue
        if not src.exists() or (dst.is_symlink() and dst.resolve() == src.resolve()):
            continue
        if dst.exists() or dst.is_symlink():
            backup.mkdir(exist_ok=True)
            shutil.move(dst, backup / name)
        dst.symlink_to(src)
        done.append(name)

    main_mcp = json.loads(main_state.read_text(encoding="utf-8")).get("mcpServers") or {}
    state_file = account_dir / ".claude.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    missing = {k: v for k, v in main_mcp.items() if k not in (data.get("mcpServers") or {})}
    if missing:
        backup.mkdir(exist_ok=True)
        shutil.copy2(state_file, backup / ".claude.json")
        data.setdefault("mcpServers", {}).update(missing)
        tmp = state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(state_file)
        done.append("mcpServers: " + ", ".join(missing))
    return done


def sync_all() -> dict[Path, list[str]]:
    return {d: sync_account(d) for d in sorted(HOME.glob(".claude-*")) if d.is_dir() and (d / ".claude.json").exists()}


def shares_transcripts(a: Path | None, b: Path | None) -> bool:
    """Do two account folders see the same conversations? (None = ~/.claude)"""
    pa, pb = ((d or HOME / ".claude") / TRANSCRIPTS for d in (a, b))
    return pa.exists() and pa.resolve() == pb.resolve()
