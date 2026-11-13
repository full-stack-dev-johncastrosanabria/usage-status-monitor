import SwiftUI

/// Every button of the panel: a thin outline, square corners, no fill until it is touched.
struct ConsoleButtonStyle: ButtonStyle {
    enum Kind: Equatable {
        case standard
        /// The main action: the accent colour.
        case primary
        /// One word of a row of options; the chosen one is outlined in the accent colour.
        case option(selected: Bool)
    }

    var kind = Kind.standard
    /// A header control: made of glass where the system has it. Never set it inside a table.
    var chrome = false

    func makeBody(configuration: Configuration) -> some View {
        ConsoleButton(style: self, configuration: configuration)
    }
}

private struct ConsoleButton: View {
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.flatChrome) private var flat
    @State private var hovering = false
    let style: ConsoleButtonStyle
    let configuration: ButtonStyleConfiguration

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: Theme.radius)
        configuration.label
            .font(Theme.small)
            .lineLimit(1)
            .foregroundStyle(foreground)
            .padding(.horizontal, isOption ? 9 : 12)
            .padding(.vertical, isOption ? 3 : 5)
            .background(background, in: shape)
            .modifier(ChromeGlass(enabled: style.chrome, interactive: isEnabled))
            .overlay { shape.strokeBorder(border, lineWidth: 1) }
            .contentShape(shape)
            .onHover { hovering = $0 }
            .animation(.easeOut(duration: 0.15), value: hovering)
    }

    private var isOption: Bool {
        if case .option = style.kind { true } else { false }
    }

    /// On glass the material is the surface, so nothing is filled.
    private var glass: Bool { style.chrome && !flat && ChromeGlass.isAvailable }

    private var foreground: Color {
        guard isEnabled else { return Theme.dim }
        return switch style.kind {
        case .standard: Theme.text
        case .primary: hovering && !glass ? Theme.accentInk : Theme.accent
        case .option(let selected): selected ? Theme.accent : hovering ? Theme.text : Theme.dim
        }
    }

    private var background: Color {
        guard isEnabled, !glass else { return .clear }
        return switch style.kind {
        case .standard: configuration.isPressed ? Theme.line : hovering ? Theme.raised : .clear
        case .primary: hovering ? Theme.accent : .clear
        case .option(let selected): selected ? Theme.accentWash : .clear
        }
    }

    private var border: Color {
        guard isEnabled else { return isOption ? .clear : Theme.line }
        return switch style.kind {
        case .standard: hovering ? Theme.dim : Theme.lineStrong
        case .primary: Theme.accent
        case .option(let selected): selected ? Theme.accent : hovering ? Theme.lineStrong : .clear
        }
    }
}
