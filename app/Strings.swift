import Foundation

/// Interface text in the language chosen in the panel (`payload.lang`).
/// Labels and errors that come from the server arrive already translated.
struct Strings {
    let lang: String

    /// Looks up `key` and fills its `{placeholders}`.
    func callAsFunction(_ key: String, _ values: [String: String] = [:]) -> String {
        var text = Self.table[lang]?[key] ?? Self.table["en"]?[key] ?? key
        for (name, value) in values {
            text = text.replacing("{\(name)}", with: value)
        }
        return text
    }

    /// The locale for dates: the panel's language, always on the 24-hour clock.
    var locale: Locale {
        var components = Locale.Components(identifier: lang == "zh" ? "zh-CN" : lang)
        components.hourCycle = .zeroToTwentyThree
        return Locale(components: components)
    }

    /// "in 2h 30min · Thu 14:30", or nothing when the limit has no reset time.
    func countdown(to date: Date?, now: Date = .now) -> String {
        guard let date else { return "" }
        let seconds = max(0, Int(date.timeIntervalSince(now)))
        let (days, hours, minutes) = (seconds / 86400, seconds % 86400 / 3600, seconds % 3600 / 60)
        let left =
            if days > 0 {
                "\(days)\(self("d")) \(hours)\(self("h"))"
            } else if hours > 0 {
                "\(hours)\(self("h")) \(minutes)\(self("min"))"
            } else {
                "\(minutes)\(self("min"))"
            }
        let when = date.formatted(
            .dateTime.weekday(.abbreviated).hour(.twoDigits(amPM: .omitted)).minute(.twoDigits).locale(locale))
        return self("resetsIn", ["left": left, "when": when])
    }

    /// A number as the web panel prints it ("95", "1.5", "12.40"): never with localised separators.
    static func number(_ value: Double, decimals: ClosedRange<Int> = 0...2) -> String {
        value.formatted(
            .number.precision(.fractionLength(decimals)).grouping(.never).locale(Locale(identifier: "en_US_POSIX")))
    }

    static func percent(_ value: Double) -> String { String(Int(value.rounded())) }

    /// Keys that some language lacks. `--snapshot` fails on them, so a missing translation does not go unnoticed.
    static var missingKeys: [String] {
        let all = Set(table.values.flatMap(\.keys))
        return table.flatMap { lang, texts in all.subtracting(texts.keys).map { "\(lang).\($0)" } }.sorted()
    }

    // Copied from the I18N table in src/usage_monitor/web/panel.html (the source of truth), plus the menu bar text.
    static let table: [String: [String: String]] = [
        "en": [
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
            "connect": "+ Connect account",
            "connectWaiting": "Waiting for the sign-in in your browser…",
            "connectDone": "Connected #{n} ({email})",
            "connectDup": "{email} is already connected as #{n}",
            "connectCancelled": "Sign-in cancelled",
            "connectFailed": "Could not connect: {error}",
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
            "menuOpen": "Open panel",
            "menuSwitch": "Switch to the account with the most room",
            "menuRefresh": "Refresh now",
            "menuQuit": "Quit",
            "language": "Language",
            "serverMissing": "`usage` was not found. Install it with: uv tool install usage-monitor",
            "serverFailed": "Could not start the server",
        ],
        "es": [
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
            "connect": "+ Conectar cuenta",
            "connectWaiting": "Esperando el inicio de sesión en tu navegador…",
            "connectDone": "Conectada la #{n} ({email})",
            "connectDup": "{email} ya está conectada como #{n}",
            "connectCancelled": "Inicio de sesión cancelado",
            "connectFailed": "No se pudo conectar: {error}",
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
            "menuOpen": "Abrir panel",
            "menuSwitch": "Cambiar a la cuenta con más margen",
            "menuRefresh": "Actualizar ahora",
            "menuQuit": "Salir",
            "language": "Idioma",
            "serverMissing": "No encuentro `usage`. Instálalo con: uv tool install usage-monitor",
            "serverFailed": "No pude arrancar el servidor",
        ],
        "zh": [
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
            "connect": "+ 连接账户",
            "connectWaiting": "正在等待浏览器中的登录…",
            "connectDone": "已连接 #{n}（{email}）",
            "connectDup": "{email} 已作为 #{n} 连接",
            "connectCancelled": "登录已取消",
            "connectFailed": "无法连接：{error}",
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
            "menuOpen": "打开面板",
            "menuSwitch": "切换到余量最多的账号",
            "menuRefresh": "立即刷新",
            "menuQuit": "退出",
            "language": "语言",
            "serverMissing": "找不到 `usage`。请运行：uv tool install usage-monitor",
            "serverFailed": "无法启动服务器",
        ],
    ]
}
