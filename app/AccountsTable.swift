import SwiftUI

/// The Claude accounts, one per row, with a column per limit.
struct AccountsTable: View {
    @Environment(\.strings) private var strings
    let accounts: [Payload.Account]
    let best: Int?
    /// The limit columns (`Payload.limitLabels`).
    let labels: [String]

    var body: some View {
        DataTable(columns: [.fit, .grow, .grow] + labels.map { _ in .grow } + [.fit]) {
            Group {
                ColumnHeader(title: "#")
                ColumnHeader(title: strings("colAccount"))
                ColumnHeader(title: strings("colPlan"))
                ForEach(labels, id: \.self) { label in
                    ColumnHeader(title: label)
                }
                ColumnHeader(title: "")
            }
            .modifier(TableCell(kind: .header))
            ForEach(accounts) { account in
                AccountRow(
                    account: account, labels: labels, isBest: account.n == best, isFirst: account.id == accounts.first?.id)
            }
        }
    }
}

/// The cells of one account, in column order.
struct AccountRow: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    let account: Payload.Account
    let labels: [String]
    let isBest: Bool
    let isFirst: Bool

    var body: some View {
        let cell = TableCell(ruled: !isFirst, highlighted: account.current)
        AccountNumber(account: account)
            .padding(.trailing, -10)
            .modifier(cell)
        AccountName(account: account, isBest: isBest)
            .modifier(cell)
        Text(account.plan ?? "")
            .foregroundStyle(Theme.dim)
            .modifier(cell)
        if let error = account.error {
            ErrorText(message: error)
                .modifier(cell)
                .tableSpan(labels.count)
        } else {
            ForEach(labels, id: \.self) { label in
                LimitCell(row: account.rows?.first { $0.label == label })
                    .modifier(cell)
            }
        }
        Button(strings("use"), action: use)
            .buttonStyle(ConsoleButtonStyle())
            // the active account keeps the slot, so every row is as tall
            .opacity(account.current ? 0 : 1)
            .disabled(account.current)
            .accessibilityHidden(account.current)
            .modifier(TableCell(ruled: !isFirst, highlighted: account.current, alignment: .topTrailing))
    }

    private func use() { monitor.switchAccount(account.n) }
}

struct AccountNumber: View {
    let account: Payload.Account

    var body: some View {
        Text(String(account.n))
            .fontWeight(account.current ? .semibold : .regular)
            .foregroundStyle(account.current ? Theme.accent : Theme.dim)
    }
}

/// The email and what is special about the account. The compact layout only keeps "active".
struct AccountName: View {
    @Environment(\.strings) private var strings
    @Environment(\.compact) private var compact
    let account: Payload.Account
    let isBest: Bool

    var body: some View {
        let showsBest = isBest && !compact
        VStack(alignment: .leading, spacing: 3) {
            Text(account.email)
                .foregroundStyle(Theme.bright)
                .lineLimit(1)
                .truncationMode(.middle)
                .help(account.email)
            if account.current || showsBest {
                HStack(spacing: 6) {
                    if account.current { Tag(text: strings("tagActive"), color: Theme.accent) }
                    if showsBest { Tag(text: strings("tagBest")) }
                }
            }
        }
        .frame(maxWidth: 300, alignment: .leading)
    }
}

/// One limit of one account: how much is free and when it resets. Empty when the account does not have it.
struct LimitCell: View {
    @Environment(\.strings) private var strings
    let row: Payload.Row?

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let row {
                Meter(free: row.free)
                Text(strings.countdown(to: row.resetDate))
                    .font(Theme.small)
                    .foregroundStyle(Theme.dim)
                    .lineLimit(1)
                    .padding(.leading, Meter.percentWidth + 10)
            }
        }
        .accessibilityElement(children: .combine)
    }
}
