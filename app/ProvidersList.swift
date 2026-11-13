import SwiftUI

/// The compact providers table: a line naming each source, then its limits with how much is free.
struct ProvidersList: View {
    @Environment(\.strings) private var strings
    let rows: [ProviderRow]

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                ColumnHeader(title: strings("colLimit"))
                    .frame(maxWidth: .infinity, alignment: .leading)
                ColumnHeader(title: strings("colFree"))
                    .frame(width: AccountsList.freeWidth, alignment: .leading)
            }
            .modifier(TableCell(kind: .header))
            ForEach(rows) { row in
                if row.isFirst {
                    SourceName(row: row)
                        .modifier(TableCell(kind: .group, ruled: row.id != rows.first?.id))
                }
                ProviderLine(row: row)
                    // the rule is above the source's name, not between its limits
                    .modifier(TableCell(kind: row.isFirst ? .row : .sub, ruled: false))
            }
        }
        .tableFrame()
    }
}

struct ProviderLine: View {
    let row: ProviderRow

    var body: some View {
        if case .error = row.value {
            ProviderValue(value: row.value)
        } else {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(row.limit)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: .infinity, alignment: .leading)
                ProviderValue(value: row.value)
                    .frame(width: AccountsList.freeWidth, alignment: .trailing)
            }
        }
    }
}
