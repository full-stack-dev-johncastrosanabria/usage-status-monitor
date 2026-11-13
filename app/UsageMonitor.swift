// macOS app: a window with the panel plus a menu bar indicator.
// The interface is the local server's web panel (`usage server`), which this app starts and stops.

import SwiftUI
import WebKit

enum Local {
    static let port = 8787  // also passed to `usage server --port`, so app and server always agree
    static let url = URL(string: "http://127.0.0.1:\(port)/")!
}

struct Payload: Decodable {
    struct Account: Decodable {
        let n: Int
        let current: Bool
        let score: Double?
    }
    let claude: [Account]
    let alert_at: Double
    let best: Int?
    let lang: String
}

/// Menu text; the language follows the one chosen in the panel.
enum Text18 {
    static let table: [String: [String: String]] = [
        "open": ["en": "Open panel", "es": "Abrir panel", "zh": "打开面板"],
        "switch": [
            "en": "Switch to the account with the most room",
            "es": "Cambiar a la cuenta con más margen",
            "zh": "切换到余量最多的账号",
        ],
        "refresh": ["en": "Refresh now", "es": "Actualizar ahora", "zh": "立即刷新"],
        "quit": ["en": "Quit", "es": "Salir", "zh": "退出"],
        "missing": [
            "en": "`usage` was not found. Install it with: uv tool install usage-monitor",
            "es": "No encuentro `usage`. Instálalo con: uv tool install usage-monitor",
            "zh": "找不到 `usage`。请运行：uv tool install usage-monitor",
        ],
        "failed": [
            "en": "Could not start the server",
            "es": "No pude arrancar el servidor",
            "zh": "无法启动服务器",
        ],
    ]

    static func of(_ key: String, _ lang: String) -> String {
        table[key]?[lang] ?? table[key]?["en"] ?? key
    }
}

@MainActor
final class Monitor: NSObject, ObservableObject, WKNavigationDelegate {
    @Published var title = "USAGE"
    @Published var problem: String?
    @Published var hasBest = false
    @Published var lang = "en"
    let webView = WKWebView()
    private var server: Process?
    private var timer: Timer?

    override init() {
        super.init()
        webView.navigationDelegate = self
        webView.underPageBackgroundColor = NSColor(red: 0.02, green: 0.027, blue: 0.05, alpha: 1)  // no white flash
        startServer()
        webView.load(URLRequest(url: Local.url))
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.poll() }
        }
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification, object: nil, queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated { self?.server?.terminate() }
        }
        Task { await poll() }
    }

    /// If the port is already taken (e.g. by `usage panel`), the child exits by itself and that server is used.
    private func startServer() {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let candidates = ["\(home)/.local/bin/usage", "/opt/homebrew/bin/usage", "/usr/local/bin/usage"]
        guard let exe = candidates.first(where: FileManager.default.isExecutableFile(atPath:)) else {
            problem = "missing"
            return
        }
        let logURL = URL(fileURLWithPath: "\(home)/.config/usage-monitor/server.log")
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let log = try? FileHandle(forWritingTo: logURL)
        _ = try? log?.seekToEnd()

        let process = Process()
        process.executableURL = URL(fileURLWithPath: exe)
        process.arguments = ["server", "--port", String(Local.port)]
        process.standardOutput = log ?? FileHandle.nullDevice
        process.standardError = log ?? FileHandle.nullDevice
        do {
            try process.run()
            server = process
        } catch {
            problem = "failed"
        }
    }

    func poll() async {
        do {
            let (data, _) = try await URLSession.shared.data(from: Local.url.appendingPathComponent("api/data"))
            let payload = try JSONDecoder().decode(Payload.self, from: data)
            hasBest = payload.best != nil
            lang = payload.lang
            if let score = payload.claude.first(where: \.current)?.score {
                let low = score <= 100 - payload.alert_at
                title = "\(low ? "⚠" : "⚡") \(Int(score.rounded()))%"
            } else {
                title = "USAGE"
            }
            if problem == "failed" { problem = nil }  // another server is answering
        } catch {
            title = "USAGE ✕"
        }
    }

    func post(_ path: String) async {
        var request = URLRequest(url: Local.url.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("1", forHTTPHeaderField: "X-Usage-Monitor")  // the server requires it to rule out other sites
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{}".utf8)
        _ = try? await URLSession.shared.data(for: request)
        await poll()
        webView.reload()
    }

    // The server takes a moment to start: retry until it answers.
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { webView.load(URLRequest(url: Local.url)) }
    }
}

struct WebPanel: NSViewRepresentable {
    let webView: WKWebView
    func makeNSView(context: Context) -> WKWebView { webView }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}

struct MenuContent: View {
    @ObservedObject var monitor: Monitor
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        if let problem = monitor.problem {
            Text(Text18.of(problem, monitor.lang))
            Divider()
        }
        Button(Text18.of("open", monitor.lang)) {
            openWindow(id: "panel")
            NSApp.activate(ignoringOtherApps: true)
        }
        Button(Text18.of("switch", monitor.lang)) { Task { await monitor.post("api/switch") } }
            .disabled(!monitor.hasBest)
        Button(Text18.of("refresh", monitor.lang)) { Task { await monitor.post("api/refresh") } }
        Divider()
        Button(Text18.of("quit", monitor.lang)) { NSApp.terminate(nil) }.keyboardShortcut("q")
    }
}

@main
struct UsageMonitorApp: App {
    @StateObject private var monitor = Monitor()

    var body: some Scene {
        Window("USAGE // MONITOR", id: "panel") {
            WebPanel(webView: monitor.webView)
                .frame(minWidth: 720, minHeight: 520)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 1280, height: 880)

        MenuBarExtra {
            MenuContent(monitor: monitor)
        } label: {
            Text(monitor.title)
        }
    }
}
