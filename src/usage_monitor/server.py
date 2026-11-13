"""Local server (127.0.0.1) behind the web panel and the native apps; it also sends the alerts."""

from __future__ import annotations

import dataclasses
import json
import logging
import socket
import threading
import time
import urllib.request
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any

from . import __version__, accounts, connect, demo, i18n, settings
from .alerts import AlertTracker, auto_switch
from .config import Config, load_config, save_prefs
from .desktop import notify
from .i18n import tr
from .models import AccountStatus, Snapshot
from .snapshot import collect, to_json

log = logging.getLogger(__name__)
APP = "usage-monitor"
MIN_GAP = 60  # "Refresh" does not hit the APIs more than once a minute
HEADER = "X-Usage-Monitor"  # required on writes; see Handler.do_POST
MAX_BODY = 64 * 1024
NEAR_MARGIN, NEAR_INTERVAL = 15, 60  # within 15 points of the threshold, fetch every minute


class Monitor:
    """Keeps the latest Snapshot, refreshes it in the background and fires the alerts."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.alerts = AlertTracker()
        self._snap: Snapshot | None = None
        self._last = 0.0
        self._fetch_lock = threading.Lock()  # serialises fetches; reads never wait
        self.connecting: dict[str, Any] = {"status": "idle"}
        self._connect_lock = threading.Lock()  # one browser sign-in at a time, even with two quick clicks

    def config(self) -> Config:
        """Reloaded on every use, so changes from the CLI or the panel apply without a restart."""
        cfg = dataclasses.replace(load_config(), port=self.port)
        i18n.set_language(cfg.language)
        return cfg

    def refresh(self, force: bool = False) -> Snapshot:
        with self._fetch_lock:
            if self._snap and not force and time.time() - self._last < MIN_GAP:
                return self._snap
            cfg = self.config()
            snap = collect(cfg)
            fired = []
            if cfg.auto_switch and (switch := auto_switch(snap, cfg.alert_at)):
                target, alert = switch
                self._select(snap, target)
                fired.append(alert)
            fired += self.alerts.check(snap, cfg.alert_at)
            self._snap, self._last = snap, time.time()
        for alert in fired:
            notify(alert)
        return snap

    @staticmethod
    def _mark_current(snap: Snapshot) -> None:
        """The selection file is the single source of truth: `usage switch` changes it behind our back."""
        if demo.ENABLED:
            return
        current = accounts.current_dir()
        for s in snap.claude:
            s.current = s.account.config_dir == current

    @classmethod
    def _select(cls, snap: Snapshot, target: AccountStatus) -> None:
        if demo.ENABLED:
            demo.select(target.account.number)
            for s in snap.claude:
                s.current = s is target
        else:
            accounts.set_current(target.account)
            cls._mark_current(snap)

    def snapshot(self) -> Snapshot:
        snap = self._snap or self.refresh()
        self._mark_current(snap)
        return snap

    def switch(self, number: int | None) -> None:
        """Changes the active account (to `number`, or to the best one) without fetching usage again."""
        snap = self.snapshot()
        target = number if number is not None else (b.account.number if (b := snap.best()) else None)
        status = next((s for s in snap.claude if s.account.number == target), None)
        if status is None:
            if number is None:
                raise ValueError(tr("No other account has free usage right now."))
            raise ValueError(tr("There is no account #{n}.", n=number))
        self._select(snap, status)

    def set_prefs(self, language: str | None = None, auto: bool | None = None) -> None:
        changes: dict[str, Any] = {}
        if language is not None:
            if language not in i18n.LANGUAGES:
                raise ValueError(tr("unknown language: {code}", code=language))
            changes["language"] = language
        if auto is not None:
            changes["auto_switch"] = auto
        relabel = "language" in changes and changes["language"] != self.config().language
        save_prefs(**changes)
        if relabel:
            # shortcut: plan names and errors are translated when fetched, so a language change fetches again;
            # keep them as keys in the Snapshot instead if that extra request ever matters
            self.refresh(force=True)

    def connect(self) -> None:
        """Starts signing in another Claude account in the browser; the payload reports how it goes."""
        if demo.ENABLED:
            raise ValueError(tr("Not available with demo data."))
        with self._connect_lock:
            if self.connecting["status"] == "waiting":
                raise ValueError(tr("A sign-in is already open in the browser."))
            self.connecting = {"status": "waiting"}
        threading.Thread(target=self._connect, daemon=True, name="connect").start()

    def _connect(self) -> None:
        try:
            result = connect.run(self.config().claude_order)
        except Exception as e:  # the thread must always report back
            log.exception("connecting an account failed")
            result = connect.Result("failed", error=str(e))
        self.connecting = dataclasses.asdict(result)
        if result.status == "connected":
            self.refresh(force=True)

    def payload(self) -> dict[str, Any]:
        cfg = self.config()
        return to_json(self.snapshot(), cfg) | {"connect": self.connecting}

    def next_delay(self) -> int:
        """Seconds until the next fetch: the configured interval, or a minute once the active account is near
        the threshold. Heavy parallel use can burn the last 15% within one normal interval."""
        cfg = self.config()
        cur = self._snap.current() if self._snap else None
        near = bool(cur and cur.usage and cur.usage.hottest(cfg.alert_at - NEAR_MARGIN))
        return min(cfg.refresh_seconds, NEAR_INTERVAL) if near else cfg.refresh_seconds

    def run_forever(self) -> None:
        while True:
            delay = NEAR_INTERVAL
            try:
                self.refresh(force=True)
                delay = self.next_delay()
            except Exception:  # the refresher must outlive any single bad cycle
                log.exception("refresh failed; retrying in %d s", delay)
            time.sleep(delay)


def _text(body: dict[str, Any], key: str) -> str | None:
    value = body.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError(tr("`{key}` must be text", key=key))
    return value


def make_handler(monitor: Monitor) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"127.0.0.1:{monitor.port}", f"localhost:{monitor.port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — inherited signature
            log.debug(format, *args)

        def _send(self, code: int, body: bytes | dict[str, Any], ctype: str = "application/json") -> None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _host_ok(self) -> bool:  # blocks DNS rebinding
            return self.headers.get("Host", "") in allowed_hosts

        def _guarded(self, respond: Any) -> None:
            """Every failure becomes a JSON answer the interfaces can show, never a dropped connection."""
            try:
                respond()
            except ValueError as e:
                self._send(400, {"error": str(e)})
            except OSError as e:  # a file we need is missing or not writable
                self._send(500, {"error": str(e)})
            except Exception:
                log.exception("request failed: %s", self.path)
                self._send(500, {"error": tr("internal error; see the server log")})

        def do_GET(self) -> None:
            self._guarded(self._get)

        def do_POST(self) -> None:
            self._guarded(self._post)

        def _get(self) -> None:
            if not self._host_ok():
                return self._send(403, {"error": tr("host not allowed")})
            if self.path == "/":
                html = resources.files("usage_monitor.web").joinpath("panel.html").read_bytes()
                return self._send(200, html, "text/html; charset=utf-8")
            if self.path == "/api/ping":  # cheap identity check: no usage is fetched
                return self._send(200, {"app": APP, "version": __version__})
            if self.path == "/api/data":
                return self._send(200, monitor.payload())
            return self._send(404, {"error": tr("not found")})

        def _post(self) -> None:
            # A custom header: another website cannot send it without a CORS preflight, which is never approved.
            if not self._host_ok() or self.headers.get(HEADER) != "1":
                return self._send(403, {"error": tr("forbidden")})
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 <= length <= MAX_BODY:
                raise ValueError(tr("request body too large"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError(tr("a JSON object was expected"))
            plain: dict[str, Callable[[], object]] = {"/api/refresh": monitor.refresh, "/api/connect": monitor.connect}
            if action := plain.get(self.path):
                action()
            elif self.path == "/api/switch":
                n = body.get("n")
                if n is not None and (isinstance(n, bool) or not isinstance(n, int)):
                    raise ValueError(tr("`{key}` must be a whole number", key="n"))
                monitor.switch(n)
            elif self.path == "/api/settings":
                model, effort = _text(body, "model"), _text(body, "effort")
                if demo.ENABLED:
                    demo.set_settings(model, effort)
                else:
                    settings.write(model=model, effort=effort)
            elif self.path == "/api/prefs":
                auto = body.get("auto_switch")
                if auto is not None and not isinstance(auto, bool):
                    raise ValueError(tr("`{key}` must be true or false", key="auto_switch"))
                monitor.set_prefs(language=_text(body, "language"), auto=auto)
            else:
                return self._send(404, {"error": tr("not found")})
            return self._send(200, monitor.payload())

    return Handler


def local_json(port: int, path: str, timeout: float = 1.5) -> Any:
    """GET from the local server. Proxies are bypassed: HTTP_PROXY must never capture 127.0.0.1."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def is_running(port: int) -> bool:
    """Is OUR server answering on the port? (Another program may own it.)"""
    try:
        return bool(local_json(port, "/api/ping", timeout=1).get("app") == APP)
    except (OSError, ValueError, AttributeError):
        return False


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def serve(port: int) -> None:
    monitor = Monitor(port)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(monitor))  # bind first: fail before fetching
    threading.Thread(target=monitor.run_forever, daemon=True, name="refresher").start()
    log.info("serving on http://127.0.0.1:%d", port)
    server.serve_forever()
