"""The GTK 4 window: the same operator console as the web panel, drawn with native widgets."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, Gio, GLib, Graphene, Gtk  # noqa: E402

from . import logic  # noqa: E402

APP_ID = "dev.usage_monitor.Linux"
APP_DIR = Path(__file__).resolve().parent.parent
Payload = dict[str, Any]
Done = Callable[[Payload], str] | None

# Colours of panel.html's :root.
BG, SURFACE, RAISED = "#0b0d0c", "#101312", "#151917"
LINE, LINE_STRONG = "#1f2523", "#2e3633"
TEXT, BRIGHT, DIM = "#c8d1cc", "#e6ece8", "#8a958f"
ACCENT, ACCENT_INK, WARN, BAD = "#3fd07a", "#06130b", "#d9a441", "#e5534b"
TONES = {"ok": ACCENT, "warn": WARN, "bad": BAD}
FONTS = '"JetBrains Mono", "DejaVu Sans Mono", "Noto Sans Mono", "Noto Sans Mono CJK SC", monospace'

CSS = f"""
window, .root {{ background-color: {BG}; color: {TEXT}; }}
.root, .root * {{ font-family: {FONTS}; font-size: 13px; font-feature-settings: "tnum"; }}
.root selection {{ background-color: {ACCENT}; color: {ACCENT_INK}; }}
scrollbar {{ background-color: transparent; border: none; }}
scrollbar slider {{ background-color: {LINE_STRONG}; border: none; border-radius: 0; min-width: 6px; min-height: 6px; }}
.header {{ padding-bottom: 14px; border-bottom: 1px solid {LINE_STRONG}; }}
.title {{ font-size: 14px; font-weight: 600; color: {BRIGHT}; }}
.demo {{ font-size: 10px; letter-spacing: 0.08em; color: {WARN}; border: 1px solid {WARN}; padding: 0 6px; }}
.status {{ color: {DIM}; font-size: 12px; }}
.status.down {{ color: {BAD}; }}
.dot {{ min-width: 7px; min-height: 7px; border-radius: 99px; background-color: {ACCENT}; }}
.status.down .dot {{ background-color: {BAD}; }}

button.btn {{ background: none; background-color: transparent; color: {TEXT}; border: 1px solid {LINE_STRONG};
  border-radius: 2px; padding: 5px 12px; min-height: 0; min-width: 0; box-shadow: none; outline-color: {ACCENT};
  font-size: 12px; transition: background-color 150ms, color 150ms, border-color 150ms; }}
button.btn label {{ font-size: 12px; }}
button.btn:hover {{ border-color: {DIM}; background-color: {RAISED}; }}
button.btn:active {{ background-color: {LINE}; }}
button.btn:disabled {{ color: {DIM}; border-color: {LINE}; }}
button.btn:focus-visible {{ outline: 2px solid {ACCENT}; outline-offset: 2px; }}
button.primary {{ color: {ACCENT}; border-color: {ACCENT}; }}
button.primary:hover {{ color: {ACCENT_INK}; background-color: {ACCENT}; }}
button.primary:disabled {{ color: {DIM}; border-color: {LINE}; background-color: transparent; }}
button.opt {{ padding: 3px 9px; color: {DIM}; border-color: transparent; }}
button.opt:hover {{ color: {TEXT}; border-color: {LINE_STRONG}; background-color: transparent; }}
button.opt.chosen {{ color: {ACCENT}; border-color: {ACCENT}; background-color: rgba(63, 208, 122, 0.07); }}

.alert {{ padding: 10px 14px; border: 1px solid {BAD}; background-color: rgba(229, 83, 75, 0.08); }}
.h2 {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: {DIM}; }}
.h2hint {{ font-size: 11px; color: {DIM}; }}
.table {{ border: 1px solid {LINE}; background-color: {SURFACE}; }}
.headbg {{ border-bottom: 1px solid {LINE_STRONG}; }}
.rowbg.rule {{ border-top: 1px solid {LINE}; }}
.rowbg.current {{ background-color: rgba(63, 208, 122, 0.07); }}
.rowbg.link:hover {{ background-color: {RAISED}; }}
.cell {{ padding: 9px 14px; }}
.cell.head {{ padding-top: 7px; padding-bottom: 7px; }}
.cell.sub {{ padding-top: 0; }}
.cell.group {{ padding-bottom: 0; }}
.compact .cell {{ padding: 7px 10px; }}
.th {{ font-size: 11px; letter-spacing: 0.08em; color: {DIM}; }}
.num {{ color: {DIM}; }}
.num.current {{ color: {ACCENT}; font-weight: 600; }}
.name {{ color: {BRIGHT}; }}
.note, .when, .hint {{ color: {DIM}; font-size: 12px; }}
.dim {{ color: {DIM}; }}
.tag {{ font-size: 10px; letter-spacing: 0.08em; color: {DIM}; border: 1px solid {LINE_STRONG}; padding: 0 6px; }}
.tag.on {{ color: {ACCENT}; border-color: {ACCENT}; }}
.pct {{ font-weight: 600; }}
.pct.ok, .money {{ color: {ACCENT}; }}
.pct.warn {{ color: {WARN}; }}
.pct.bad, .money.bad, .err {{ color: {BAD}; }}
.money {{ font-weight: 600; }}
.empty {{ padding: 14px; color: {DIM}; }}
.dl > .dlrow {{ padding: 8px 14px; }}
.dl > .dlrow.rule {{ border-top: 1px solid {LINE}; }}
.dt {{ font-size: 11px; letter-spacing: 0.08em; color: {DIM}; }}
flowbox, flowboxchild {{ padding: 0; background: none; }}
.toast {{ padding: 8px 14px; font-size: 12px; color: {TEXT}; background-color: {RAISED};
  border: 1px solid {LINE_STRONG}; }}
"""


def rgba(hex_colour: str) -> Gdk.RGBA:
    colour = Gdk.RGBA()
    colour.parse(hex_colour)
    return colour


def label(text: str, *classes: str, xalign: float = 0.0, **props: Any) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=xalign, **props)
    for c in classes:
        widget.add_css_class(c)
    return widget


def button(text: str, on_click: Callable[[], None], *classes: str, pressed: bool | None = None) -> Gtk.Button:
    widget = Gtk.Button(label=text)
    for c in ("btn", *classes):
        widget.add_css_class(c)
    if pressed:
        widget.add_css_class("chosen")
    widget.connect("clicked", lambda _b: on_click())
    return widget


def hbox(*children: Gtk.Widget, spacing: int = 0, **props: Any) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing, **props)
    for child in children:
        box.append(child)
    return box


def vbox(*children: Gtk.Widget, spacing: int = 0, **props: Any) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing, **props)
    for child in children:
        box.append(child)
    return box


def clear(box: Gtk.Box) -> None:
    while child := box.get_first_child():
        box.remove(child)


class Meter(Gtk.Widget):
    """The thin segmented bar: ten cells, filled up to the % free, in the tone's colour."""

    CELLS, GAP, HEIGHT = 10, 1.4, 6

    def __init__(self, free: float, width: int) -> None:
        super().__init__(valign=Gtk.Align.CENTER)
        self.free, self.width = max(0.0, min(100.0, free)), width
        self.fill, self.empty = rgba(TONES[logic.tone(free)]), rgba(LINE)

    def do_measure(self, orientation: Gtk.Orientation, _for_size: int) -> tuple[int, int, int, int]:
        size = self.width if orientation == Gtk.Orientation.HORIZONTAL else self.HEIGHT
        return size, size, -1, -1

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        step = self.width / self.CELLS
        filled = self.width * self.free / 100
        for i in range(self.CELLS):
            x, w = i * step, step - self.GAP
            snapshot.append_color(self.empty, Graphene.Rect().init(x, 0, w, self.HEIGHT))
            if (lit := min(w, filled - x)) > 0:
                snapshot.append_color(self.fill, Graphene.Rect().init(x, 0, lit, self.HEIGHT))


class Table:
    """A Gtk.Grid of aligned columns in a bordered, horizontally scrollable frame.

    Every row gets a background widget spanning all columns, under its cells: it draws the rule above the row,
    the active row's wash and, for clickable rows, the hover.
    """

    def __init__(self, columns: int, expand: int, on_row: Callable[[int], None] | None = None) -> None:
        self.grid = Gtk.Grid()
        self.columns, self.expand, self.row, self.rule_next = columns, expand, 0, False
        self.targets: dict[Gtk.Widget, int] = {}
        self.widget = Gtk.ScrolledWindow(
            child=self.grid,
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True,
        )
        self.widget.add_css_class("table")
        # A horizontal-only scroller still swallows the vertical wheel; hand it to the page instead.
        wheel = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect("scroll", self._wheel)
        self.widget.add_controller(wheel)
        if on_row:
            click = Gtk.GestureClick()
            click.connect("released", self._clicked, on_row)
            self.grid.add_controller(click)

    def _wheel(self, controller: Gtk.EventControllerScroll, dx: float, dy: float) -> bool:
        parent = self.widget.get_parent()
        page = parent.get_ancestor(Gtk.ScrolledWindow) if parent else None
        if not dy or dx or page is None:
            return False  # sideways scrolling stays with the table
        adj = page.get_vadjustment()
        wheel_steps = controller.get_unit() == Gdk.ScrollUnit.WHEEL
        step = adj.get_page_size() ** (2 / 3) if wheel_steps else 1  # GTK's own wheel step
        adj.set_value(adj.get_value() + dy * step)
        return True

    def _clicked(self, _g: Gtk.GestureClick, _n: int, x: float, y: float, on_row: Callable[[int], None]) -> None:
        widget = self.grid.pick(x, y, Gtk.PickFlags.DEFAULT)
        while widget is not None and widget is not self.grid and widget not in self.targets:
            widget = widget.get_parent()
        if widget in self.targets:
            on_row(self.targets[widget])

    def add(self, cells: list[Any], *, kind: str = "", current: bool = False, n: int | None = None) -> None:
        """cells: widgets or (widget, column span). kind: "head", "sub" (continues the row above) or "group"."""
        bg = Gtk.Box(css_classes=["rowbg"])
        if kind == "head":
            bg.add_css_class("headbg")
        elif self.rule_next and kind != "sub":
            bg.add_css_class("rule")
        bg.add_css_class("current") if current else None
        self.grid.attach(bg, 0, self.row, self.columns, 1)
        col, row_widgets = 0, [bg]
        for item in cells:
            widget, span = item if isinstance(item, tuple) else (item, 1)
            box = vbox(widget, css_classes=["cell", kind] if kind else ["cell"], hexpand=col == self.expand)
            self.grid.attach(box, col, self.row, span, 1)
            row_widgets.append(box)
            col += span
        if n is not None:
            bg.add_css_class("link")
            for w in row_widgets:
                self.targets[w] = n
                w.set_cursor_from_name("pointer")
        self.rule_next = kind not in ("head", "group")
        self.row += 1


class Window(Gtk.ApplicationWindow):
    def __init__(self, app: App, width: int, snapshot: bool) -> None:
        super().__init__(
            application=app, title="usage-monitor", default_width=width, default_height=1 if snapshot else 860
        )
        self.app, self.data, self.lang = app, None, "en"
        self.compact = width < logic.COMPACT_BELOW
        self.toast_timer = 0
        self.root = vbox(css_classes=["root"])
        self.overlay = Gtk.Overlay()
        self.toast = label("", "toast", halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=20, wrap=True)
        self.toast.set_visible(False)
        if snapshot:  # the whole content at its natural height, for the PNG
            self.overlay.set_child(self.root)
        else:
            self.overlay.set_child(Gtk.ScrolledWindow(child=self.root, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.overlay.add_overlay(self.toast)
        self.set_child(self.overlay)
        self.status = label("…")
        self.offline = False
        self.render()

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        Gtk.ApplicationWindow.do_size_allocate(self, width, height, baseline)
        if (width < logic.COMPACT_BELOW) != self.compact:
            self.compact = not self.compact
            GLib.idle_add(self.render)  # never change the widget tree during allocation

    # ---------- text ----------

    def t(self, key: str, **values: object) -> str:
        return logic.tr(self.lang, key, **values)

    def show_toast(self, message: str) -> None:
        self.toast.set_label(message)
        self.toast.set_visible(True)
        if self.toast_timer:
            GLib.source_remove(self.toast_timer)
        self.toast_timer = GLib.timeout_add(4500, self._hide_toast)

    def _hide_toast(self) -> bool:
        self.toast.set_visible(False)
        self.toast_timer = 0
        return False

    # ---------- rendering ----------

    def render(self) -> bool:
        clear(self.root)
        pad = 12 if self.compact else 20
        for side in ("start", "end", "top"):
            getattr(self.root, f"set_margin_{side}")(pad)
        self.root.set_margin_bottom(24 if self.compact else 48)
        self.root.add_css_class("compact") if self.compact else self.root.remove_css_class("compact")
        data = self.data
        self.root.append(self.header(data))
        if data is None:
            return False
        if alert := self.alert(data):
            self.root.append(alert)
        self.section(self.t("secAccounts"), self.t("freeHint"), self.accounts(data))
        self.root.append(self.connect_row(data))
        self.section(self.t("secProviders"), "", self.providers(data))
        if not self.compact:
            self.section(self.t("secDefaults"), self.t("defaultsHint"), self.defaults(data))
        return False

    def connect_row(self, data: Payload) -> Gtk.Widget:
        state = data.get("connect") or {"status": "idle"}
        add = button(self.t("connect"), lambda: self.post("/api/connect", {}))
        add.set_sensitive(state["status"] != "waiting" and not data.get("demo"))
        row = hbox(add, spacing=14, margin_top=10)
        if text := logic.connect_text(state, self.lang):
            row.append(label(text, "dim"))
        if state["status"] == "waiting":  # the new account appears as soon as its browser sign-in ends
            GLib.timeout_add_seconds(3, lambda: self.post("/api/data", None) or False)
        return row

    def section(self, title: str, hint: str, body: Gtk.Widget) -> None:
        head = hbox(label(title.upper(), "h2"), spacing=10, margin_top=18 if self.compact else 30, margin_bottom=6)
        if hint and not self.compact:
            head.append(label(hint, "h2hint"))
        self.root.append(head)
        self.root.append(body)

    def header(self, data: Payload | None) -> Gtk.Widget:
        title = hbox(label("usage-monitor", "title"), spacing=10)
        if data and data.get("demo"):
            title.append(label(self.t("demo").upper(), "demo", valign=Gtk.Align.CENTER))
        left = vbox(title, hexpand=True, valign=Gtk.Align.END, spacing=4)
        tools = hbox(spacing=8, valign=Gtk.Align.END)
        if not self.compact:
            self.status = label("…", ellipsize=3)
            line = hbox(Gtk.Box(css_classes=["dot"], valign=Gtk.Align.CENTER), self.status, spacing=8)
            line.set_css_classes(["status", "down"] if self.offline else ["status"])
            left.append(line)
            if data:
                tools.append(self.language_options(data))
                refresh = button(self.t("refresh"), lambda: None)
                refresh.connect("clicked", self.on_refresh)
                tools.append(refresh)
        best = self.best(data)
        switch = button(
            self.t("switchBest", n=best["n"], p=logic.whole(best["score"])) if best else self.t("noBest"),
            lambda: self.post("/api/switch", {}, self.switched),
            "primary",
        )
        switch.set_sensitive(best is not None)
        switch.get_child().set_ellipsize(3)  # lets a narrow window shrink below the label's width
        tools.append(switch)
        self.update_status()
        return hbox(left, tools, spacing=20, css_classes=["header"])

    def language_options(self, data: Payload) -> Gtk.Widget:
        box = hbox(spacing=4, margin_end=8)
        for code, name in data.get("languages", {}).items():
            box.append(
                button(name, lambda c=code: self.post("/api/prefs", {"language": c}), "opt", pressed=code == self.lang)
            )
        return box

    def update_status(self) -> None:
        if self.offline or self.data is None:
            self.status.set_label(self.t("offline") if self.offline else "…")
            return
        d = self.data
        ago = logic.ago(d["updated"], self.lang)
        every = f"{d['every'] / 60:g}"
        self.status.set_label(f"{self.t('online')} · " + self.t("status", ago=ago, m=every, p=f"{d['alert_at']:g}"))

    def best(self, data: Payload | None) -> Payload | None:
        return next((c for c in (data or {}).get("claude", []) if c["n"] == (data or {}).get("best")), None)

    def alert(self, data: Payload) -> Gtk.Widget | None:
        if not (hot := logic.hot_row(data)):
            return None
        cur, row = hot
        best = self.best(data)
        head = self.t("alertHead", n=cur["n"], p=logic.whole(row["used"]), label=row["label"])
        rest = self.t("alertBest", n=best["n"], p=logic.whole(best["score"])) if best else self.t("alertNone")
        text = label("", hexpand=True, wrap=True)
        esc = GLib.markup_escape_text
        text.set_markup(f'<span weight="600" foreground="{BAD}">{esc(head)}</span> {esc(rest)}')
        box = hbox(text, spacing=16, css_classes=["alert"], margin_top=16)
        if best:
            n = best["n"]
            box.append(
                button(self.t("alertButton", n=n), lambda: self.post("/api/switch", {"n": n}, self.switched), "primary")
            )
        return box

    def meter(self, free: float, reset: str | None = None, when: bool = False) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=10, row_spacing=2, halign=Gtk.Align.END if self.compact else Gtk.Align.START)
        tone = logic.tone(free)
        grid.attach(label(f"{logic.whole(free)}%", "pct", tone, xalign=1, width_chars=4), 0, 0, 1, 1)
        bar = Meter(free, 44 if self.compact else 84)
        bar.set_tooltip_text(self.t("freeAria", p=logic.whole(free)))
        grid.attach(bar, 1, 0, 1, 1)
        if when and (text := logic.countdown(reset, self.lang)):
            grid.attach(label(text, "when"), 1, 1, 1, 1)
        return grid

    def account_name(self, c: Payload, best: int | None) -> Gtk.Widget:
        name = label(c["email"], "name", ellipsize=3, width_chars=16, max_width_chars=34, hexpand=True)
        name.set_tooltip_text(c["email"])
        tags = hbox(spacing=6, margin_top=3)
        if c["current"]:
            tags.append(label(self.t("tagActive").upper(), "tag", "on"))
        if c["n"] == best and not self.compact:
            tags.append(label(self.t("tagBest").upper(), "tag"))
        return vbox(name, tags) if tags.get_first_child() else name

    def accounts(self, data: Payload) -> Gtk.Widget:
        if not data["claude"]:
            return vbox(label(self.t("noSessions"), "empty", wrap=True), css_classes=["table"])
        labels = logic.limit_labels(data["claude"])
        if self.compact:
            table = Table(3, 1, on_row=self.use)
            table.add(
                [
                    label("#", "th"),
                    label(self.t("colAccount").upper(), "th"),
                    label(self.t("colFree").upper(), "th", xalign=1),
                ],
                kind="head",
            )
        else:
            table = Table(4 + max(1, len(labels)), 1)
            heads = ["#", self.t("colAccount"), self.t("colPlan"), *labels]
            table.add([label(h.upper(), "th") for h in heads] + [label("")], kind="head")
        for c in data["claude"]:
            table.add(
                self.account_row(c, data["best"], labels), current=c["current"], n=None if c["current"] else c["n"]
            )
        return table.widget

    def account_row(self, c: Payload, best: int | None, labels: list[str]) -> list[Any]:
        cells: list[Any] = [
            label(str(c["n"]), "num", *(["current"] if c["current"] else [])),
            self.account_name(c, best),
        ]
        if self.compact:
            cells.append(label(self.t("failed"), "err", xalign=1) if "error" in c else self.meter(c["score"]))
            return cells
        cells.append(label(c.get("plan") or "", "dim"))
        if "error" in c:
            cells.append((label(c["error"], "err", wrap=True, max_width_chars=60), max(1, len(labels))))
        else:
            by_label = {r["label"]: r for r in c["rows"]}
            cells += [
                self.meter(r["free"], r["reset"], when=True) if (r := by_label.get(lb)) else label("") for lb in labels
            ]
        n = c["n"]
        use = button(self.t("use"), lambda: self.post("/api/switch", {"n": n}, self.switched))
        use.set_halign(Gtk.Align.END)
        cells.append(label("") if c["current"] else use)
        return cells

    def providers(self, data: Payload) -> Gtk.Widget:
        table = Table(2 if self.compact else 4, 0 if self.compact else 3)
        heads = ["colLimit", "colFree"] if self.compact else ["colSource", "colLimit", "colFree", "colResets"]
        table.add(
            [label(self.t(h).upper(), "th", xalign=1 if self.compact and h == "colFree" else 0) for h in heads],
            kind="head",
        )
        ag = data["antigravity"]
        self.provider_rows(table, "ChatGPT / Codex", data["codex"].get("plan") or "", data["codex"])
        self.provider_rows(table, "Antigravity", ag.get("plan") or "", ag, lambda r: f"{r['group']} · {r['label']}")
        if gh := data.get("copilot"):  # missing from servers older than 0.2
            self.provider_rows(table, "GitHub Copilot", gh.get("plan") or "", gh)
        self.provider_rows(table, "DeepSeek API", "", data["deepseek"])
        return table.widget

    def provider_rows(
        self, table: Table, source: str, note: str, usage: Payload, label_of: Callable[[Payload], str] | None = None
    ) -> None:
        name = hbox(label(source, "name"), spacing=10)
        if note:
            name.append(label(note, "note", ellipsize=3, max_width_chars=40, tooltip_text=note))
        if self.compact:
            table.add([(name, 2)], kind="group")
        lead: Callable[[bool], list[Any]] = (
            (lambda _first: []) if self.compact else (lambda first: [name if first else label("")])
        )
        if "error" in usage:
            table.add(
                [*lead(True), (label(usage["error"], "err", wrap=True, max_width_chars=60), 2 if self.compact else 3)]
            )
            return
        for i, row in enumerate(usage.get("balances") or usage["rows"]):
            table.add(lead(i == 0) + self.provider_cells(row, usage, label_of), kind="sub" if i else "")

    def provider_cells(self, row: Payload, usage: Payload, label_of: Callable[[Payload], str] | None) -> list[Any]:
        if "currency" in row:  # a DeepSeek balance
            money = label(f"{row['total']:.2f} {row['currency']}", "money", *([] if usage["available"] else ["bad"]))
            money.set_xalign(1 if self.compact else 0)
            cells: list[Any] = [label(self.t("balance")), money]
            if not self.compact:
                topped, granted = f"{row['topped_up']:.2f}", f"{row['granted']:.2f}"
                detail = f"{self.t('toppedUp', v=topped)} · {self.t('granted', v=granted)}"
                cells.append(label(detail if usage["available"] else self.t("noBalance"), "dim"))
            return cells
        cells = [label(label_of(row) if label_of else row["label"]), self.meter(row["free"])]
        if not self.compact:
            cells.append(label(logic.countdown(row["reset"], self.lang), "dim"))
        return cells

    def defaults(self, data: Payload) -> Gtk.Widget:
        s, rows = data.get("settings") or {}, []
        if "error" in s:
            rows.append((self.t("model"), [label(s["error"], "err", wrap=True)]))
        else:
            for key, more in (("model", False), ("moreModels", True)):
                models = [(m["id"], m["label"]) for m in s["models"] if m["more"] == more]
                rows.append((self.t(key), [self.options("model", models, s["model"])]))
            efforts = [(e, e) for e in s["efforts"]]
            rows.append(
                (
                    self.t("effort"),
                    [self.options("effort", efforts, s["effort"]), label(self.t("effortHint"), "hint", wrap=True)],
                )
            )
        auto = [(True, self.t("on")), (False, self.t("off"))]
        hint = label(self.t("autoHint", p=f"{data['alert_at']:g}"), "hint", wrap=True)
        rows.append((self.t("autoSwitch"), [self.options("auto", auto, data["auto_switch"]), hint]))
        dl = vbox(css_classes=["table", "dl"])
        for i, (term, body) in enumerate(rows):
            dt = label(term.upper(), "dt", valign=Gtk.Align.START, margin_top=4, wrap=True)
            dt.set_size_request(130, -1)
            row = hbox(
                dt, vbox(*body, spacing=4, hexpand=True), spacing=14, css_classes=["dlrow", *(["rule"] if i else [])]
            )
            dl.append(row)
        return dl

    def options(self, name: str, items: list[tuple[Any, str]], chosen: Any) -> Gtk.Widget:
        flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE, column_spacing=4, row_spacing=4, max_children_per_line=24
        )
        flow.set_homogeneous(False)
        flow.set_halign(Gtk.Align.START)
        for value, text in items:
            flow.append(button(text, lambda v=value: self.choose(name, v), "opt", pressed=value == chosen))
        child = flow.get_first_child()
        while child:
            child.set_focusable(False)  # focus goes to the button inside, not to the flowbox cell
            child = child.get_next_sibling()
        return flow

    # ---------- actions ----------

    def choose(self, name: str, value: Any) -> None:
        if name == "auto":
            self.post(
                "/api/prefs",
                {"auto_switch": value},
                lambda d: self.t("toastAuto", state=self.t("on" if d["auto_switch"] else "off")),
            )
        else:
            self.post("/api/settings", {name: value}, self.settings_changed)

    def use(self, n: int) -> None:
        self.post("/api/switch", {"n": n}, self.switched)

    def switched(self, d: Payload) -> str:
        c = next(x for x in d["claude"] if x["current"])
        return self.t("toastSwitch", n=c["n"], email=c["email"])

    def settings_changed(self, d: Payload) -> str:
        s = d["settings"]
        model = next((m["label"] for m in s["models"] if m["id"] == s["model"]), s["model"])
        return self.t("toastSettings", model=model, effort=s["effort"])

    def on_refresh(self, b: Gtk.Button) -> None:
        b.set_sensitive(False)
        b.set_label(self.t("refreshing"))
        self.post("/api/refresh", {})

    def post(self, path: str, body: Payload, done: Done = None) -> None:
        self.app.request(path, body, done)

    def loaded(self, data: Payload | None, error: str | None, done: Done, poll: bool) -> None:
        """On the UI thread, with the result of a request: a poll failing means offline; an action, a toast."""
        if data is not None:
            self.data, self.offline = data, False
            self.lang = data["lang"] if data.get("lang") in logic.I18N else "en"
        elif poll:
            self.offline = True
        self.render()
        if data is not None and done:
            self.show_toast(done(data))
        elif error and not poll:
            self.show_toast(error)


class App(Gtk.Application):
    def __init__(self, args: argparse.Namespace) -> None:
        flags = Gio.ApplicationFlags.NON_UNIQUE if args.snapshot else Gio.ApplicationFlags.DEFAULT_FLAGS
        super().__init__(application_id=APP_ID, flags=flags)
        self.args = args
        env_port = logic.port_from_env()
        self.port = env_port or logic.DEFAULT_PORT
        self.may_spawn = env_port is None  # someone else's server: never start our own
        self.server: subprocess.Popen[bytes] | None = None
        self.spawn_lock = threading.Lock()
        self.window: Window | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        Gtk.Window.set_default_icon_name("usage-monitor")  # installed by the .deb (hicolor theme)
        settings = Gtk.Settings.get_default()
        if settings:
            settings.props.gtk_application_prefer_dark_theme = True
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS) if hasattr(provider, "load_from_string") else provider.load_from_data(CSS, -1)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        for sig in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self._quit)

    def _quit(self) -> bool:
        self.quit()
        return False

    def do_activate(self) -> None:
        if self.window:
            self.window.present()
            return
        self.window = Window(self, self.args.width, snapshot=bool(self.args.snapshot))
        self.window.present()
        if self.args.snapshot:
            self.request("/api/data", None, None, then=self._capture_soon)
            GLib.timeout_add_seconds(40, self._watchdog)
        else:
            self.request("/api/data", None, None)
            GLib.timeout_add_seconds(logic.POLL_SECONDS, self._poll)

    def do_shutdown(self) -> None:
        if self.server and self.server.poll() is None:  # only the server this app started
            self.server.terminate()
            try:
                self.server.wait(5)
            except subprocess.TimeoutExpired:
                self.server.kill()
        Gtk.Application.do_shutdown(self)

    def _poll(self) -> bool:
        self.request("/api/data", None, None)
        return True

    # ---------- the backend ----------

    def ensure_server(self) -> None:
        """Worker thread: starts `usage server` when nothing answers on the port (only once)."""
        with self.spawn_lock:
            if not self.may_spawn or self.server or logic.is_up(self.port):
                return
            cmd = logic.server_command()
            if not cmd:
                return
            path = os.pathsep.join(filter(None, [str(APP_DIR), os.environ.get("PYTHONPATH")]))
            self.server = subprocess.Popen(
                [*cmd, "server", "--port", str(self.port)],
                env={**os.environ, "PYTHONPATH": path},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            for _ in range(100):  # up to 10 s; the first payload fetches every provider
                if logic.is_up(self.port) or self.server.poll() is not None:
                    break
                time.sleep(0.1)

    def request(self, path: str, body: Payload | None, done: Done, then: Callable[[], None] | None = None) -> None:
        """Runs the HTTP call on a worker thread and hands the result to the window on the UI thread."""

        def work() -> None:
            data, error = None, None
            try:
                self.ensure_server()
                data = logic.call(self.port, path, body, timeout=120)
            except (logic.ApiError, OSError) as e:  # OSError: the server could not be started
                error = str(e)
            GLib.idle_add(self._deliver, data, error, done, body is None, then)

        threading.Thread(target=work, daemon=True, name=f"request {path}").start()

    def _deliver(
        self, data: Payload | None, error: str | None, done: Done, poll: bool, then: Callable[[], None] | None
    ) -> bool:
        if self.window:
            self.window.loaded(data, error, done, poll)
        if then:
            then()
        return False

    # ---------- --snapshot ----------

    def _capture_soon(self) -> None:
        GLib.timeout_add(800, self._capture)

    def _capture(self) -> bool:
        assert self.window
        root = self.window.overlay
        width, height = root.get_width(), root.get_height()
        paintable = Gtk.WidgetPaintable(widget=root)
        snap = Gtk.Snapshot()
        snap.append_color(rgba(BG), Graphene.Rect().init(0, 0, width, height))
        paintable.snapshot(snap, width, height)
        node = snap.to_node()
        renderer = self.window.get_renderer()
        if node is None or renderer is None:
            print("snapshot: nothing to render", file=sys.stderr)
            self.exit_code = 1
        else:
            renderer.render_texture(node, None).save_to_png(self.args.snapshot)
            print(f"{self.args.snapshot} ({width}x{height})")
        self.quit()
        return False

    def _watchdog(self) -> bool:
        print("snapshot: timed out", file=sys.stderr)
        self.exit_code = 2
        self.quit()
        return False

    exit_code = 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="usage-monitor", description="usage-monitor for the Linux desktop")
    parser.add_argument("--snapshot", metavar="FILE.png", help=argparse.SUPPRESS)
    parser.add_argument("--width", type=int, default=1100, help=argparse.SUPPRESS)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    GLib.set_prgname(APP_ID)  # X11 WM_CLASS: matches StartupWMClass in the .desktop file (else "__main__.py")
    GLib.set_application_name("Usage Monitor")
    app = App(args)
    status = app.run([sys.argv[0]])
    return app.exit_code or status
