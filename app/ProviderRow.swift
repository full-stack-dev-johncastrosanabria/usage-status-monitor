import Foundation

/// One line of the "Other providers" table: a limit (or the balance) of a source other than Claude.
struct ProviderRow: Identifiable {
    enum Value {
        /// % free.
        case meter(Double)
        /// A balance; `spendable` is false when it cannot be used.
        case money(String, spendable: Bool)
        /// The source failed; this is all there is to show.
        case error(String)
    }

    let id: String
    let source: String
    /// The plan or the account, next to the source's name.
    let note: String
    /// The first row of its source: the only one that names it.
    let isFirst: Bool
    let limit: String
    let value: Value
    /// When it resets, or what the balance is made of.
    let detail: String
}

extension Payload {
    /// ChatGPT/Codex, Antigravity (a row per model, named after its group) and DeepSeek, in that order.
    func providerRows(_ strings: Strings) -> [ProviderRow] {
        rows("ChatGPT / Codex", codex, strings) { $0.label }
            + rows("Antigravity", antigravity, strings) { row in row.group.map { "\($0) · \(row.label)" } ?? row.label }
            + balanceRows(strings)
    }

    private func rows(_ source: String, _ usage: Usage, _ strings: Strings, label: (Row) -> String) -> [ProviderRow] {
        let note = usage.plan ?? ""
        if let error = usage.error {
            return [ProviderRow(id: source, source: source, note: note, isFirst: true, limit: "", value: .error(error), detail: "")]
        }
        return (usage.rows ?? []).enumerated().map { index, row in
            ProviderRow(
                id: "\(source)/\(index)", source: source, note: note, isFirst: index == 0, limit: label(row),
                value: .meter(row.free), detail: strings.countdown(to: row.resetDate))
        }
    }

    private func balanceRows(_ strings: Strings) -> [ProviderRow] {
        let source = "DeepSeek API"
        if let error = deepseek.error {
            return [ProviderRow(id: source, source: source, note: "", isFirst: true, limit: "", value: .error(error), detail: "")]
        }
        let spendable = deepseek.available ?? true
        return (deepseek.balances ?? []).enumerated().map { index, balance in
            let toppedUp = strings("toppedUp", ["v": Strings.number(balance.toppedUp, decimals: 2...2)])
            let granted = strings("granted", ["v": Strings.number(balance.granted, decimals: 2...2)])
            return ProviderRow(
                id: "\(source)/\(index)", source: source, note: "", isFirst: index == 0, limit: strings("balance"),
                value: .money("\(Strings.number(balance.total, decimals: 2...2)) \(balance.currency)", spendable: spendable),
                detail: spendable ? "\(toppedUp) · \(granted)" : strings("noBalance"))
        }
    }
}
