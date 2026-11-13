import SwiftUI

/// The sources other than Claude, one row per limit; each source is named once, on its first row.
struct ProvidersTable: View {
    @Environment(\.strings) private var strings
    let rows: [ProviderRow]

    var body: some View {
        DataTable(columns: [.grow, .grow, .grow, .grow]) {
            Group {
                ColumnHeader(title: strings("colSource"))
                ColumnHeader(title: strings("colLimit"))
                ColumnHeader(title: strings("colFree"))
                ColumnHeader(title: strings("colResets"))
            }
            .modifier(TableCell(kind: .header))
            ForEach(rows) { row in
                ProviderCells(row: row, isFirst: row.id == rows.first?.id)
            }
        }
    }
}

/// The cells of one row, in column order.
struct ProviderCells: View {
    let row: ProviderRow
    let isFirst: Bool

    var body: some View {
        let cell = TableCell(kind: row.isFirst ? .row : .sub, ruled: !isFirst)
        SourceName(row: row)
            .opacity(row.isFirst ? 1 : 0)
            .accessibilityHidden(!row.isFirst)
            .modifier(cell)
        if case .error = row.value {
            ProviderValue(value: row.value)
                .modifier(cell)
                .tableSpan(3)
        } else {
            Text(row.limit)
                .lineLimit(1)
                .modifier(cell)
            ProviderValue(value: row.value)
                .modifier(cell)
            Text(row.detail)
                .lineLimit(1)
                .modifier(cell)
        }
    }
}

/// "ChatGPT / Codex  plus": the source and, dimmer, its plan. The compact layout drops the plan.
struct SourceName: View {
    @Environment(\.compact) private var compact
    let row: ProviderRow

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(row.source)
                .foregroundStyle(Theme.bright)
            if !compact, !row.note.isEmpty {
                Text(row.note)
                    .font(Theme.small)
                    .foregroundStyle(Theme.dim)
            }
        }
        .lineLimit(1)
        .help(row.note)
    }
}

struct ProviderValue: View {
    let value: ProviderRow.Value

    var body: some View {
        switch value {
        case .meter(let free):
            Meter(free: free)
        case .money(let amount, let spendable):
            Text(amount)
                .fontWeight(.semibold)
                .foregroundStyle(spendable ? Theme.accent : Theme.bad)
                .lineLimit(1)
        case .error(let message):
            ErrorText(message: message)
        }
    }
}
