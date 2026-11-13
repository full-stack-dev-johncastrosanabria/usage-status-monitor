"""Pure logic of the Linux app (no GTK): interface text, formatting, the backend's location and HTTP calls."""

from __future__ import annotations

import json
import math
import os
import shutil
import socket
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_PORT = 8787
COMPACT_BELOW = 620  # px: same breakpoint as the web panel's compact media query
POLL_SECONDS = 30

# Interface text, copied from src/usage_monitor/web/panel.html (a test keeps the keys in sync).
I18N: dict[str, dict[str, str]] = {
    "en": {
        "refresh": "Refresh",
        "refreshing": "Refreshing…",
        "switchBest": "Switch to #{n} · {p}% free",
        "noBest": "No account with room",
        "online": "online",
        "offline": "offline: no connection to the local server",
        "status": "updated {ago} · checks every {m} min · alerts at {p}%",
        "justNow": "just now",
        "minAgo": "{m} min ago",
        "demo": "demo data",
        "secAccounts": "Claude accounts",
        "freeHint": "% free in each limit",
        "secProviders": "Other providers",
        "secDefaults": "Claude Code defaults",
        "defaultsHint": "apply to new sessions",
        "colAccount": "Account",
        "colPlan": "Plan",
        "colFree": "Free",
        "colResets": "Resets",
        "colSource": "Source",
        "colLimit": "Limit",
        "tagActive": "active",
        "tagBest": "most room",
        "use": "Use",
        "model": "Model",
        "moreModels": "More models",
        "effort": "Effort",
        "effortHint": "Open sessions keep their own; use /model inside them.",
        "autoSwitch": "Auto-switch",
        "on": "on",
        "off": "off",
        "autoHint": "At {p}% used, new sessions move to the account with the most room.",
        "freeAria": "{p}% free",
        "resetsIn": "in {left} · {when}",
        "balance": "Balance",
        "toppedUp": "topped up {v}",
        "granted": "granted {v}",
        "noBalance": "no balance",
        "failed": "error",
        "alertHead": "Account #{n} is at {p}% of {label}.",
        "alertBest": "#{n} has {p}% free.",
        "alertNone": "No other account has room right now.",
        "alertButton": "Switch to #{n}",
        "toastSwitch": "Active account: #{n} {email}. New claude sessions will use it.",
        "toastSettings": "Claude Code: {model} · effort {effort}",
        "toastAuto": "Auto-switch: {state}",
        "noSessions": "No Claude sessions. Sign in with `claude` and they will show up here.",
        "d": "d",
        "h": "h",
        "min": "min",
    },
    "es": {
        "refresh": "Actualizar",
        "refreshing": "Actualizando…",
        "switchBest": "Cambiar a #{n} · {p} % libre",
        "noBest": "Sin cuenta con margen",
        "online": "en línea",
        "offline": "sin conexión con el servidor local",
        "status": "actualizado {ago} · consulta cada {m} min · avisa al {p} %",
        "justNow": "hace un momento",
        "minAgo": "hace {m} min",
        "demo": "datos de ejemplo",
        "secAccounts": "Cuentas de Claude",
        "freeHint": "% libre en cada límite",
        "secProviders": "Otros proveedores",
        "secDefaults": "Valores por defecto de Claude Code",
        "defaultsHint": "se aplican a las sesiones nuevas",
        "colAccount": "Cuenta",
        "colPlan": "Plan",
        "colFree": "Libre",
        "colResets": "Se reinicia",
        "colSource": "Origen",
        "colLimit": "Límite",
        "tagActive": "activa",
        "tagBest": "más margen",
        "use": "Usar",
        "model": "Modelo",
        "moreModels": "Más modelos",
        "effort": "Esfuerzo",
        "effortHint": "Las sesiones abiertas conservan el suyo; usa /model dentro de ellas.",
        "autoSwitch": "Cambio automático",
        "on": "sí",
        "off": "no",
        "autoHint": "Al {p} % de uso, las sesiones nuevas pasan a la cuenta con más margen.",
        "freeAria": "{p} % libre",
        "resetsIn": "en {left} · {when}",
        "balance": "Saldo",
        "toppedUp": "recargado {v}",
        "granted": "regalado {v}",
        "noBalance": "sin saldo",
        "failed": "error",
        "alertHead": "La cuenta #{n} está al {p} % de {label}.",
        "alertBest": "La #{n} tiene {p} % libre.",
        "alertNone": "Ninguna otra cuenta tiene margen ahora.",
        "alertButton": "Cambiar a #{n}",
        "toastSwitch": "Cuenta activa: #{n} {email}. Las sesiones nuevas de claude la usarán.",
        "toastSettings": "Claude Code: {model} · esfuerzo {effort}",
        "toastAuto": "Cambio automático: {state}",
        "noSessions": "No hay sesiones de Claude. Inicia sesión con `claude` y aparecerán aquí.",
        "d": "d",
        "h": "h",
        "min": "min",
    },
    "zh": {
        "refresh": "刷新",
        "refreshing": "正在刷新…",
        "switchBest": "切换到 #{n} · 剩余 {p}%",
        "noBest": "没有可用余量的账号",
        "online": "在线",
        "offline": "离线：无法连接本地服务器",
        "status": "{ago}更新 · 每 {m} 分钟查询 · {p}% 时提醒",
        "justNow": "刚刚",
        "minAgo": "{m} 分钟前",
        "demo": "示例数据",
        "secAccounts": "Claude 账号",
        "freeHint": "各项额度的剩余百分比",
        "secProviders": "其他服务",
        "secDefaults": "Claude Code 默认设置",
        "defaultsHint": "对新会话生效",
        "colAccount": "账号",
        "colPlan": "套餐",
        "colFree": "剩余",
        "colResets": "重置时间",
        "colSource": "来源",
        "colLimit": "额度",
        "tagActive": "当前",
        "tagBest": "余量最多",
        "use": "使用",
        "model": "模型",
        "moreModels": "更多模型",
        "effort": "强度",
        "effortHint": "已打开的会话保持原设置；可在会话内使用 /model。",
        "autoSwitch": "自动切换",
        "on": "开",
        "off": "关",
        "autoHint": "用量达到 {p}% 时，新会话将改用余量最多的账号。",
        "freeAria": "剩余 {p}%",
        "resetsIn": "{left}后 · {when}",
        "balance": "余额",
        "toppedUp": "充值 {v}",
        "granted": "赠送 {v}",
        "noBalance": "余额不足",
        "failed": "错误",
        "alertHead": "账号 #{n} 的{label}已用 {p}%。",
        "alertBest": "#{n} 还剩 {p}%。",
        "alertNone": "目前其他账号都没有余量。",
        "alertButton": "切换到 #{n}",
        "toastSwitch": "当前账号：#{n} {email}。新的 claude 会话将使用它。",
        "toastSettings": "Claude Code：{model} · 强度 {effort}",
        "toastAuto": "自动切换：{state}",
        "noSessions": "没有 Claude 会话。用 `claude` 登录后会显示在这里。",
        "d": "天",
        "h": "小时",
        "min": "分钟",
    },
}
# Short weekday names (Monday first), so the reset time does not depend on the system locale.
WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "es": ("lun", "mar", "mié", "jue", "vie", "sáb", "dom"),
    "zh": ("周一", "周二", "周三", "周四", "周五", "周六", "周日"),
}


def tr(lang: str, key: str, **values: object) -> str:
    text = I18N.get(lang, I18N["en"]).get(key) or I18N["en"][key]
    return text.format(**values)


def whole(value: float) -> int:
    """Rounds half up, like the panel's Math.round (Python's round() rounds half to even)."""
    return math.floor(value + 0.5)


def tone(free: float) -> str:
    """The meter colour: the same thresholds as the web panel."""
    return "ok" if free > 50 else "warn" if free > 20 else "bad"


def countdown(iso: str | None, lang: str, now: datetime | None = None) -> str:
    """'in 2h 29min · Fri 00:02' (local time, 24-hour clock); empty without a reset time."""
    if not iso:
        return ""
    when = datetime.fromisoformat(iso).astimezone()
    seconds = max(0.0, (when - (now or datetime.now(UTC))).total_seconds())
    days, hours, mins = int(seconds // 86400), int(seconds % 86400 // 3600), int(seconds % 3600 // 60)
    d, h, m = (tr(lang, k) for k in ("d", "h", "min"))
    left = f"{days}{d} {hours}{h}" if days else f"{hours}{h} {mins}{m}" if hours else f"{mins}{m}"
    day = WEEKDAYS.get(lang, WEEKDAYS["en"])[when.weekday()]
    return tr(lang, "resetsIn", left=left, when=f"{day} {when:%H:%M}")


def ago(updated: str, lang: str, now: datetime | None = None) -> str:
    minutes = round(((now or datetime.now(UTC)) - datetime.fromisoformat(updated)).total_seconds() / 60)
    return tr(lang, "justNow") if minutes < 1 else tr(lang, "minAgo", m=minutes)


def hot_row(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """(active account, its most-used blocking row) when that row is at or over the alert threshold."""
    cur = next((c for c in data.get("claude", []) if c.get("current")), None)
    rows = [r for r in (cur or {}).get("rows", []) if r["blocking"] and r["used"] >= data["alert_at"]]
    return (cur, max(rows, key=lambda r: r["used"])) if cur and rows else None


def limit_labels(accounts: list[dict[str, Any]]) -> list[str]:
    """One column per limit, in the order they first appear."""
    labels: list[str] = []
    for acc in accounts:
        labels += [r["label"] for r in acc.get("rows", []) if r["label"] not in labels]
    return labels


# ---------- the backend ----------


def port_from_env() -> int | None:
    """USAGE_MONITOR_PORT points the app at a server someone else runs (it then never starts one)."""
    value = os.environ.get("USAGE_MONITOR_PORT")
    return int(value) if value else None


def server_command(app_dir: Path | None = None) -> list[str] | None:
    """How to start `usage server`: the package installed next to the app, then PATH, then ~/.local/bin."""
    app_dir = app_dir or Path(__file__).resolve().parent.parent
    if (app_dir / "usage_monitor" / "__main__.py").exists():  # the .deb layout: /usr/lib/usage-monitor/
        return [sys.executable, "-m", "usage_monitor"]  # run with PYTHONPATH=app_dir
    if exe := shutil.which("usage"):
        return [exe]
    local = Path.home() / ".local" / "bin" / "usage"
    return [str(local)] if local.exists() else None


def is_up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


class ApiError(Exception):
    """A request the server rejected (with its translated message) or could not be made."""


def call(port: int, path: str, body: dict[str, Any] | None = None, timeout: float = 30) -> dict[str, Any]:
    """GET (no body) or POST to the local server; returns the payload or raises ApiError."""
    url = f"http://127.0.0.1:{port}{path}"
    headers = {"Content-Type": "application/json", "X-Usage-Monitor": "1"}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers if data else {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result: dict[str, Any] = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read()).get("error") or e.reason
        except ValueError:
            message = e.reason
        raise ApiError(str(message)) from e
    except (OSError, ValueError) as e:
        raise ApiError(str(e)) from e
    return result
