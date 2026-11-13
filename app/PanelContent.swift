import SwiftUI

/// Everything the panel shows, top to bottom. It does not scroll by itself: the window wraps it in a scroll view
/// and `--snapshot` renders it at its full height.
struct PanelContent: View {
    let monitor: Monitor
    let compact: Bool

    var body: some View {
        let strings = monitor.strings
        VStack(alignment: .leading, spacing: 0) {
            HeaderView()
            if let payload = monitor.payload {
                if let account = payload.current, let row = payload.hotRow {
                    AlertRow(account: account, row: row, best: payload.bestAccount)
                }
                SectionTitle(title: strings("secAccounts"), note: strings("freeHint"))
                if payload.claude.isEmpty {
                    Hint(text: strings("noSessions"))
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .tableFrame()
                } else if compact {
                    AccountsList(accounts: payload.claude)
                } else {
                    AccountsTable(accounts: payload.claude, best: payload.best, labels: payload.limitLabels)
                }
                HStack(spacing: 14) {
                    Button(strings("connect")) { monitor.connectAccount() }
                        .buttonStyle(ConsoleButtonStyle())
                        .disabled(payload.connect?.status == "waiting" || payload.demo == true)
                    if let state = monitor.connectState {
                        Text(state).foregroundStyle(Theme.dim)
                    }
                }
                .padding(.top, 10)
                SectionTitle(title: strings("secProviders"))
                let rows = payload.providerRows(strings)
                if compact {
                    ProvidersList(rows: rows)
                } else {
                    ProvidersTable(rows: rows)
                    SectionTitle(title: strings("secDefaults"), note: strings("defaultsHint"))
                    DefaultsList(settings: payload.settings, autoSwitch: payload.autoSwitch, alertAt: payload.alertAt)
                }
            }
        }
        .padding(.horizontal, compact ? 12 : 20)
        .padding(.top, compact ? 12 : 20)
        .padding(.bottom, compact ? 24 : 48)
        .frame(maxWidth: Theme.maxContentWidth)
        .frame(maxWidth: .infinity)
        .font(Theme.body)
        .monospacedDigit()
        .foregroundStyle(Theme.text)
        .tint(Theme.accent)
        .environment(\.compact, compact)
        .environment(\.strings, strings)
        .environment(\.locale, strings.locale)
        .environment(monitor)
    }
}

/// "CLAUDE ACCOUNTS  % free in each limit": the title of a table.
struct SectionTitle: View {
    @Environment(\.compact) private var compact
    let title: String
    var note: String?

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(title)
                .font(Theme.mono(11, .semibold))
                .tracking(1.1)
                .textCase(.uppercase)
                .accessibilityAddTraits(.isHeader)
            if let note, !compact {
                Text(note)
                    .font(Theme.label)
            }
        }
        .foregroundStyle(Theme.dim)
        .lineLimit(1)
        .padding(.top, compact ? 18 : 30)
        .padding(.bottom, compact ? 6 : 8)
    }
}

/// Shown while the active account is over the alert threshold in a limit that blocks it.
struct AlertRow: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    let account: Payload.Account
    let row: Payload.Row
    /// The account to move to, when one has room.
    let best: Payload.Account?

    var body: some View {
        let head = Text(strings("alertHead", ["n": String(account.n), "p": Strings.percent(row.used), "label": row.label]))
            .fontWeight(.semibold)
            .foregroundStyle(Theme.bad)
        let advice =
            if let best {
                strings("alertBest", ["n": String(best.n), "p": Strings.percent(best.score ?? 0)])
            } else {
                strings("alertNone")
            }
        FlowLayout(spacing: 16, lineSpacing: 10) {
            Text("\(head) \(advice)")
                .fixedSize(horizontal: false, vertical: true)
            if let best {
                Button(strings("alertButton", ["n": String(best.n)])) { monitor.switchAccount(best.n) }
                    .buttonStyle(ConsoleButtonStyle(kind: .primary))
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.badWash)
        .border(Theme.bad)
        .padding(.top, 16)
        .accessibilityElement(children: .contain)
    }
}
