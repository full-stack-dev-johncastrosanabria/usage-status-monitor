"""Translations. The English text in the code is the key; each catalogue maps it to another language."""

from __future__ import annotations

from typing import Any

LANGUAGES = {"en": "English", "es": "Español", "zh": "简体中文"}
_language = "en"


def set_language(code: str) -> None:
    global _language  # noqa: PLW0603 — one process, one interface language
    _language = code if code in LANGUAGES else "en"


def language() -> str:
    return _language


def tr(text: str, **values: Any) -> str:
    """Translates `text` to the current language (falling back to English) and fills its placeholders."""
    translated = CATALOGS.get(_language, {}).get(text, text)
    return translated.format(**values) if values else translated


ES = {
    # http
    "invalid token; open the tool once to refresh it": "token inválido; abre la herramienta una vez para renovarlo",
    "access denied": "acceso denegado",
    "too many requests; wait a few minutes": "demasiadas consultas; espera unos minutos",
    "no connection ({reason})": "sin conexión ({reason})",
    # providers
    "Session (5h)": "Sesión (5h)",
    "Weekly (all models)": "Semanal (todos)",
    "Weekly ({model})": "Semanal ({model})",
    "Weekly": "Semanal",
    "{hours}h window": "Ventana de {hours} h",
    "Other": "Otros",
    "not signed in; open `{cmd}` and run /login": "sin sesión; abre `{cmd}` y ejecuta /login",
    "token expired; open `{cmd}` to refresh it": "token expirado; abre `{cmd}` para renovarlo",
    "not signed in; run `codex login`": "sin sesión; ejecuta `codex login`",
    "Codex uses an API key, not a ChatGPT login: there are no plan limits": (
        "Codex usa una API key, no un inicio de sesión de ChatGPT: no hay límites de plan"
    ),
    "not signed in; open `agy` and sign in": "sin sesión; abre `agy` e inicia sesión",
    "cannot read the session saved by `agy`": "no entiendo la sesión guardada por `agy`",
    "token expired; open `agy` to refresh it": "token expirado; abre `agy` para renovarlo",
    "no API key; add it with `opencode auth login` or DEEPSEEK_API_KEY": (
        "sin clave; añádela con `opencode auth login` o DEEPSEEK_API_KEY"
    ),
    "unexpected error: {error}": "error inesperado: {error}",
    "no data": "sin datos",
    # settings
    "Default": "Por defecto",
    "unknown model: {model}": "modelo desconocido: {model}",
    "unknown effort: {effort}": "esfuerzo desconocido: {effort}",
    "unknown language: {code}": "idioma desconocido: {code}",
    # alerts
    "Switch to Claude #{n} ({free:.0f}% free).": "Cambia a Claude #{n} ({free:.0f} % libre).",
    "No other account has room.": "Ninguna otra cuenta tiene margen.",
    "{name}: {label} at {used:.0f}%": "{name}: {label} al {used:.0f} %",
    "Switched to Claude #{n} automatically": "Cambio automático a Claude #{n}",
    "{email}. #{old} reached {used:.0f}% of {label}; new sessions use #{n}.": (
        "{email}. La #{old} llegó al {used:.0f} % de {label}; las sesiones nuevas usan la #{n}."
    ),
    "#{n} has {free:.0f}% free: run `usage switch` and start a new session.": (
        "La #{n} tiene {free:.0f} % libre: ejecuta `usage switch` y abre una sesión nueva."
    ),
    "No other account has room right now.": "Ninguna otra cuenta tiene margen ahora.",
    "Claude #{n} ({email}): {label} at {used:.0f}%.": "Claude #{n} ({email}): {label} al {used:.0f} %.",
    "type /exit and this conversation reopens on #{n} by itself": (
        "escribe /exit y esta conversación se reabre sola con la #{n}"
    ),
    "Account changed: reopening this conversation on {dir} in {s} s (Ctrl+C cancels)…": (
        "Cambió la cuenta: reabriendo esta conversación con {dir} en {s} s (Ctrl+C cancela)…"
    ),
    "Not available with demo data.": ("No disponible con datos de demostración."),
    "A sign-in is already open in the browser.": ("Ya hay un inicio de sesión abierto en el navegador."),
    "Sign in with the new account in the browser that opens…": (
        "Inicia sesión con la cuenta nueva en el navegador que se abre…"
    ),
    "Connected Claude #{n} ({email}).": ("Conectada Claude #{n} ({email})."),
    "{email} is already connected as #{n}.": ("{email} ya está conectada como #{n}."),
    "Sign-in cancelled; nothing was added.": ("Inicio de sesión cancelado; no se añadió nada."),
    "Could not connect: {error}": ("No se pudo conectar: {error}"),
    "sign in another Claude account (opens the browser)": ("conectar otra cuenta de Claude (abre el navegador)"),
    "Premium requests": "Solicitudes premium",
    "Chat": "Chat",
    "Completions": "Autocompletado",
    "Unlimited": "Ilimitado",
    "not signed in; run `gh auth login` or sign in to Copilot in your editor": (
        "sin sesión; ejecuta `gh auth login` o inicia sesión en Copilot en tu editor"
    ),
    "exit and run `claude --continue` to carry on this conversation with #{n}": (
        "sal y ejecuta `claude --continue` para seguir esta conversación con la #{n}"
    ),
    "new sessions will use it (run `usage sync` to continue conversations across accounts)": (
        "las sesiones nuevas la usarán (ejecuta `usage sync` para continuar conversaciones entre cuentas)"
    ),
    "You switched to Claude #{n} ({email}). This session is still on #{mine} ({mine_email}): {how}.": (
        "Cambiaste a Claude #{n} ({email}). Esta sesión sigue con la #{mine} ({mine_email}): {how}."
    ),
    # desktop / sync
    "the app": "la app",
    "its own window": "una ventana propia",
    "the browser": "el navegador",
    "{name}: not linked (the account has its own history)": "{name}: sin enlazar (la cuenta tiene historial propio)",
    # server
    "No other account has free usage right now.": "Ninguna otra cuenta tiene uso libre ahora.",
    "There is no account #{n}.": "No hay cuenta #{n}.",
    "host not allowed": "host no permitido",
    "not found": "no encontrado",
    "forbidden": "prohibido",
    "a JSON object was expected": "se esperaba un objeto JSON",
    # terminal
    "resets in {left} ({when})": "se reinicia en {left} ({when})",
    "{free:5.1f}% free": "{free:5.1f} % libre",
    "(no balance)": "(sin saldo)",
    "balance {amount:.2f} {currency}": "saldo {amount:.2f} {currency}",
    "Available usage — {when}": "Uso disponible — {when}",
    "active": "activa",
    "Claude: no sessions; sign in with `claude`": "Claude: sin sesiones; inicia sesión con `claude`",
    # cli
    "The active folder ({path}) has no Claude session.": "La carpeta activa ({path}) no tiene sesión de Claude.",
    "No other account has free usage right now; check which one resets first.": (
        "Ninguna otra cuenta tiene uso libre ahora; mira cuál se reinicia antes."
    ),
    "→ Active account: Claude #{n} {email}": "→ Cuenta activa: Claude #{n} {email}",
    "Open sessions keep their account: exit and run `claude --continue` to carry on with this one.": (
        "Las sesiones abiertas siguen con su cuenta: sal y ejecuta `claude --continue` para seguir con esta."
    ),
    "Model: {label} ({id})   Effort: {effort}": "Modelo: {label} ({id})   Esfuerzo: {effort}",
    "Available: {values}": "Disponibles: {values}",
    "Panel opened in {where} ({url}).": "Panel abierto en {where} ({url}).",
    "The server keeps running in the background and alerts at {p:.0f}%.": (
        "El servidor sigue en segundo plano y avisa al {p:.0f} %."
    ),
    "(refreshes every {s}s, Ctrl+C to quit)": "(se actualiza cada {s} s, Ctrl+C para salir)",
    "unexpected response from the server": "respuesta inesperada del servidor",
    "internal error; see the server log": "error interno; consulta el registro del servidor",
    "request body too large": "la petición es demasiado grande",
    "`{key}` must be text": "`{key}` debe ser texto",
    "`{key}` must be a whole number": "`{key}` debe ser un número entero",
    "`{key}` must be true or false": "`{key}` debe ser true o false",
    "error: port {port} is used by another program; set another `port` in the configuration.": (
        "error: otro programa usa el puerto {port}; elige otro `port` en la configuración."
    ),
    "error: the server did not start; see {path}": "error: el servidor no arrancó; consulta {path}",
    "{name}: error: {error}": "{name}: error: {error}",
    "On Windows, turn on Developer Mode to create links.": (
        "En Windows, activa el Modo de desarrollador para poder crear enlaces."
    ),
    "already in sync": "ya sincronizada",
    "Start at login enabled ({path}).": "Inicio con el sistema activado ({path}).",
    "Start at login disabled ({path}).": "Inicio con el sistema desactivado ({path}).",
    "Automatic switch: on (at {p:.0f}%, while the panel or the app is running).": (
        "Cambio automático: activado (al {p:.0f} %, mientras el panel o la app estén abiertos)."
    ),
    "Automatic switch: off.": "Cambio automático: desactivado.",
    "Created {path}": "Creado {path}",
    "error: `claude` is not on the PATH.": "error: no encuentro `claude` en el PATH.",
    "Available usage across Claude, ChatGPT, Antigravity and DeepSeek.": (
        "Uso disponible de Claude, ChatGPT, Antigravity y DeepSeek."
    ),
    "every account (the default)": "todas las cuentas (por defecto)",
    "JSON output": "salida en JSON",
    "only the active Claude account": "solo la cuenta de Claude activa",
    "change the active Claude account": "cambia la cuenta de Claude activa",
    "account number; without it, the one with the most room": "número de cuenta; sin él, la que tenga más margen",
    "run Claude Code with the active account (arguments are passed through)": (
        "ejecuta Claude Code con la cuenta activa (los argumentos se pasan tal cual)"
    ),
    "show or set Claude Code's default model": "muestra o cambia el modelo por defecto de Claude Code",
    "show or set Claude Code's default effort": "muestra o cambia el esfuerzo por defecto de Claude Code",
    "open the panel (starts the server if needed)": "abre el panel (arranca el servidor si hace falta)",
    "open the panel when you log in": "abre el panel al iniciar sesión en el sistema",
    "switch account automatically when the active one hits the threshold": (
        "cambia de cuenta automáticamente cuando la activa llega al umbral"
    ),
    "show or set the interface language": "muestra o cambia el idioma de la interfaz",
    "run the server in the foreground": "ejecuta el servidor en primer plano",
    "port (default: the configured one)": "puerto (por defecto, el configurado)",
    "keep refreshing in the terminal": "refresco continuo en la terminal",
    "share ~/.claude's configuration and conversations with every account": (
        "comparte la configuración y las conversaciones de ~/.claude con todas las cuentas"
    ),
    "create or show the configuration file": "crea o muestra el archivo de configuración",
    "(Claude Code hook) tell the session when it should change account": (
        "(hook de Claude Code) avisa a la sesión cuando debe cambiar de cuenta"
    ),
}

ZH = {
    # http
    "invalid token; open the tool once to refresh it": "令牌无效；请打开一次该工具以刷新",
    "access denied": "拒绝访问",
    "too many requests; wait a few minutes": "请求过于频繁；请稍等几分钟",
    "no connection ({reason})": "无法连接（{reason}）",
    # providers
    "Session (5h)": "会话（5 小时）",
    "Weekly (all models)": "每周（全部模型）",
    "Weekly ({model})": "每周（{model}）",
    "Weekly": "每周",
    "{hours}h window": "{hours} 小时窗口",
    "Other": "其他",
    "not signed in; open `{cmd}` and run /login": "未登录；请打开 `{cmd}` 并运行 /login",
    "token expired; open `{cmd}` to refresh it": "令牌已过期；请打开 `{cmd}` 以刷新",
    "not signed in; run `codex login`": "未登录；请运行 `codex login`",
    "Codex uses an API key, not a ChatGPT login: there are no plan limits": (
        "Codex 使用的是 API 密钥而非 ChatGPT 登录：没有套餐额度"
    ),
    "not signed in; open `agy` and sign in": "未登录；请打开 `agy` 并登录",
    "cannot read the session saved by `agy`": "无法读取 `agy` 保存的会话",
    "token expired; open `agy` to refresh it": "令牌已过期；请打开 `agy` 以刷新",
    "no API key; add it with `opencode auth login` or DEEPSEEK_API_KEY": (
        "没有 API 密钥；请用 `opencode auth login` 或 DEEPSEEK_API_KEY 添加"
    ),
    "unexpected error: {error}": "意外错误：{error}",
    "no data": "无数据",
    # settings
    "Default": "默认",
    "unknown model: {model}": "未知模型：{model}",
    "unknown effort: {effort}": "未知强度：{effort}",
    "unknown language: {code}": "未知语言：{code}",
    # alerts
    "Switch to Claude #{n} ({free:.0f}% free).": "请切换到 Claude #{n}（剩余 {free:.0f}%）。",
    "No other account has room.": "其他账号都没有余量。",
    "{name}: {label} at {used:.0f}%": "{name}：{label} 已用 {used:.0f}%",
    "Switched to Claude #{n} automatically": "已自动切换到 Claude #{n}",
    "{email}. #{old} reached {used:.0f}% of {label}; new sessions use #{n}.": (
        "{email}。#{old} 的{label}已用 {used:.0f}%；新会话将使用 #{n}。"
    ),
    "#{n} has {free:.0f}% free: run `usage switch` and start a new session.": (
        "#{n} 还剩 {free:.0f}%：请运行 `usage switch` 并开启新会话。"
    ),
    "No other account has room right now.": "目前其他账号都没有余量。",
    "Claude #{n} ({email}): {label} at {used:.0f}%.": "Claude #{n}（{email}）：{label} 已用 {used:.0f}%。",
    "type /exit and this conversation reopens on #{n} by itself": "输入 /exit，这段对话会自动用 #{n} 重新打开",
    "Account changed: reopening this conversation on {dir} in {s} s (Ctrl+C cancels)…": (
        "账户已切换：{s} 秒后用 {dir} 重新打开这段对话（Ctrl+C 取消）…"
    ),
    "Not available with demo data.": ("演示数据下不可用。"),
    "A sign-in is already open in the browser.": ("浏览器中已有一个登录正在进行。"),
    "Sign in with the new account in the browser that opens…": ("请在打开的浏览器中登录新账户…"),
    "Connected Claude #{n} ({email}).": ("已连接 Claude #{n}（{email}）。"),
    "{email} is already connected as #{n}.": ("{email} 已作为 #{n} 连接。"),
    "Sign-in cancelled; nothing was added.": ("登录已取消，未添加任何账户。"),
    "Could not connect: {error}": ("无法连接：{error}"),
    "sign in another Claude account (opens the browser)": ("登录另一个 Claude 账户（会打开浏览器）"),
    "Premium requests": "高级请求",
    "Chat": "聊天",
    "Completions": "代码补全",
    "Unlimited": "无限制",
    "not signed in; run `gh auth login` or sign in to Copilot in your editor": (
        "未登录；请运行 `gh auth login` 或在编辑器中登录 Copilot"
    ),
    "exit and run `claude --continue` to carry on this conversation with #{n}": (
        "请退出并运行 `claude --continue`，用 #{n} 继续这段对话"
    ),
    "new sessions will use it (run `usage sync` to continue conversations across accounts)": (
        "新会话将使用它（运行 `usage sync` 后可跨账号继续对话）"
    ),
    "You switched to Claude #{n} ({email}). This session is still on #{mine} ({mine_email}): {how}.": (
        "你已切换到 Claude #{n}（{email}）。本会话仍在使用 #{mine}（{mine_email}）：{how}。"
    ),
    # desktop / sync
    "the app": "应用",
    "its own window": "独立窗口",
    "the browser": "浏览器",
    "{name}: not linked (the account has its own history)": "{name}：未链接（该账号有自己的历史记录）",
    # server
    "No other account has free usage right now.": "目前其他账号都没有可用额度。",
    "There is no account #{n}.": "没有 #{n} 号账号。",
    "host not allowed": "不允许的主机",
    "not found": "未找到",
    "forbidden": "禁止访问",
    "a JSON object was expected": "需要一个 JSON 对象",
    # terminal
    "resets in {left} ({when})": "{left} 后重置（{when}）",
    "{free:5.1f}% free": "剩余 {free:5.1f}%",
    "(no balance)": "（余额不足）",
    "balance {amount:.2f} {currency}": "余额 {amount:.2f} {currency}",
    "Available usage — {when}": "可用额度 — {when}",
    "active": "当前",
    "Claude: no sessions; sign in with `claude`": "Claude：没有会话；请用 `claude` 登录",
    # cli
    "The active folder ({path}) has no Claude session.": "当前目录（{path}）没有 Claude 会话。",
    "No other account has free usage right now; check which one resets first.": (
        "目前其他账号都没有可用额度；请查看哪个账号最先重置。"
    ),
    "→ Active account: Claude #{n} {email}": "→ 当前账号：Claude #{n} {email}",
    "Open sessions keep their account: exit and run `claude --continue` to carry on with this one.": (
        "已打开的会话仍使用原账号：请退出并运行 `claude --continue` 以改用此账号继续。"
    ),
    "Model: {label} ({id})   Effort: {effort}": "模型：{label}（{id}）   强度：{effort}",
    "Available: {values}": "可选：{values}",
    "Panel opened in {where} ({url}).": "面板已在{where}中打开（{url}）。",
    "The server keeps running in the background and alerts at {p:.0f}%.": (
        "服务器在后台继续运行，用量达到 {p:.0f}% 时提醒。"
    ),
    "(refreshes every {s}s, Ctrl+C to quit)": "（每 {s} 秒刷新，按 Ctrl+C 退出）",
    "unexpected response from the server": "服务器返回了意外的响应",
    "internal error; see the server log": "内部错误；请查看服务器日志",
    "request body too large": "请求内容过大",
    "`{key}` must be text": "`{key}` 必须是文本",
    "`{key}` must be a whole number": "`{key}` 必须是整数",
    "`{key}` must be true or false": "`{key}` 必须是 true 或 false",
    "error: port {port} is used by another program; set another `port` in the configuration.": (
        "错误：端口 {port} 已被其他程序占用；请在配置中改用其他 `port`。"
    ),
    "error: the server did not start; see {path}": "错误：服务器未能启动；请查看 {path}",
    "{name}: error: {error}": "{name}：错误：{error}",
    "On Windows, turn on Developer Mode to create links.": "在 Windows 上请开启开发者模式以创建链接。",
    "already in sync": "已同步",
    "Start at login enabled ({path}).": "已启用登录时启动（{path}）。",
    "Start at login disabled ({path}).": "已停用登录时启动（{path}）。",
    "Automatic switch: on (at {p:.0f}%, while the panel or the app is running).": (
        "自动切换：已开启（达到 {p:.0f}% 时，需面板或应用保持运行）。"
    ),
    "Automatic switch: off.": "自动切换：已关闭。",
    "Created {path}": "已创建 {path}",
    "error: `claude` is not on the PATH.": "错误：PATH 中找不到 `claude`。",
    "Available usage across Claude, ChatGPT, Antigravity and DeepSeek.": (
        "查看 Claude、ChatGPT、Antigravity 和 DeepSeek 的可用额度。"
    ),
    "every account (the default)": "所有账号（默认）",
    "JSON output": "以 JSON 输出",
    "only the active Claude account": "仅当前的 Claude 账号",
    "change the active Claude account": "切换当前的 Claude 账号",
    "account number; without it, the one with the most room": "账号编号；省略则选余量最多的账号",
    "run Claude Code with the active account (arguments are passed through)": (
        "用当前账号运行 Claude Code（参数原样传递）"
    ),
    "show or set Claude Code's default model": "查看或设置 Claude Code 的默认模型",
    "show or set Claude Code's default effort": "查看或设置 Claude Code 的默认强度",
    "open the panel (starts the server if needed)": "打开面板（必要时启动服务器）",
    "open the panel when you log in": "登录系统时打开面板",
    "switch account automatically when the active one hits the threshold": "当前账号达到阈值时自动切换账号",
    "show or set the interface language": "查看或设置界面语言",
    "run the server in the foreground": "在前台运行服务器",
    "port (default: the configured one)": "端口（默认使用配置中的端口）",
    "keep refreshing in the terminal": "在终端中持续刷新",
    "share ~/.claude's configuration and conversations with every account": "让所有账号共享 ~/.claude 的配置和对话",
    "create or show the configuration file": "创建或显示配置文件",
    "(Claude Code hook) tell the session when it should change account": (
        "（Claude Code 钩子）在会话需要切换账号时提醒"
    ),
}

CATALOGS = {"es": ES, "zh": ZH}
