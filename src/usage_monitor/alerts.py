"""Alerts when usage crosses the threshold, the automatic switch, and notices for open sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .i18n import tr
from .models import AccountStatus, ClaudeAccount, Snapshot, Usage


@dataclass(frozen=True, slots=True)
class Alert:
    title: str
    message: str


def _roomy(best: AccountStatus | None, threshold: float) -> AccountStatus | None:
    """`best` only if switching to it helps: it must not be over the threshold itself."""
    return best if best and best.usage and best.usage.score > 100 - threshold else None


@dataclass(slots=True)
class AlertTracker:
    """Fires once when a window crosses the threshold and re-arms when usage drops again."""

    _flagged: set[tuple[str, str]] = field(default_factory=set)

    def check(self, snap: Snapshot, threshold: float) -> list[Alert]:
        """Watches the active Claude account, ChatGPT and every Antigravity model."""
        best = _roomy(snap.best(), threshold)
        tip = (
            tr("Switch to Claude #{n} ({free:.0f}% free).", n=best.account.number, free=best.usage.score)
            if best and best.usage
            else tr("No other account has room.")
        )
        watched: list[tuple[str, str, Usage, str]] = []
        if (cur := snap.current()) and cur.usage:
            watched.append((f"Claude #{cur.account.number}", cur.account.email, cur.usage, " " + tip))
        for name, usage in (("ChatGPT", snap.codex), ("Antigravity", snap.antigravity)):
            if isinstance(usage, Usage):
                watched.append((name, usage.plan, usage, ""))

        alerts = []
        for name, who, usage, hint in watched:
            for w in usage.windows:
                if not w.blocking:
                    continue
                key = (f"{name}|{who}", w.label)
                if w.used >= threshold and key not in self._flagged:
                    self._flagged.add(key)
                    title = tr("{name}: {label} at {used:.0f}%", name=name, label=w.label, used=w.used)
                    alerts.append(Alert(title, f"{who}.{hint}"))
                elif w.used < threshold:
                    self._flagged.discard(key)
        return alerts


def auto_switch(snap: Snapshot, threshold: float) -> tuple[AccountStatus, Alert] | None:
    """If the active account is over the threshold and another has room: (account to switch to, alert)."""
    cur, best = snap.current(), _roomy(snap.best(), threshold)
    if not (cur and cur.usage and best):
        return None
    hot = cur.usage.hottest(threshold)
    if hot is None:
        return None
    alert = Alert(
        tr("Switched to Claude #{n} automatically", n=best.account.number),
        tr(
            "{email}. #{old} reached {used:.0f}% of {label}; new sessions use #{n}.",
            email=best.account.email,
            old=cur.account.number,
            used=hot.used,
            label=hot.label,
            n=best.account.number,
        ),
    )
    return best, alert


def session_warning(payload: dict[str, Any], number: int) -> str | None:
    """Warning for account `number` built from the server's JSON, or None if it has room."""
    acc = next((c for c in payload.get("claude", []) if c["n"] == number), None)
    if acc is None:
        return None
    hot = [r for r in acc.get("rows", []) if r["blocking"] and r["used"] >= payload["alert_at"]]
    if not hot:
        return None
    worst = max(hot, key=lambda r: r["used"])
    best = next((c for c in payload["claude"] if c["n"] == payload.get("best") and c["n"] != number), None)
    tip = (
        tr("#{n} has {free:.0f}% free: run `usage switch` and start a new session.", n=best["n"], free=best["score"])
        if best and best["score"] > 100 - payload["alert_at"]
        else tr("No other account has room right now.")
    )
    head = tr(
        "Claude #{n} ({email}): {label} at {used:.0f}%.",
        n=number,
        email=acc["email"],
        label=worst["label"],
        used=worst["used"],
    )
    return f"{head} {tip}"


def switch_notice(mine: ClaudeAccount, chosen: ClaudeAccount, can_continue: bool) -> str:
    """Notice for an open session whose account is no longer the selected one."""
    how = (
        tr("exit and run `claude --continue` to carry on this conversation with #{n}", n=chosen.number)
        if can_continue
        else tr("new sessions will use it (run `usage sync` to continue conversations across accounts)")
    )
    return tr(
        "You switched to Claude #{n} ({email}). This session is still on #{mine} ({mine_email}): {how}.",
        n=chosen.number,
        email=chosen.email,
        mine=mine.number,
        mine_email=mine.email,
        how=how,
    )


REMIND_AFTER = 30 * 60  # the same notice is not repeated on every message


def should_show(state: dict[str, list[Any]], key: str, text: str, now: float) -> bool:
    """Records the notice in `state` and says whether it is due (new text, or enough time has passed)."""
    for k in [k for k, (_, ts) in state.items() if now - ts > 86400]:
        del state[k]  # old sessions
    last = state.get(key)
    if last and last[0] == text and now - last[1] < REMIND_AFTER:
        return False
    state[key] = [text, now]
    return True
