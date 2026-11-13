import Foundation

/// What `GET /api/data` and every `POST` return (see `to_json` in src/usage_monitor/snapshot.py).
/// A source that failed carries `error` instead of its data, so everything specific to a source is optional.
struct Payload: Decodable {
    /// One usage window ("Session (5h)", "Weekly", a model's quota...).
    struct Row: Decodable, Identifiable {
        let label: String
        let used: Double
        let free: Double
        let reset: String?
        let group: String?
        /// Whether running out of it stops the account; the others are shown smaller.
        let blocking: Bool

        var id: String { label }
        var resetDate: Date? { Payload.date(reset) }
    }

    struct Account: Decodable, Identifiable {
        let n: Int
        let email: String
        let current: Bool
        let plan: String?
        let rows: [Row]?
        /// % free in the tightest blocking window.
        let score: Double?
        let error: String?

        var id: Int { n }
    }

    struct Usage: Decodable {
        let plan: String?
        let rows: [Row]?
        let score: Double?
        let error: String?

    }

    struct Balance: Decodable, Identifiable {
        let currency: String
        let total: Double
        let granted: Double
        let toppedUp: Double

        var id: String { currency }
    }

    struct Credits: Decodable {
        let available: Bool?
        let balances: [Balance]?
        let error: String?
    }

    struct Model: Decodable, Identifiable {
        let id: String
        let label: String
        /// Listed under "More models".
        let more: Bool
    }

    struct Settings: Decodable {
        let model: String?
        let effort: String?
        let models: [Model]?
        let efforts: [String]?
        let error: String?

        var modelLabel: String { models?.first { $0.id == model }?.label ?? model ?? "" }
    }

    let updated: String
    let claude: [Account]
    let codex: Usage
    let antigravity: Usage
    let deepseek: Credits
    /// Number of the account with the most room, when one beats the active account.
    let best: Int?
    /// % used from which the server alerts (and switches, if automatic switching is on).
    let alertAt: Double
    /// Seconds between two fetches on the server.
    let every: Double
    let settings: Settings
    let autoSwitch: Bool
    let lang: String
    let languages: [String: String]
    /// The server is showing canned data (`USAGE_MONITOR_DEMO`).
    let demo: Bool?

    var current: Account? { claude.first(where: \.current) }
    var bestAccount: Account? { claude.first { $0.n == best } }
    var updatedDate: Date? { Payload.date(updated) }

    /// The limits the Claude accounts have, in order of first appearance: the columns of their table.
    var limitLabels: [String] {
        var labels: [String] = []
        for row in claude.flatMap({ $0.rows ?? [] }) where !labels.contains(row.label) {
            labels.append(row.label)
        }
        return labels
    }

    /// The blocking window of the active account that is furthest over the alert threshold, if any.
    var hotRow: Row? {
        current?.rows?.filter { $0.blocking && $0.used >= alertAt }.max { $0.used < $1.used }
    }

    /// Python's `isoformat()`: fractional seconds are there unless they are exactly zero.
    static func date(_ text: String?) -> Date? {
        guard let text else { return nil }
        return (try? Date.ISO8601FormatStyle(includingFractionalSeconds: true).parse(text))
            ?? (try? Date.ISO8601FormatStyle().parse(text))
    }
}
