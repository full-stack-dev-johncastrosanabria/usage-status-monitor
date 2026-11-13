"""Local server (127.0.0.1) behind the web panel and the macOS app; it also sends the alerts."""

from __future__ import annotations

import dataclasses
import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any

from . import accounts, i18n, settings
from .alerts import AlertTracker, auto_switch
from .config import Config, load_config, save_prefs
from .desktop import notify
from .i18n import tr
from .models import Snapshot
from .snapshot import collect, to_json

log = logging.getLogger(__name__)
MIN_GAP = 60  # "Refresh" does not hit the APIs more than once a minute
HEADER = "X-Usage-Monitor"  # required on writes; see Handler.do_POST


class Monitor:
    """Keeps the latest Snapshot, refreshes it in the background and fires the alerts."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.alerts = AlertTracker()
        self._snap: Snapshot | None = None
        self._last = 0.0
        self._fetch_lock = threading.Lock()  # serialises fetches; reads never wait

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
                accounts.set_current(target.account)
                for s in snap.claude:
                    s.current = s is target
                fired.append(alert)
            fired += self.alerts.check(snap, cfg.alert_at)
            self._snap, self._last = snap, time.time()
        for alert in fired:
            notify(alert)
        return snap

    def snapshot(self) -> Snapshot:
        return self._snap or self.refresh()

    def switch(self, number: int | None) -> None:
        """Changes the active account (to `number`, or to the best one) without fetching usage again."""
        snap = self.snapshot()
        target = number if number is not None else (b.account.number if (b := snap.best()) else None)
        status = next((s for s in snap.claude if s.account.number == target), None)
        if status is None:
            if number is None:
                raise ValueError(tr("No other account has free usage right now."))
            raise ValueError(tr("There is no account #{n}.", n=number))
        accounts.set_current(status.account)
        for s in snap.claude:
            s.current = s is status

    def set_prefs(self, language: Any = None, auto: Any = None) -> None:
        changes: dict[str, Any] = {}
        if language is not None:
            if language not in i18n.LANGUAGES:
                raise ValueError(tr("unknown language: {code}", code=language))
            changes["language"] = language
        if auto is not None:
            changes["auto_switch"] = bool(auto)
        relabel = "language" in changes and changes["language"] != self.config().language
        save_prefs(**changes)
        if relabel:
            # shortcut: labels and errors are translated when fetched, so a language change fetches again;
            # store label keys in Window instead if that extra request ever matters
            self.refresh(force=True)

    def payload(self) -> dict[str, Any]:
        cfg = self.config()
        return to_json(self.snapshot(), cfg)

    def run_forever(self) -> None:
        while True:
            try:
                self.refresh(force=True)
            except Exception:  # the server must not die because of one bad cycle
                log.exception("refresh failed")
            time.sleep(self.config().refresh_seconds)


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
            self.end_headers()
            self.wfile.write(data)

        def _host_ok(self) -> bool:  # blocks DNS rebinding
            return self.headers.get("Host", "") in allowed_hosts

        def do_GET(self) -> None:
            if not self._host_ok():
                return self._send(403, {"error": tr("host not allowed")})
            if self.path == "/":
                html = resources.files("usage_monitor.web").joinpath("panel.html").read_bytes()
                return self._send(200, html, "text/html; charset=utf-8")
            if self.path == "/api/data":
                return self._send(200, monitor.payload())
            return self._send(404, {"error": tr("not found")})

        def do_POST(self) -> None:
            # A custom header: another website cannot send it without a CORS preflight, which is never approved.
            if not self._host_ok() or self.headers.get(HEADER) != "1":
                return self._send(403, {"error": tr("forbidden")})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError(tr("a JSON object was expected"))
                if self.path == "/api/refresh":
                    monitor.refresh()
                elif self.path == "/api/switch":
                    n = body.get("n")
                    monitor.switch(int(n) if n is not None else None)
                elif self.path == "/api/settings":
                    settings.write(model=body.get("model"), effort=body.get("effort"))
                elif self.path == "/api/prefs":
                    monitor.set_prefs(language=body.get("language"), auto=body.get("auto_switch"))
                else:
                    return self._send(404, {"error": tr("not found")})
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, monitor.payload())

    return Handler


def is_running(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def serve(port: int) -> None:
    monitor = Monitor(port)
    threading.Thread(target=monitor.run_forever, daemon=True, name="refresher").start()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(monitor))
    log.info("serving on http://127.0.0.1:%d", port)
    server.serve_forever()
