import SwiftUI

/// The app's state: the latest payload from the local server, plus the actions the interface can take on it.
@MainActor
@Observable
final class Monitor {
    private(set) var payload: Payload?
    /// The last request did not reach the server; the last payload (if any) stays on screen.
    private(set) var offline = false
    private(set) var refreshing = false
    /// Transient message at the bottom of the window.
    private(set) var toast: String?
    /// Why the server could not be started: a key of `Strings` ("serverMissing" or "serverFailed").
    private(set) var problem: String?

    @ObservationIgnored private var server: Process?
    @ObservationIgnored private var toastTask: Task<Void, Never>?

    /// `live` starts the server if needed and keeps polling; without it nothing happens until `load()`.
    init(live: Bool) {
        guard live else { return }
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification, object: nil, queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated { self?.server?.terminate() }
        }
        Task { await run() }
    }

    var strings: Strings {
        let system = String(Locale.preferredLanguages.first?.prefix(2) ?? "en")
        return Strings(lang: payload?.lang ?? system)
    }

    /// Menu bar text: % free on the active account.
    var menuTitle: String {
        guard !offline else { return "USAGE ✕" }
        guard let payload, let score = payload.current?.score else { return "USAGE" }
        let low = score <= 100 - payload.alertAt
        return "\(low ? "⚠" : "⚡") \(Strings.percent(score))%"
    }

    func load() async {
        do {
            payload = try await Backend.request("api/data")
            offline = false
            if problem == "serverFailed" { problem = nil }  // another server is answering
        } catch {
            offline = true
        }
    }

    func refresh() {
        Task {
            refreshing = true
            await perform("api/refresh", Backend.Command())
            refreshing = false
        }
    }

    /// Makes account `n` the active one; without a number, the one with the most room.
    func switchAccount(_ n: Int? = nil) {
        Task {
            await perform("api/switch", Backend.Command(n: n)) { payload, strings in
                payload.current.map { strings("toastSwitch", ["n": String($0.n), "email": $0.email]) }
            }
        }
    }

    /// Opens the browser to sign another Claude account in; the payload reports how it goes.
    func connectAccount() {
        Task { await perform("api/connect", Backend.Command()) }
    }

    /// The line next to the connect button, or nil when there is nothing to say.
    var connectState: String? {
        guard let c = payload?.connect else { return nil }
        let values = ["n": c.number.map(String.init) ?? "", "email": c.email ?? "", "error": c.error ?? ""]
        let key = [
            "waiting": "connectWaiting", "connected": "connectDone", "duplicate": "connectDup",
            "cancelled": "connectCancelled", "failed": "connectFailed",
        ][c.status]
        return key.map { strings($0, values) }
    }

    func setModel(_ model: String) { set(Backend.Command(model: model)) }

    func setEffort(_ effort: String) { set(Backend.Command(effort: effort)) }

    func setLanguage(_ code: String) {
        Task { await perform("api/prefs", Backend.Command(language: code)) }
    }

    func setAutoSwitch(_ on: Bool) {
        Task {
            await perform("api/prefs", Backend.Command(autoSwitch: on)) { payload, strings in
                strings("toastAuto", ["state": strings(payload.autoSwitch ? "on" : "off")])
            }
        }
    }

    private func set(_ command: Backend.Command) {
        Task {
            await perform("api/settings", command) { payload, strings in
                strings("toastSettings", ["model": payload.settings.modelLabel, "effort": payload.settings.effort ?? ""])
            }
        }
    }

    /// Sends a command and shows its outcome: `done` words the confirmation, a failure shows the server's message.
    private func perform(
        _ path: String, _ command: Backend.Command, done: (Payload, Strings) -> String? = { _, _ in nil }
    ) async {
        do {
            let new = try await Backend.request(path, command)
            payload = new
            offline = false
            if let message = done(new, strings) { show(message) }
        } catch {
            show(error.localizedDescription)
        }
    }

    private func show(_ message: String) {
        toast = message
        AccessibilityNotification.Announcement(message).post()
        toastTask?.cancel()
        toastTask = Task {
            try? await Task.sleep(for: .seconds(4.5))
            if !Task.isCancelled { toast = nil }
        }
    }

    private func run() async {
        await load()
        if offline, !Backend.isExternal { startServer() }
        while !Task.isCancelled {
            // a server that was just started takes a moment to answer
            // a new account appears as soon as its browser sign-in ends
            let waiting = payload?.connect?.status == "waiting"
            try? await Task.sleep(for: .seconds(payload == nil ? 1 : waiting ? 3 : 30))
            await load()
        }
    }

    private func startServer() {
        guard let executable = Backend.executable else {
            problem = "serverMissing"
            return
        }
        do {
            server = try Backend.startServer(executable)
        } catch {
            problem = "serverFailed"
        }
    }
}
