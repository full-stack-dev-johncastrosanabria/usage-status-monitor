from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from usage_monitor import i18n
from usage_monitor.models import ClaudeAccount, ProviderError, Window
from usage_monitor.providers import antigravity, claude, codex, copilot, deepseek

CLAUDE = {
    "limits": [
        {"kind": "session", "percent": 45, "resets_at": "2026-11-13T01:20:00.084796+00:00", "scope": None},
        {"kind": "weekly_all", "percent": 38, "resets_at": "2026-11-17T15:00:00+00:00", "scope": None},
        {
            "kind": "weekly_scoped",
            "percent": 90,
            "resets_at": "2026-11-17T15:00:00+00:00",
            "scope": {"model": {"display_name": "Fable"}},
        },
    ]
}


def test_claude_limits_and_blocking() -> None:
    u = claude.parse(CLAUDE, plan="pro")
    assert [(w.label, w.used, w.blocking) for w in u.windows] == [
        ("Session (5h)", 45, True),
        ("Weekly (all models)", 38, True),
        ("Weekly (Fable)", 90, False),
    ]
    assert u.windows[0].resets_at == datetime(2026, 11, 13, 1, 20, 0, 84796, UTC)
    assert u.score == 55  # Fable's cap (10% free) does not count: it does not block
    assert u.hottest(40) == u.windows[0] and u.hottest(46) is None


def test_claude_labels_follow_the_language() -> None:
    i18n.set_language("es")
    assert [w.label for w in claude.parse(CLAUDE).windows] == ["Sesión (5h)", "Semanal (todos)", "Semanal (Fable)"]


def test_claude_legacy_fields() -> None:
    u = claude.parse({"five_hour": {"utilization": 44.0, "resets_at": "2026-11-13T01:20:00+00:00"}})
    assert u.windows == (Window("Session (5h)", 44.0, datetime(2026, 11, 13, 1, 20, tzinfo=UTC)),)


def test_codex_windows() -> None:
    u = codex.parse(
        {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {"used_percent": 27, "limit_window_seconds": 18000, "reset_at": 1794534429},
                "secondary_window": {"used_percent": 26, "limit_window_seconds": 604800, "reset_at": 1794841276},
            },
        }
    )
    assert u.plan == "plus"
    assert [(w.label, w.used) for w in u.windows] == [("Session (5h)", 27), ("Weekly", 26)]
    assert u.windows[1].resets_at == datetime.fromtimestamp(1794841276, UTC)


def test_antigravity_missing_fraction_means_exhausted_and_dedupes() -> None:
    u = antigravity.parse(
        {
            "models": {
                "a": {
                    "displayName": "Gemini X",
                    "modelProvider": "MODEL_PROVIDER_GOOGLE",
                    "quotaInfo": {"remainingFraction": 0.8, "resetTime": "2026-11-20T02:38:10Z"},
                },
                "b": {
                    "displayName": "Gemini X",
                    "modelProvider": "MODEL_PROVIDER_GOOGLE",
                    "quotaInfo": {"remainingFraction": 0.3},
                },
                "c": {
                    "displayName": "Claude Y",
                    "modelProvider": "MODEL_PROVIDER_ANTHROPIC",
                    "quotaInfo": {"resetTime": "2026-11-20T02:38:10Z"},
                },
                "d": {"displayName": "Mystery", "modelProvider": "MODEL_PROVIDER_NEW", "quotaInfo": {}},
                "tab_internal": {"quotaInfo": {"remainingFraction": 1}},
                "no_quota": {"displayName": "No quota", "modelProvider": "MODEL_PROVIDER_OPENAI"},
            }
        }
    )
    assert [(w.label, round(w.used), w.group) for w in u.windows] == [
        ("Gemini X", 70, "Gemini"),
        ("Claude Y", 100, "Anthropic"),
        ("Mystery", 100, "Other"),
    ]
    assert u.windows[1].resets_at == datetime(2026, 11, 20, 2, 38, 10, tzinfo=UTC)


def test_deepseek_balance() -> None:
    c = deepseek.parse(
        {
            "is_available": True,
            "balance_infos": [
                {"currency": "USD", "total_balance": "5.33", "granted_balance": "0.00", "topped_up_balance": "5.33"}
            ],
        }
    )
    assert c.available and c.balances[0].total == 5.33 and c.balances[0].currency == "USD"


def test_copilot_premium_blocks_and_unlimited_is_skipped() -> None:
    u = copilot.parse(
        {
            "copilot_plan": "individual",
            "quota_reset_date": "2026-12-01",
            "quota_snapshots": {
                "premium_interactions": {"entitlement": 300, "percent_remaining": 20.0, "unlimited": False},
                "chat": {"unlimited": True},
                "completions": {"entitlement": 2000, "percent_remaining": 90.0, "unlimited": False},
            },
        }
    )
    assert u.plan == "individual"
    assert [(w.label, w.used, w.blocking) for w in u.windows] == [
        ("Premium requests", 80.0, True),
        ("Completions", 10.0, False),
    ]
    assert u.windows[0].resets_at == datetime(2026, 12, 1, tzinfo=UTC)


def test_copilot_all_unlimited_reports_it() -> None:
    u = copilot.parse({"copilot_plan": "business", "quota_snapshots": {"chat": {"unlimited": True}}})
    assert [(w.label, w.used) for w in u.windows] == [("Unlimited", 0.0)]


def test_copilot_token_from_apps_json_then_gh(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(copilot, "_gh_token", lambda: None)
    monkeypatch.setattr(copilot, "_config_dir", lambda: home / "github-copilot")  # same on every OS
    assert copilot.token() is None
    apps = home / "github-copilot" / "apps.json"
    apps.parent.mkdir(parents=True)
    apps.write_text(json.dumps({"github.com:Iv1.b507a08c87ecfe98": {"oauth_token": "gho_x"}}))
    assert copilot.token() == "gho_x"


def test_copilot_gh_not_logged_in_is_not_signed_in(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(copilot, "_gh_token", lambda: None)
    monkeypatch.setattr(copilot, "_config_dir", lambda: home / "github-copilot")
    with pytest.raises(ProviderError, match="not signed in"):
        copilot.fetch()


def test_claude_idle_account_shows_its_last_usage(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unused account's token expires, but its usage cannot change: the last numbers stand, resets applied."""
    acc = ClaudeAccount(1, "a@x", home / ".claude-2")
    creds = {"accessToken": "t", "expiresAt": (time.time() + 3600) * 1000, "subscriptionType": "pro"}
    monkeypatch.setattr(claude, "read_secret", lambda service: json.dumps({"claudeAiOauth": creds}))
    data = {
        "limits": [
            {"kind": "session", "percent": 40, "resets_at": "2000-01-01T00:00:00+00:00"},
            {"kind": "weekly_all", "percent": 22, "resets_at": "2999-01-01T00:00:00+00:00"},
        ]
    }
    monkeypatch.setattr(claude, "request_json", lambda url, headers: data)
    claude.fetch(acc)

    creds["expiresAt"] = 0
    idle = claude.fetch(acc)
    assert idle.plan == "pro · idle"
    assert [w.used for w in idle.windows] == [0.0, 22.0]  # the session window has reset since


def test_claude_expired_without_history_says_so(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        claude, "read_secret", lambda service: '{"claudeAiOauth": {"accessToken": "t", "expiresAt": 0}}'
    )
    with pytest.raises(ProviderError, match="expired"):
        claude.fetch(ClaudeAccount(1, "a@x", None))
