import Foundation

/// The local `usage server`: where it listens, how to talk to it and how to start it.
enum Backend {
    /// `USAGE_MONITOR_PORT` points the app at a server that is already running (development, tests):
    /// the app then never starts one of its own.
    static let isExternal = ProcessInfo.processInfo.environment["USAGE_MONITOR_PORT"] != nil
    /// Also passed to `usage server --port`, so app and server always agree.
    static let port = ProcessInfo.processInfo.environment["USAGE_MONITOR_PORT"].flatMap(Int.init) ?? 8787
    /// The app posts the alerts itself (see `Notifier`): it tells the server, which then stops notifying.
    nonisolated(unsafe) static var notifies = false

    /// The body of a `POST`; only the fields that are set are sent.
    struct Command: Encodable {
        var n: Int?
        var model: String?
        var effort: String?
        var language: String?
        var autoSwitch: Bool?
    }

    struct Failure: LocalizedError, Decodable {
        let error: String
        var errorDescription: String? { error }
    }

    /// `GET` without a command, `POST` with one. The server answers the full payload, or `{error}` with a 4xx.
    static func request(_ path: String, _ command: Command? = nil) async throws -> Payload {
        guard let url = URL(string: "http://127.0.0.1:\(port)/\(path)") else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        if notifies { request.setValue("macos", forHTTPHeaderField: "X-Usage-Monitor-Notifier") }
        if let command {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            request.httpMethod = "POST"
            request.httpBody = try encoder.encode(command)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("1", forHTTPHeaderField: "X-Usage-Monitor")  // the server requires it to rule out other sites
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        if let status = (response as? HTTPURLResponse)?.statusCode, status >= 400 {
            throw (try? decoder.decode(Failure.self, from: data)) ?? Failure(error: "HTTP \(status)")
        }
        return try decoder.decode(Payload.self, from: data)
    }

    /// The `usage` executable: the copy bundled with the app first, then the usual install locations.
    static var executable: String? {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let candidates: [String?] = [
            Bundle.main.resourceURL?.appending(path: "usage").path(percentEncoded: false),
            "\(home)/.local/bin/usage", "/opt/homebrew/bin/usage", "/usr/local/bin/usage",
        ]
        return candidates.compactMap { $0 }.first(where: FileManager.default.isExecutableFile(atPath:))
    }

    /// Starts `usage server`, logging to ~/.config/usage-monitor/server.log.
    static func startServer(_ executable: String) throws -> Process {
        let logURL = FileManager.default.homeDirectoryForCurrentUser.appending(path: ".config/usage-monitor/server.log")
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let log = try? FileHandle(forWritingTo: logURL)
        _ = try? log?.seekToEnd()

        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = ["server", "--port", String(port)]
        process.standardOutput = log ?? FileHandle.nullDevice
        process.standardError = log ?? FileHandle.nullDevice
        try process.run()
        return process
    }
}
