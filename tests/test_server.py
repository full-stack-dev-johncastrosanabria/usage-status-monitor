from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from usage_monitor import accounts, config, connect, demo, server, settings, snapshot
from usage_monitor.alerts import Alert
from usage_monitor.config import Config
from usage_monitor.models import AccountStatus, ClaudeAccount, Snapshot, Usage, Window

Api = Callable[..., tuple[int, Any]]


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[Alert]:
    alerts: list[Alert] = []
    monkeypatch.setattr(server, "notify", alerts.append)
    return alerts


@pytest.fixture
def api(home: Path, sent: list[Alert], monkeypatch: pytest.MonkeyPatch) -> Iterator[Api]:
    """A real server on a free port, with a fixed Snapshot (no network) and a temporary settings.json."""
    settings_path = home / "settings.json"
    settings_path.write_text(json.dumps({"model": "opus", "effortLevel": "high"}))
    monkeypatch.setattr(settings, "SETTINGS", settings_path)

    def fake_collect(_: Config) -> Snapshot:
        def mk(n: int, used: float) -> AccountStatus:
            acc = ClaudeAccount(n, f"c{n}@x", home / f".claude-c{n}")
            usage = Usage("pro", (Window("Session (5h)", used),))
            return AccountStatus(acc, usage, current=acc.config_dir == accounts.selected_dir())

        return Snapshot(
            datetime.now(UTC),
            [mk(1, 97), mk(2, 40), mk(3, 10)],
            "not signed in",
            "not signed in",
            "no key",
            "not signed in",
        )

    monkeypatch.setattr(server, "collect", fake_collect)
    accounts.set_current(ClaudeAccount(1, "c1@x", home / ".claude-c1"))

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.BaseHTTPRequestHandler)
    port = httpd.server_address[1]
    httpd.RequestHandlerClass = server.make_handler(server.Monitor(port))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(path: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> tuple[int, Any]:
        hdrs = {server.HEADER: "1"} if headers is None else headers
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    yield call
    httpd.shutdown()


def test_data_reports_best_account_and_settings(api: Api, sent: list[Alert]) -> None:
    status, d = api("/api/data")
    assert status == 200 and d["best"] == 3
    assert [c["current"] for c in d["claude"]] == [True, False, False]
    assert d["settings"]["model"] == "opus" and d["codex"] == {"error": "not signed in"}
    assert d["copilot"] == {"error": "not signed in"}
    assert (d["lang"], d["auto_switch"]) == ("en", False)
    assert [a.title for a in sent] == ["Claude #1: Session (5h) at 97%"]


def test_switch_to_best_and_to_explicit_account(api: Api, home: Path) -> None:
    _, d = api("/api/switch", {})
    assert [c["n"] for c in d["claude"] if c["current"]] == [3]
    assert accounts.current_dir() == home / ".claude-c3"
    _, d = api("/api/switch", {"n": 2})
    assert [c["n"] for c in d["claude"] if c["current"]] == [2] and d["best"] == 3
    assert api("/api/switch", {"n": 99}) == (400, {"error": "There is no account #99."})


def test_settings_endpoint_validates(api: Api) -> None:
    assert api("/api/settings", {"effort": "turbo"}) == (400, {"error": "unknown effort: turbo"})
    status, d = api("/api/settings", {"effort": "max", "model": "sonnet"})
    assert status == 200 and (d["settings"]["model"], d["settings"]["effort"]) == ("sonnet", "max")


def test_language_preference_is_saved_and_relabels(api: Api) -> None:
    assert api("/api/prefs", {"language": "xx"})[0] == 400
    _, d = api("/api/prefs", {"language": "es"})
    assert d["lang"] == "es" and config.load_config().language == "es"
    assert d["settings"]["models"][0]["label"] == "Por defecto"
    assert api("/api/switch", {"n": 99})[1] == {"error": "No hay cuenta #99."}


def test_auto_switch_moves_to_the_best_account_and_notifies(api: Api, home: Path, sent: list[Alert]) -> None:
    api("/api/data")
    sent.clear()
    _, d = api("/api/prefs", {"auto_switch": True})
    assert d["auto_switch"] is True and accounts.selected_dir() == home / ".claude-c1"  # applies on the next fetch

    monitor_refresh = api("/api/prefs", {"language": "zh"})  # a language change fetches again
    assert monitor_refresh[0] == 200
    assert accounts.selected_dir() == home / ".claude-c3"
    assert len(sent) == 1 and "#3" in sent[0].title


def test_rejects_cross_site_requests(api: Api) -> None:
    assert api("/api/switch", {}, headers={})[0] == 403  # without the custom header
    assert api("/api/data", headers={"Host": "evil.example"})[0] == 403  # DNS rebinding
    assert api("/api/nothing", {})[0] == 404


def test_demo_mode_never_touches_real_accounts_or_settings(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo, "ENABLED", True)
    monkeypatch.setattr(demo, "_state", {"current": 1, "model": "opus", "effort": "high"})
    monkeypatch.setattr(server, "notify", lambda alert: None)
    monitor = server.Monitor(port=1)

    payload = monitor.payload()
    assert payload["demo"] is True and [c["current"] for c in payload["claude"]] == [True, False, False, False]
    assert payload["claude"][0]["rows"][0] == payload["claude"][0]["rows"][0] | {"label": "Session (5h)", "used": 96}
    assert len(payload["antigravity"]["rows"]) == 5 and payload["deepseek"]["balances"][0]["total"] == 12.4
    assert payload["copilot"]["rows"][0]["label"] == "Premium requests"

    monitor.switch(None)  # to the best one
    assert [c["n"] for c in monitor.payload()["claude"] if c["current"]] == [2]
    assert snapshot.collect(config.load_config()).current().account.number == 2  # type: ignore[union-attr]
    assert not config.active_file().exists()  # the real selection is untouched


def test_polls_every_minute_when_the_active_account_is_near_the_threshold(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    used = {"active": 40.0}

    def fake_collect(_: Config) -> Snapshot:
        usage = Usage("pro", (Window("Session (5h)", used["active"]), Window("Weekly (Fable)", 99, blocking=False)))
        return Snapshot(datetime.now(UTC), [AccountStatus(ClaudeAccount(1, "a@x", None), usage, current=True)])

    monkeypatch.setattr(server, "collect", fake_collect)
    monkeypatch.setattr(server, "notify", lambda alert: None)
    monitor = server.Monitor(port=1)
    assert monitor.next_delay() == 300  # nothing fetched yet

    monitor.refresh(force=True)
    assert monitor.next_delay() == 300  # 40% used; the per-model cap at 99% does not block, so it does not count

    used["active"] = 81.0  # within 15 points of the 95% threshold
    monitor.refresh(force=True)
    assert monitor.next_delay() == 60


def test_connect_runs_in_the_background_and_reports(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()
    release = threading.Event()

    def fake_run(order: tuple[str, ...]) -> connect.Result:
        started.set()
        release.wait(5)
        return connect.Result("duplicate", "c1@x", 1)

    monkeypatch.setattr(connect, "run", fake_run)
    assert api("/api/data")[1]["connect"] == {"status": "idle"}
    status, d = api("/api/connect", {})
    assert status == 200 and d["connect"] == {"status": "waiting"} and started.wait(5)
    assert api("/api/connect", {}) == (400, {"error": "A sign-in is already open in the browser."})
    release.set()
    for _ in range(50):
        if (d := api("/api/data")[1])["connect"]["status"] != "waiting":
            break
        threading.Event().wait(0.05)
    assert d["connect"] == {"status": "duplicate", "email": "c1@x", "number": 1, "error": None}


def test_alerts_go_to_the_native_app_while_it_polls(api: Api, sent: list[Alert]) -> None:
    _, d = api("/api/data")
    assert len(sent) == 1 and [n["title"] for n in d["notices"]] == [sent[0].title]  # #1 is at 97%
    first = d["notices"][0]["id"]

    sent.clear()
    api("/api/data", headers={server.NATIVE_HEADER: "macos"})  # the app polls: it shows the alerts from now on
    api("/api/prefs", {"auto_switch": True})
    _, d = api("/api/prefs", {"language": "es"})  # fetches again: the auto switch fires an alert
    assert sent == []
    assert len(d["notices"]) == 2 and d["notices"][1]["id"] > first
