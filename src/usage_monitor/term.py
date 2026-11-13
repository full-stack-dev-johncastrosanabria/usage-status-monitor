"""Terminal output: bars of % free with colour, and a countdown to each reset."""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from .i18n import tr
from .models import Credits, Snapshot, Usage

GREEN, YELLOW, RED, DIM, BOLD, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def _c(code: str) -> str:
    return code if sys.stdout.isatty() else ""


def countdown(dt: datetime | None, now: datetime | None = None) -> str:
    if not dt:
        return ""
    secs = max(0, int((dt - (now or datetime.now(UTC))).total_seconds()))
    d, h, m = secs // 86400, secs % 86400 // 3600, secs % 3600 // 60
    left = f"{d}d {h}h" if d else f"{h}h {m:02d}m"
    return tr("resets in {left} ({when})", left=left, when=f"{dt.astimezone():%a %d %H:%M}")


def bar(free: float, width: int = 20) -> str:
    filled = round(free / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _color(free: float) -> str:
    return _c(GREEN if free > 50 else YELLOW if free > 20 else RED)


def print_usage(title: str, usage: Usage | str | None, mark: str = "") -> None:
    if not isinstance(usage, Usage):
        print(f"{_c(BOLD)}{title}{_c(RESET)}: {usage or tr('no data')}{mark}\n")
        return
    print(f"{_c(BOLD)}{title}{_c(RESET)}  {_c(DIM)}({usage.plan}){_c(RESET)}{mark}")
    labels = [f"{w.group}: {w.label}" if w.group else w.label for w in usage.windows]
    pad = max([18, *map(len, labels)])
    for label, w in zip(labels, usage.windows, strict=True):
        free = tr("{free:5.1f}% free", free=w.free)
        print(f"  {label:<{pad}} {_color(w.free)}{bar(w.free)} {free}{_c(RESET)}   {countdown(w.resets_at)}")
    print()


def print_credits(title: str, balance: Credits | str | None) -> None:
    if not isinstance(balance, Credits):
        print(f"{_c(BOLD)}{title}{_c(RESET)}: {balance or tr('no data')}\n")
        return
    for b in balance.balances:
        warn = "" if balance.available else f"  {_c(RED)}{tr('(no balance)')}{_c(RESET)}"
        amount = tr("balance {amount:.2f} {currency}", amount=b.total, currency=b.currency)
        print(f"{_c(BOLD)}{title}{_c(RESET)}  {amount}{warn}")
    print()


def print_snapshot(snap: Snapshot, only_current: bool = False) -> None:
    if not only_current:
        print(tr("Available usage — {when}", when=f"{snap.updated.astimezone():%Y-%m-%d %H:%M:%S}") + "\n")
    for s in snap.claude:
        if only_current and not s.current:
            continue
        mark = f"   {_c(BOLD)}◀ {tr('active')}{_c(RESET)}" if s.current else ""
        print_usage(f"Claude #{s.account.number}  {s.account.email}", s.usage or s.error, mark)
    if only_current:
        return
    if not snap.claude:
        print(tr("Claude: no sessions; sign in with `claude`") + "\n")
    print_usage("ChatGPT / Codex", snap.codex)
    print_usage("Antigravity", snap.antigravity)
    print_credits("DeepSeek API", snap.deepseek)
