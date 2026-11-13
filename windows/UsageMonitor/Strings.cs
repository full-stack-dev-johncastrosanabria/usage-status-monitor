using System.Globalization;

namespace UsageMonitor;

/// <summary>
/// Interface text: the same table as the web panel (src/usage_monitor/web/panel.html), plus the tray menu.
/// Labels and errors that come from the server arrive already translated.
/// </summary>
static class Strings
{
    static string lang = "en";

    public static string Lang
    {
        get => lang;
        set => lang = Table.ContainsKey(value) ? value : "en";
    }

    public static CultureInfo Culture => CultureInfo.GetCultureInfo(lang switch { "es" => "es-ES", "zh" => "zh-CN", _ => "en-US" });

    public static string T(string key, params (string Name, object Value)[] vars)
    {
        var text = Table[lang].GetValueOrDefault(key) ?? Table["en"][key];
        foreach (var (name, value) in vars)
            text = text.Replace("{" + name + "}", Convert.ToString(value, CultureInfo.InvariantCulture));
        return text;
    }

    /// <summary>Keys that a translation lacks; checked by `--snapshot`, so a build with a gap fails loudly.</summary>
    public static string[] Missing() =>
        [.. Table.SelectMany(t => Table["en"].Keys.Except(t.Value.Keys).Select(k => $"{t.Key}:{k}"))];

    static readonly Dictionary<string, Dictionary<string, string>> Table = new()
    {
        ["en"] = new()
        {
            ["refresh"] = "Refresh",
            ["refreshing"] = "Refreshing…",
            ["switchBest"] = "Switch to #{n} · {p}% free",
            ["noBest"] = "No account with room",
            ["online"] = "online",
            ["offline"] = "offline: no connection to the local server",
            ["status"] = "updated {ago} · checks every {m} min · alerts at {p}%",
            ["justNow"] = "just now",
            ["minAgo"] = "{m} min ago",
            ["demo"] = "demo data",
            ["secAccounts"] = "Claude accounts",
            ["freeHint"] = "% free in each limit",
            ["secProviders"] = "Other providers",
            ["secDefaults"] = "Claude Code defaults",
            ["defaultsHint"] = "apply to new sessions",
            ["colAccount"] = "Account",
            ["colPlan"] = "Plan",
            ["colFree"] = "Free",
            ["colResets"] = "Resets",
            ["colSource"] = "Source",
            ["colLimit"] = "Limit",
            ["tagActive"] = "active",
            ["tagBest"] = "most room",
            ["use"] = "Use",
            ["model"] = "Model",
            ["moreModels"] = "More models",
            ["effort"] = "Effort",
            ["effortHint"] = "Open sessions keep their own; use /model inside them.",
            ["autoSwitch"] = "Auto-switch",
            ["on"] = "on",
            ["off"] = "off",
            ["autoHint"] = "At {p}% used, new sessions move to the account with the most room.",
            ["freeAria"] = "{p}% free",
            ["resetsIn"] = "in {left} · {when}",
            ["balance"] = "Balance",
            ["toppedUp"] = "topped up {v}",
            ["granted"] = "granted {v}",
            ["noBalance"] = "no balance",
            ["failed"] = "error",
            ["alertHead"] = "Account #{n} is at {p}% of {label}.",
            ["alertBest"] = "#{n} has {p}% free.",
            ["alertNone"] = "No other account has room right now.",
            ["alertButton"] = "Switch to #{n}",
            ["toastSwitch"] = "Active account: #{n} {email}. New claude sessions will use it.",
            ["toastSettings"] = "Claude Code: {model} · effort {effort}",
            ["toastAuto"] = "Auto-switch: {state}",
            ["noSessions"] = "No Claude sessions. Sign in with `claude` and they will show up here.",
            ["d"] = "d",
            ["h"] = "h",
            ["min"] = "min",
            // Only in the desktop apps.
            ["trayOpen"] = "Open",
            ["traySwitch"] = "Switch to the account with the most room",
            ["trayRefresh"] = "Refresh now",
            ["trayQuit"] = "Quit",
            ["missing"] = "usage.exe was not found: put it next to this app or install `usage` (see the README)",
            ["startFailed"] = "could not start the local server",
        },
        ["es"] = new()
        {
            ["refresh"] = "Actualizar",
            ["refreshing"] = "Actualizando…",
            ["switchBest"] = "Cambiar a #{n} · {p} % libre",
            ["noBest"] = "Sin cuenta con margen",
            ["online"] = "en línea",
            ["offline"] = "sin conexión con el servidor local",
            ["status"] = "actualizado {ago} · consulta cada {m} min · avisa al {p} %",
            ["justNow"] = "hace un momento",
            ["minAgo"] = "hace {m} min",
            ["demo"] = "datos de ejemplo",
            ["secAccounts"] = "Cuentas de Claude",
            ["freeHint"] = "% libre en cada límite",
            ["secProviders"] = "Otros proveedores",
            ["secDefaults"] = "Valores por defecto de Claude Code",
            ["defaultsHint"] = "se aplican a las sesiones nuevas",
            ["colAccount"] = "Cuenta",
            ["colPlan"] = "Plan",
            ["colFree"] = "Libre",
            ["colResets"] = "Se reinicia",
            ["colSource"] = "Origen",
            ["colLimit"] = "Límite",
            ["tagActive"] = "activa",
            ["tagBest"] = "más margen",
            ["use"] = "Usar",
            ["model"] = "Modelo",
            ["moreModels"] = "Más modelos",
            ["effort"] = "Esfuerzo",
            ["effortHint"] = "Las sesiones abiertas conservan el suyo; usa /model dentro de ellas.",
            ["autoSwitch"] = "Cambio automático",
            ["on"] = "sí",
            ["off"] = "no",
            ["autoHint"] = "Al {p} % de uso, las sesiones nuevas pasan a la cuenta con más margen.",
            ["freeAria"] = "{p} % libre",
            ["resetsIn"] = "en {left} · {when}",
            ["balance"] = "Saldo",
            ["toppedUp"] = "recargado {v}",
            ["granted"] = "regalado {v}",
            ["noBalance"] = "sin saldo",
            ["failed"] = "error",
            ["alertHead"] = "La cuenta #{n} está al {p} % de {label}.",
            ["alertBest"] = "La #{n} tiene {p} % libre.",
            ["alertNone"] = "Ninguna otra cuenta tiene margen ahora.",
            ["alertButton"] = "Cambiar a #{n}",
            ["toastSwitch"] = "Cuenta activa: #{n} {email}. Las sesiones nuevas de claude la usarán.",
            ["toastSettings"] = "Claude Code: {model} · esfuerzo {effort}",
            ["toastAuto"] = "Cambio automático: {state}",
            ["noSessions"] = "No hay sesiones de Claude. Inicia sesión con `claude` y aparecerán aquí.",
            ["d"] = "d",
            ["h"] = "h",
            ["min"] = "min",
            ["trayOpen"] = "Abrir",
            ["traySwitch"] = "Cambiar a la cuenta con más margen",
            ["trayRefresh"] = "Actualizar ahora",
            ["trayQuit"] = "Salir",
            ["missing"] = "no se encontró usage.exe: ponlo junto a esta aplicación o instala `usage` (consulta el README)",
            ["startFailed"] = "no se pudo arrancar el servidor local",
        },
        ["zh"] = new()
        {
            ["refresh"] = "刷新",
            ["refreshing"] = "正在刷新…",
            ["switchBest"] = "切换到 #{n} · 剩余 {p}%",
            ["noBest"] = "没有可用余量的账号",
            ["online"] = "在线",
            ["offline"] = "离线：无法连接本地服务器",
            ["status"] = "{ago}更新 · 每 {m} 分钟查询 · {p}% 时提醒",
            ["justNow"] = "刚刚",
            ["minAgo"] = "{m} 分钟前",
            ["demo"] = "示例数据",
            ["secAccounts"] = "Claude 账号",
            ["freeHint"] = "各项额度的剩余百分比",
            ["secProviders"] = "其他服务",
            ["secDefaults"] = "Claude Code 默认设置",
            ["defaultsHint"] = "对新会话生效",
            ["colAccount"] = "账号",
            ["colPlan"] = "套餐",
            ["colFree"] = "剩余",
            ["colResets"] = "重置时间",
            ["colSource"] = "来源",
            ["colLimit"] = "额度",
            ["tagActive"] = "当前",
            ["tagBest"] = "余量最多",
            ["use"] = "使用",
            ["model"] = "模型",
            ["moreModels"] = "更多模型",
            ["effort"] = "强度",
            ["effortHint"] = "已打开的会话保持原设置；可在会话内使用 /model。",
            ["autoSwitch"] = "自动切换",
            ["on"] = "开",
            ["off"] = "关",
            ["autoHint"] = "用量达到 {p}% 时，新会话将改用余量最多的账号。",
            ["freeAria"] = "剩余 {p}%",
            ["resetsIn"] = "{left}后 · {when}",
            ["balance"] = "余额",
            ["toppedUp"] = "充值 {v}",
            ["granted"] = "赠送 {v}",
            ["noBalance"] = "余额不足",
            ["failed"] = "错误",
            ["alertHead"] = "账号 #{n} 的{label}已用 {p}%。",
            ["alertBest"] = "#{n} 还剩 {p}%。",
            ["alertNone"] = "目前其他账号都没有余量。",
            ["alertButton"] = "切换到 #{n}",
            ["toastSwitch"] = "当前账号：#{n} {email}。新的 claude 会话将使用它。",
            ["toastSettings"] = "Claude Code：{model} · 强度 {effort}",
            ["toastAuto"] = "自动切换：{state}",
            ["noSessions"] = "没有 Claude 会话。用 `claude` 登录后会显示在这里。",
            ["d"] = "天",
            ["h"] = "小时",
            ["min"] = "分钟",
            ["trayOpen"] = "打开",
            ["traySwitch"] = "切换到余量最多的账号",
            ["trayRefresh"] = "立即刷新",
            ["trayQuit"] = "退出",
            ["missing"] = "找不到 usage.exe：请把它放在本程序旁边，或安装 `usage`（见 README）",
            ["startFailed"] = "无法启动本地服务器",
        },
    };
}
