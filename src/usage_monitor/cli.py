"""The `usage` command: account status, switching, model/effort, the panel and the server."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__, accounts, config, connect, desktop, i18n, settings, sync
from .alerts import session_warning, should_show, switch_notice
from .config import Config, load_config, save_prefs
from .i18n import tr
from .server import is_running, local_json, port_in_use, serve
from .snapshot import collect, collect_current, to_json
from .system import atomic_write_text
from .term import print_snapshot


def self_command() -> list[str]:
    """How to run this program again from another process (the server, the start-at-login entry)."""
    if getattr(sys, "frozen", False):  # a standalone build: the executable is the program
        return [sys.executable]
    if exe := shutil.which("usage"):
        return [exe]
    return [sys.executable, "-m", "usage_monitor"]


def cmd_status(args: argparse.Namespace, cfg: Config) -> int:
    snap = collect(cfg)
    if getattr(args, "json", False):
        print(json.dumps(to_json(snap, cfg), ensure_ascii=False, indent=2))
    else:
        print_snapshot(snap)
    return 0


def cmd_current(_: argparse.Namespace, cfg: Config) -> int:
    snap = collect_current(cfg)
    if not snap.claude:
        print(tr("The active folder ({path}) has no Claude session.", path=accounts.current_dir() or "~/.claude"))
        return 1
    print_snapshot(snap, only_current=True)
    return 0


def cmd_switch(args: argparse.Namespace, cfg: Config) -> int:
    if args.number is not None:
        acc = next((a for a in accounts.discover(cfg.claude_order) if a.number == args.number), None)
        if acc is None:
            print(tr("There is no account #{n}.", n=args.number))
            return 1
    else:
        snap = collect(cfg)
        print_snapshot(snap)
        best = snap.best()
        if best is None:
            print(tr("No other account has free usage right now; check which one resets first."))
            return 1
        acc = best.account
    accounts.set_current(acc)
    print(tr("→ Active account: Claude #{n} {email}", n=acc.number, email=acc.email))
    print("  " + tr("Open sessions keep their account: exit and run `claude --continue` to carry on with this one."))
    return 0


def _print_settings(s: settings.ClaudeSettings) -> None:
    print(tr("Model: {label} ({id})   Effort: {effort}", label=s.label, id=s.model, effort=s.effort))


def cmd_model(args: argparse.Namespace, _: Config) -> int:
    s = settings.write(model=args.value) if args.value else settings.read()
    _print_settings(s)
    if not args.value:
        for m in s.models:
            print(f"  {m.id:<18} {m.label}")
    return 0


def cmd_effort(args: argparse.Namespace, _: Config) -> int:
    s = settings.write(effort=args.value) if args.value else settings.read()
    _print_settings(s)
    if not args.value:
        print(tr("Available: {values}", values=", ".join(s.efforts)))
    return 0


def cmd_panel(_: argparse.Namespace, cfg: Config) -> int:
    url = f"http://127.0.0.1:{cfg.port}/"
    if not is_running(cfg.port):
        log_path = config.CONFIG_DIR / "server.log"
        if port_in_use(cfg.port):
            print(
                tr(
                    "error: port {port} is used by another program; set another `port` in the configuration.",
                    port=cfg.port,
                ),
                file=sys.stderr,
            )
            return 1
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            desktop.spawn_detached([*self_command(), "server"], log)
        for _attempt in range(80):
            if is_running(cfg.port):
                break
            time.sleep(0.1)
        else:
            print(tr("error: the server did not start; see {path}", path=log_path), file=sys.stderr)
            return 1
    where = desktop.open_panel(url)
    print(tr("Panel opened in {where} ({url}).", where=where, url=url))
    print(tr("The server keeps running in the background and alerts at {p:.0f}%.", p=cfg.alert_at))
    return 0


def cmd_server(args: argparse.Namespace, cfg: Config) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # the server is global: the active account is the selected one, not that of the terminal that started it
    os.environ.pop("CLAUDE_CONFIG_DIR", None)
    serve(args.port or cfg.port)
    return 0


def cmd_watch(args: argparse.Namespace, cfg: Config) -> int:
    every = max(60, args.seconds)  # the endpoints answer 429 when polled often
    try:
        while True:
            snap = collect(cfg)
            print("\033[2J\033[H", end="")
            print_snapshot(snap)
            print(tr("(refreshes every {s}s, Ctrl+C to quit)", s=every))
            time.sleep(every)
    except KeyboardInterrupt:
        return 0


def cmd_sync(_: argparse.Namespace, __: Config) -> int:
    failed = 0
    for path in sync.account_dirs():  # one account failing must not hide what was done for the others
        name = str(path).replace(str(config.HOME), "~")
        try:
            print(f"{name}: {', '.join(sync.sync_account(path)) or tr('already in sync')}")
        except (OSError, ValueError) as e:  # on Windows, creating symlinks needs Developer Mode
            failed += 1
            print(tr("{name}: error: {error}", name=name, error=e), file=sys.stderr)
            if getattr(e, "winerror", None) == 1314:
                print(tr("On Windows, turn on Developer Mode to create links."), file=sys.stderr)
    return 1 if failed else 0


def cmd_connect(_: argparse.Namespace, cfg: Config) -> int:
    print(tr("Sign in with the new account in the browser that opens…"))
    r = connect.run(cfg.claude_order, interactive=True)
    messages = {
        "connected": tr("Connected Claude #{n} ({email}).", n=r.number, email=r.email),
        "duplicate": tr("{email} is already connected as #{n}.", email=r.email, n=r.number),
        "cancelled": tr("Sign-in cancelled; nothing was added."),
        "failed": tr("Could not connect: {error}", error=r.error),
    }
    print(messages[r.status], file=sys.stdout if r.status == "connected" else sys.stderr)
    return 0 if r.status == "connected" else 1


def cmd_autostart(args: argparse.Namespace, _: Config) -> int:
    path = desktop.set_autostart(args.state == "on", [*self_command(), "panel"])
    state = tr("Start at login enabled ({path}).") if args.state == "on" else tr("Start at login disabled ({path}).")
    print(state.format(path=path))
    return 0


def cmd_autoswitch(args: argparse.Namespace, cfg: Config) -> int:
    if args.state:
        save_prefs(auto_switch=args.state == "on")
        cfg = load_config()
    if cfg.auto_switch:
        print(tr("Automatic switch: on (at {p:.0f}%, while the panel or the app is running).", p=cfg.alert_at))
    else:
        print(tr("Automatic switch: off."))
    return 0


def cmd_lang(args: argparse.Namespace, _: Config) -> int:
    if args.code:
        save_prefs(language=args.code)
        i18n.set_language(args.code)
    for code, name in i18n.LANGUAGES.items():
        print(f"{'●' if code == i18n.language() else ' '} {code}  {name}")
    return 0


def cmd_config(_: argparse.Namespace, __: Config) -> int:
    path = config.config_file()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(config.EXAMPLE, encoding="utf-8")
        print(tr("Created {path}", path=path))
    else:
        print(path)
    return 0


def hook_messages(cfg: Config) -> list[str]:
    """Notices for the Claude Code session running the hook (its account is that of its CLAUDE_CONFIG_DIR)."""
    accs = accounts.discover(cfg.claude_order)
    mine = next((a for a in accs if a.config_dir == accounts.session_dir()), None)
    chosen = next((a for a in accs if a.config_dir == accounts.selected_dir()), None)
    if mine is None:
        return []
    messages = []
    if chosen and chosen != mine:
        shared = sync.shares_transcripts(mine.config_dir, chosen.config_dir)
        messages.append(switch_notice(mine, chosen, can_continue=shared, reopens=bool(os.environ.get(LAUNCHER))))
    try:  # only the local server's cache: a hook must not call the APIs on every message
        if msg := session_warning(local_json(cfg.port, "/api/data"), mine.number):
            messages.append(msg)
    except (OSError, ValueError, LookupError):  # server not running, or not ours
        pass
    return messages


def cmd_notice(_: argparse.Namespace, cfg: Config) -> int:
    """Claude Code hook (SessionStart, UserPromptSubmit, Stop). It never fails: a broken hook would nag on every
    message. It also tells the launcher which conversation runs and whether Claude is answering."""
    try:
        hook = json.loads(sys.stdin.read() or "{}") if not sys.stdin.isatty() else {}
        event = hook.get("hook_event_name")
        if (launch := _launch_file()) and isinstance(sid := hook.get("session_id"), str):
            atomic_write_text(launch, json.dumps({"session": sid, "busy": event == "UserPromptSubmit"}))
        if event == "Stop":
            return 0
        text = " · ".join(hook_messages(cfg))
        state_file = config.CONFIG_DIR / "notices.json"
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        if text and should_show(state, str(hook.get("session_id", "cli")), text, time.time()):
            atomic_write_text(state_file, json.dumps(state))
            print(json.dumps({"systemMessage": "⚠ " + text}, ensure_ascii=False))
    except Exception:  # noqa: BLE001 — see the docstring
        pass
    return 0


REOPEN_DELAY = 3  # seconds to cancel (Ctrl+C) before reopening on the new account
POLL, EXHAUSTED_EVERY = 1.0, 10.0  # seconds between checks of the selection / of the server's usage cache
LAUNCHER = "USAGE_MONITOR_LAUNCHER"  # set by the launcher: lets the hook report the session to it
# sent to Claude (not translated) when the switch cut a reply short
CONTINUE = "Continue where you left off: the account was switched because the previous one ran out."


def _launch_file() -> Path | None:
    """Where the hook reports to the launcher that started it (keyed by its process id)."""
    token = os.environ.get(LAUNCHER, "")
    return config.CONFIG_DIR / "launches" / token if token.isdigit() else None


def _launch_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _exhausted(directory: Path | None) -> bool:
    """Is the account in `directory` at 100% of a blocking limit? Read from the local server's cache only."""
    cfg = load_config()
    mine = next((a for a in accounts.discover(cfg.claude_order) if a.config_dir == directory), None)
    try:
        payload = local_json(cfg.port, "/api/data")
    except (OSError, ValueError):
        return False
    acc = next((c for c in payload.get("claude", []) if mine and c.get("n") == mine.number), None)
    if acc is None:
        return False
    return any(r.get("blocking") and r.get("used", 0) >= 100 for r in acc.get("rows", []))


# Claude Code options followed by a value (`claude --help`); anything else that is not an option is the prompt.
# shortcut: a fixed list; an option added later that takes a value loses it on reopen until it is listed here
VALUE_OPTIONS = frozenset(
    [
        "--add-dir",
        "--agent",
        "--agents",
        "--append-system-prompt",
        "--autocompact",
        "--betas",
        "--debug-file",
        "--effort",
        "--environment",
        "--fallback-model",
        "--file",
        "--input-format",
        "--json-schema",
        "--max-budget-usd",
        "--mcp-config",
        "--model",
        "-n",
        "--name",
        "--output-format",
        "--permission-mode",
        "--permission-prompts",
        "--plugin-dir",
        "--plugin-url",
        "--remote-control-session-name-prefix",
        "--session-id",
        "--setting-sources",
        "--settings",
        "--system-prompt",
        "--system-prompt-snapshot",
        "--tools",
    ]
)


def _reopen_args(args: list[str]) -> list[str]:
    """The options to reopen with: without -c/--continue, -r/--resume [id] (the session is named instead) and
    the initial prompt (it was already sent)."""
    out: list[str] = []
    rest = iter(args)
    for a in rest:
        if a in ("-r", "--resume"):
            continue  # its optional id is dropped below as a positional
        if a in VALUE_OPTIONS:
            out += [a, next(rest, "")]
        elif a.startswith("-") and a not in ("-c", "--continue") and not a.startswith("--resume="):
            out.append(a)
    return out


def _run(cmd: list[str], env: dict[str, str], used: Path | None, launch: Path, watch: bool) -> tuple[int, bool]:
    """Runs Claude Code. With `watch`, stops it once another account is selected and Claude is not answering
    (or its account is exhausted, so nothing is lost). Returns (exit code, whether a reply was cut short)."""
    proc = subprocess.Popen(cmd, env=env)
    checked = -EXHAUSTED_EVERY
    while (code := proc.poll()) is None:
        try:
            time.sleep(POLL)
        except KeyboardInterrupt:  # Ctrl+C belongs to Claude Code, which got it too
            continue
        if not watch or accounts.selected_dir() == used:
            continue
        busy = bool(_launch_state(launch).get("busy"))
        if busy:
            if time.monotonic() - checked < EXHAUSTED_EVERY:
                continue
            checked = time.monotonic()
            if not _exhausted(used):
                continue
        proc.terminate()  # the transcript is on disk: --resume picks it up
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        return 0, busy
    return code, False


def launch_claude(args: list[str]) -> int:
    """`usage claude …`: runs Claude Code with the selected account (the same in any shell and system).

    A running session cannot change account, so when another account is selected (`usage switch`, the panel or
    the automatic switch) the launcher closes Claude Code between replies and reopens the same conversation on
    the new account. A reply cut short by an exhausted account is resumed with a "continue" prompt.
    """
    exe = shutil.which("claude")
    if exe is None:
        print(tr("error: `claude` is not on the PATH."), file=sys.stderr)
        return 127
    pinned = bool(os.environ.get("CLAUDE_CONFIG_DIR"))  # an explicit folder is never second-guessed
    oneshot = "-p" in args or "--print" in args
    token = str(os.getpid())
    launch = config.CONFIG_DIR / "launches" / token
    base, run_args = _reopen_args(args), args
    try:
        while True:
            env = os.environ | {LAUNCHER: token}
            used = accounts.selected_dir()
            if not pinned and used:
                env["CLAUDE_CONFIG_DIR"] = str(used)
            code, cut = _run([exe, *run_args], env, used, launch, watch=not (pinned or oneshot))
            now = accounts.selected_dir()
            if pinned or oneshot or now == used:
                return code
            print(
                tr(
                    "Account changed: reopening this conversation on {dir} in {s} s (Ctrl+C cancels)…",
                    dir=str(now or "~/.claude").replace(str(config.HOME), "~"),
                    s=REOPEN_DELAY,
                )
            )
            time.sleep(REOPEN_DELAY)
            sid = _launch_state(launch).get("session")
            # no conversation reported yet (still on a startup dialog): start over the way the user did
            run_args = ["--resume", sid, *base] if isinstance(sid, str) and sid else list(args)
            if cut:
                run_args.append(CONTINUE)
    except KeyboardInterrupt:
        return 130
    finally:
        launch.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="usage", description=tr("Available usage across Claude, ChatGPT, Antigravity and DeepSeek.")
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="command")

    st = sub.add_parser("status", help=tr("every account (the default)"))
    st.add_argument("--json", action="store_true", help=tr("JSON output"))
    sub.add_parser("current", help=tr("only the active Claude account"))
    sw = sub.add_parser("switch", help=tr("change the active Claude account"))
    sw.add_argument("number", nargs="?", type=int, help=tr("account number; without it, the one with the most room"))
    sub.add_parser("claude", help=tr("run Claude Code with the active account (arguments are passed through)"))
    m = sub.add_parser("model", help=tr("show or set Claude Code's default model"))
    m.add_argument("value", nargs="?")
    e = sub.add_parser("effort", help=tr("show or set Claude Code's default effort"))
    e.add_argument("value", nargs="?", choices=settings.EFFORTS)
    sub.add_parser("panel", help=tr("open the panel (starts the server if needed)"))
    a = sub.add_parser("autostart", help=tr("open the panel when you log in"))
    a.add_argument("state", choices=("on", "off"))
    au = sub.add_parser("autoswitch", help=tr("switch account automatically when the active one hits the threshold"))
    au.add_argument("state", nargs="?", choices=("on", "off"))
    la = sub.add_parser("lang", help=tr("show or set the interface language"))
    la.add_argument("code", nargs="?", choices=tuple(i18n.LANGUAGES))
    srv = sub.add_parser("server", help=tr("run the server in the foreground"))
    srv.add_argument("--port", type=int, help=tr("port (default: the configured one)"))
    w = sub.add_parser("watch", help=tr("keep refreshing in the terminal"))
    w.add_argument("-n", "--seconds", type=int, default=300)
    sub.add_parser("connect", help=tr("sign in another Claude account (opens the browser)"))
    sub.add_parser("sync", help=tr("share ~/.claude's configuration and conversations with every account"))
    sub.add_parser("config", help=tr("create or show the configuration file"))
    sub.add_parser("notice", help=tr("(Claude Code hook) tell the session when it should change account"))
    return p


COMMANDS: dict[str | None, Callable[[argparse.Namespace, Config], int]] = {
    None: cmd_status,
    "status": cmd_status,
    "current": cmd_current,
    "switch": cmd_switch,
    "model": cmd_model,
    "effort": cmd_effort,
    "panel": cmd_panel,
    "autostart": cmd_autostart,
    "autoswitch": cmd_autoswitch,
    "lang": cmd_lang,
    "server": cmd_server,
    "watch": cmd_watch,
    "connect": cmd_connect,
    "sync": cmd_sync,
    "config": cmd_config,
    "notice": cmd_notice,
}


def _setup_console() -> None:
    """Windows: UTF-8 output (bars and symbols) and ANSI colours on old consoles."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    os.system("")  # turns on ANSI escape processing


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    _setup_console()
    cfg = load_config()
    i18n.set_language(cfg.language)
    if argv[:1] == ["claude"]:  # before argparse: the arguments belong to Claude Code, not to us
        return launch_claude(argv[1:])
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.cmd](args, cfg)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
