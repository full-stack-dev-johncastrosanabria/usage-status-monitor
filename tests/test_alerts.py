from __future__ import annotations

from datetime import UTC, datetime

from usage_monitor.alerts import (
    REMIND_AFTER,
    AlertTracker,
    auto_switch,
    session_warning,
    should_show,
    switch_notice,
)
from usage_monitor.models import AccountStatus, ClaudeAccount, Snapshot, Usage, Window


def usage(session: float, model: float = 0) -> Usage:
    return Usage("pro", (Window("Session (5h)", session), Window("Weekly (Fable)", model, blocking=False)))


def snap(current_used: float, other_used: float = 20, codex_used: float = 10) -> Snapshot:
    return Snapshot(
        datetime.now(UTC),
        claude=[
            AccountStatus(ClaudeAccount(1, "a@x", None), usage(current_used, model=99), current=True),
            AccountStatus(ClaudeAccount(2, "b@x", None), usage(other_used)),
        ],
        codex=Usage("plus", (Window("Weekly", codex_used),)),
        antigravity="token expired",
    )


def test_alerts_only_blocking_windows_of_the_active_account() -> None:
    alerts = AlertTracker().check(snap(96, other_used=99), 95)
    assert len(alerts) == 1  # neither Fable's cap (99) nor the inactive account (99) alert
    assert alerts[0].title == "Claude #1: Session (5h) at 96%"
    assert alerts[0].message == "a@x. No other account has room."  # the other one is at 99%: not recommended


def test_alert_recommends_best_account_and_fires_once() -> None:
    tracker = AlertTracker()
    first = tracker.check(snap(96), 95)
    assert first[0].message == "a@x. Switch to Claude #2 (80% free)."
    assert tracker.check(snap(97), 95) == []  # not repeated while it stays above


def test_alert_rearms_after_dropping() -> None:
    tracker = AlertTracker()
    tracker.check(snap(96), 95)
    tracker.check(snap(5), 95)  # the window reset
    assert len(tracker.check(snap(98), 95)) == 1


def test_other_providers_alert_too() -> None:
    alerts = AlertTracker().check(snap(10, codex_used=95), 95)
    assert [a.title for a in alerts] == ["ChatGPT: Weekly at 95%"]


def test_best_ignores_current_failed_and_exhausted() -> None:
    s = snap(0, other_used=100)
    s.claude.append(AccountStatus(ClaudeAccount(3, "c@x", None), error="token expired"))
    assert s.best() is None
    s.claude.append(AccountStatus(ClaudeAccount(4, "d@x", None), usage(40)))
    best = s.best()
    assert best is not None and best.account.number == 4


def test_auto_switch_only_when_it_helps() -> None:
    assert auto_switch(snap(94), 95) is None  # still under the threshold
    assert auto_switch(snap(96, other_used=97), 95) is None  # the other account is no better
    target, alert = auto_switch(snap(96), 95) or (None, None)
    assert target is not None and target.account.number == 2
    assert alert is not None and alert.title == "Switched to Claude #2 automatically"
    assert alert.message == "b@x. #1 reached 96% of Session (5h); new sessions use #2."


def test_session_warning_for_the_session_account() -> None:
    def row(used: float, blocking: bool = True) -> dict[str, object]:
        return {"label": "Session (5h)", "used": used, "blocking": blocking}

    accounts = [
        {"n": 1, "email": "a@x", "rows": [row(97), row(99, blocking=False)], "score": 3},
        {"n": 2, "email": "b@x", "rows": [row(20)], "score": 80},
    ]
    payload: dict[str, object] = {"alert_at": 95, "best": 2, "claude": accounts}
    assert session_warning(payload, 1) == (
        "Claude #1 (a@x): Session (5h) at 97%. #2 has 80% free: run `usage switch` and start a new session."
    )
    assert session_warning(payload, 2) is None  # it has room
    assert session_warning(payload, 7) is None  # unknown account
    payload["best"] = None
    assert (session_warning(payload, 1) or "").endswith("No other account has room right now.")


def test_switch_notice_says_how_to_follow() -> None:
    mine, chosen = ClaudeAccount(1, "a@x", None), ClaudeAccount(3, "c@x", None)
    assert "`claude --continue`" in switch_notice(mine, chosen, can_continue=True)
    assert "`usage sync`" in switch_notice(mine, chosen, can_continue=False)


def test_should_show_throttles_per_session_and_prunes() -> None:
    state: dict[str, list[object]] = {"old": ["x", 0.0]}
    now = 200_000.0
    assert should_show(state, "s1", "notice", now) and "old" not in state
    assert not should_show(state, "s1", "notice", now + 60)
    assert should_show(state, "s1", "another notice", now + 61)  # new text: shown straight away
    assert should_show(state, "s2", "another notice", now + 62)  # another session
    assert should_show(state, "s1", "another notice", now + 61 + REMIND_AFTER + 1)
