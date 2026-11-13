import SwiftUI

/// The small pieces the tables are made of.

/// A table in its frame. When the window is too narrow for its columns it scrolls sideways instead of squeezing.
struct DataTable<Cells: View>: View {
    let columns: [TableLayout.Column]
    @ViewBuilder let cells: Cells
    @Environment(\.flatChrome) private var flatChrome

    var body: some View {
        ViewThatFits(in: .horizontal) {
            TableLayout(columns: columns) { cells }
            if flatChrome {
                // `ImageRenderer` (the snapshot) draws a ScrollView as an empty box: clip it as if scrolled to the start
                TableLayout(columns: columns) { cells }
                    .fixedSize(horizontal: true, vertical: false)
                    .frame(minWidth: 0, maxWidth: .infinity, alignment: .leading)
                    .clipped()
            } else {
                ScrollView(.horizontal) {
                    TableLayout(columns: columns) { cells }
                }
            }
        }
        .tableFrame()
    }
}

/// The padding, rule and background of one cell (or, in the compact layout, of one whole row).
struct TableCell: ViewModifier {
    enum Kind {
        case header
        case row
        /// A further row of the same source: it joins the one above.
        case sub
        /// The line that names a source above its rows (compact layout).
        case group
    }

    @Environment(\.compact) private var compact
    var kind = Kind.row
    /// A rule above it; the first row of a table has none.
    var ruled = true
    /// The active account.
    var highlighted = false
    var alignment = Alignment.topLeading

    func body(content: Content) -> some View {
        let vertical = compact || kind == .header ? 7.0 : 9.0
        content
            .padding(.horizontal, compact ? 10 : 14)
            .padding(.top, kind == .sub ? 0 : vertical)
            .padding(.bottom, kind == .group ? 0 : vertical)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: alignment)
            .background(highlighted ? Theme.accentWash : .clear)
            .overlay(alignment: kind == .header ? .bottom : .top) {
                Rectangle()
                    .fill(kind == .header ? Theme.lineStrong : Theme.line)
                    .frame(height: 1)
                    .opacity(kind == .header || (ruled && kind != .sub) ? 1 : 0)
            }
    }
}

extension View {
    /// The surface and outline shared by the tables and the list of defaults.
    func tableFrame() -> some View {
        background(Theme.surface).border(Theme.line)
    }
}

struct ColumnHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(Theme.label)
            .tracking(Theme.labelTracking)
            .textCase(.uppercase)
            .foregroundStyle(Theme.dim)
            .lineLimit(1)
    }
}

/// % free and a bar of ten cells, coloured by how much is left.
struct Meter: View {
    @Environment(\.strings) private var strings
    @Environment(\.compact) private var compact
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    /// Room for "100%", so the bars of a column line up.
    static let percentWidth = 34.0
    let free: Double

    var body: some View {
        let tone = Theme.tone(free: free)
        HStack(spacing: 10) {
            Text("\(Strings.percent(free))%")
                .font(Theme.mono(13, .semibold))
                .monospacedDigit()
                .foregroundStyle(tone)
                .frame(width: Self.percentWidth, alignment: .trailing)
            SegmentBar(fraction: 1)
                .fill(Theme.lineStrong)
                .overlay {
                    SegmentBar(fraction: free / 100).fill(tone)
                }
                .frame(width: compact ? 44 : 84, height: 6)
                .animation(reduceMotion ? nil : .easeOut(duration: 0.2), value: free)
        }
        .fixedSize()
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(strings("freeAria", ["p": Strings.percent(free)]))
    }
}

/// A small outlined word next to a name: "active", "most room", "demo data".
struct Tag: View {
    let text: String
    var color = Theme.dim

    var body: some View {
        Text(text)
            .font(Theme.mono(10))
            .tracking(0.8)
            .textCase(.uppercase)
            .lineLimit(1)
            .foregroundStyle(color)
            .padding(.horizontal, 6)
            .padding(.vertical, 1)
            .border(color == Theme.dim ? Theme.lineStrong : color)
    }
}

/// What a source answered instead of its data (already translated by the server).
struct ErrorText: View {
    let message: String

    var body: some View {
        Text(message)
            .foregroundStyle(Theme.bad)
            .frame(idealWidth: 240, maxWidth: .infinity, alignment: .leading)
            .fixedSize(horizontal: false, vertical: true)
    }
}

/// An explanation next to a control.
struct Hint: View {
    let text: String

    var body: some View {
        Text(text)
            .font(Theme.small)
            .foregroundStyle(Theme.dim)
            .fixedSize(horizontal: false, vertical: true)
    }
}

/// A whole row that is a button (compact layout): it lights up under the pointer.
struct RowButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        RowButton(configuration: configuration)
    }
}

private struct RowButton: View {
    @Environment(\.isEnabled) private var isEnabled
    @State private var hovering = false
    let configuration: ButtonStyleConfiguration

    var body: some View {
        configuration.label
            .background(isEnabled && (hovering || configuration.isPressed) ? Theme.raised : .clear)
            .contentShape(.rect)
            .onHover { hovering = $0 }
    }
}
