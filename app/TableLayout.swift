import SwiftUI

/// An HTML-like table: the children are its cells, row by row; every column is as wide as its widest cell and
/// every row as tall as its tallest. Each cell is offered its whole slot, so it can paint a background or a rule.
struct TableLayout: Layout {
    enum Column {
        /// As wide as its content, never more.
        case fit
        /// As wide as its content, plus a share of the room the table has to spare.
        case grow
    }

    let columns: [Column]

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let widths = columnWidths(subviews, width: proposal.width.map(Double.init))
        let heights = rowHeights(subviews, widths: widths)
        return CGSize(width: widths.reduce(0, +), height: heights.reduce(0, +))
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let widths = columnWidths(subviews, width: bounds.width)
        let heights = rowHeights(subviews, widths: widths)
        for (cell, subview) in zip(cells(subviews), subviews) {
            let x = widths[..<cell.column].reduce(bounds.minX, +)
            let y = heights[..<cell.row].reduce(bounds.minY, +)
            let width = widths[cell.column..<cell.column + cell.span].reduce(0, +)
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(width: width, height: heights[cell.row]))
        }
    }

    /// Where each child goes: cells fill a row left to right, a cell with `tableSpan(n)` takes n columns.
    private func cells(_ subviews: Subviews) -> [(row: Int, column: Int, span: Int)] {
        var cells: [(row: Int, column: Int, span: Int)] = []
        var row = 0
        var column = 0
        for subview in subviews {
            let span = min(max(1, subview[TableSpan.self]), columns.count - column)
            cells.append((row, column, span))
            column += span
            if column >= columns.count {
                column = 0
                row += 1
            }
        }
        return cells
    }

    /// The natural width of every column; room to spare goes to the `grow` columns in proportion to their content,
    /// as a browser does. A table that does not fit keeps its natural width (the caller scrolls it).
    private func columnWidths(_ subviews: Subviews, width: Double?) -> [Double] {
        var widths = [Double](repeating: 0, count: columns.count)
        for (cell, subview) in zip(cells(subviews), subviews) where cell.span == 1 {
            widths[cell.column] = max(widths[cell.column], subview.sizeThatFits(.unspecified).width)
        }
        let growing = columns.indices.filter { columns[$0] == .grow }
        let share = growing.map { widths[$0] }.reduce(0, +)
        if let width, share > 0, width > widths.reduce(0, +) {
            let spare = width - widths.reduce(0, +)
            for index in growing {
                widths[index] += spare * widths[index] / share
            }
        }
        return widths
    }

    private func rowHeights(_ subviews: Subviews, widths: [Double]) -> [Double] {
        var heights: [Double] = []
        for (cell, subview) in zip(cells(subviews), subviews) {
            let width = widths[cell.column..<cell.column + cell.span].reduce(0, +)
            let height = subview.sizeThatFits(ProposedViewSize(width: width, height: nil)).height
            if cell.row == heights.count { heights.append(0) }
            heights[cell.row] = max(heights[cell.row], height)
        }
        return heights
    }
}

/// How many columns a cell of a `TableLayout` takes.
struct TableSpan: LayoutValueKey {
    static let defaultValue = 1
}

extension View {
    func tableSpan(_ columns: Int) -> some View {
        layoutValue(key: TableSpan.self, value: columns)
    }
}
