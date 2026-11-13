import SwiftUI

/// The compact accounts table: one line per account with its tightest limit. The whole line of an account that
/// is not in use switches to it.
struct AccountsList: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    /// Width of the "Free" column: a compact meter.
    static let freeWidth = 92.0
    let accounts: [Payload.Account]

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                ColumnHeader(title: "#")
                    .frame(width: 16, alignment: .leading)
                ColumnHeader(title: strings("colAccount"))
                    .frame(maxWidth: .infinity, alignment: .leading)
                ColumnHeader(title: strings("colFree"))
                    .frame(width: Self.freeWidth, alignment: .leading)
            }
            .modifier(TableCell(kind: .header))
            ForEach(accounts) { account in
                Button {
                    monitor.switchAccount(account.n)
                } label: {
                    AccountLine(account: account)
                        .modifier(TableCell(ruled: account.id != accounts.first?.id, highlighted: account.current))
                }
                .buttonStyle(RowButtonStyle())
                .disabled(account.current)
                .accessibilityAddTraits(account.current ? .isSelected : [])
                .accessibilityHint(account.current ? "" : strings("use"))
            }
        }
        .tableFrame()
    }
}

struct AccountLine: View {
    @Environment(\.strings) private var strings
    let account: Payload.Account

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            AccountNumber(account: account)
                .frame(width: 16, alignment: .leading)
            AccountName(account: account, isBest: false)
                .frame(maxWidth: .infinity, alignment: .leading)
            Group {
                if let score = account.score {
                    Meter(free: score)
                } else {
                    Text(strings("failed"))
                        .foregroundStyle(Theme.bad)
                }
            }
            .frame(width: AccountsList.freeWidth, alignment: .trailing)
        }
    }
}
