from __future__ import annotations

from datetime import UTC, datetime

from usage_monitor import i18n
from usage_monitor.models import Window
from usage_monitor.providers import antigravity, claude, codex, deepseek

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
