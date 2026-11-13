"""Pure logic of the GTK app; runs without GTK: `uv run pytest linux/tests`."""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from usage_monitor_gtk import logic

PANEL = Path(__file__).resolve().parents[2] / "src" / "usage_monitor" / "web" / "panel.html"


def test_every_language_has_the_same_keys() -> None:
    keys = {code: set(table) for code, table in logic.I18N.items()}
    assert set(keys) == {"en", "es", "zh"}
    assert keys["en"] == keys["es"] == keys["zh"]


def test_strings_match_the_web_panel() -> None:
    html = PANEL.read_text(encoding="utf-8")
    block = html[html.index("const I18N = {") : html.index("\n};\n")]
    for code, body in re.findall(r"^  (\w+): \{\n(.*?)^  \},", block, flags=re.S | re.M):
        panel = dict(re.findall(r'^    (\w+): "(.*)",$', body, flags=re.M))
        assert panel == logic.I18N[code], code


def test_tone_thresholds() -> None:
    assert [logic.tone(f) for f in (100, 51, 50, 21, 20, 0)] == ["ok", "ok", "warn", "warn", "bad", "bad"]


def test_countdown() -> None:
    now = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
    reset = now + timedelta(hours=2, minutes=29, seconds=30)
    text = logic.countdown(reset.isoformat(), "en", now)
    local = reset.astimezone()
    assert text == f"in 2h 29min · {logic.WEEKDAYS['en'][local.weekday()]} {local:%H:%M}"
    assert logic.countdown((now + timedelta(days=3, hours=5)).isoformat(), "es", now).startswith("en 3d 5h · ")
    assert logic.countdown((now + timedelta(minutes=7)).isoformat(), "zh", now).startswith("7分钟后 · ")
    assert logic.countdown((now - timedelta(hours=1)).isoformat(), "en", now).startswith("in 0min")
    assert logic.countdown(None, "en", now) == ""


def test_hot_row_only_for_the_active_blocking_row() -> None:
    row = {"label": "5-hour", "used": 96.0, "free": 4.0, "reset": None, "group": None, "blocking": True}
    minor = {**row, "label": "Fable", "used": 99.0, "blocking": False}
    data = {"alert_at": 95, "claude": [{"n": 1, "current": False, "rows": [row]}, {"n": 2, "current": True}]}
    assert logic.hot_row(data) is None
    data["claude"][1]["rows"] = [minor, row]
    assert logic.hot_row(data) == (data["claude"][1], row)


def test_limit_labels_keep_first_seen_order() -> None:
    accounts = [{"rows": [{"label": "a"}, {"label": "b"}]}, {"error": "x"}, {"rows": [{"label": "c"}, {"label": "a"}]}]
    assert logic.limit_labels(accounts) == ["a", "b", "c"]


def test_server_command_prefers_the_packaged_backend(tmp_path: Path) -> None:
    (tmp_path / "usage_monitor").mkdir()
    (tmp_path / "usage_monitor" / "__main__.py").touch()
    assert logic.server_command(tmp_path) == [sys.executable, "-m", "usage_monitor"]


def test_whole_rounds_half_up() -> None:
    assert [logic.whole(v) for v in (0.5, 1.5, 2.5, 2.49)] == [1, 2, 3, 2]


def test_connect_text() -> None:
    assert logic.connect_text(None, "en") == "" and logic.connect_text({"status": "idle"}, "en") == ""
    assert logic.connect_text({"status": "duplicate", "email": "a@x", "number": 2}, "es") == (
        "a@x ya está conectada como #2"
    )
