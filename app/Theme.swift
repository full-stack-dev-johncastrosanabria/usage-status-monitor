import SwiftUI

/// An operator console: near-monochrome, one phosphor-green accent, tabular data, thin rules. Dark only: it sits
/// next to terminals and editors, usually for hours. The values are the CSS variables of the web panel
/// (src/usage_monitor/web/panel.html), so both interfaces stay the same product.
enum Theme {
    static let bg = Color(hex: 0x0B0D0C)
    static let surface = Color(hex: 0x101312)
    static let raised = Color(hex: 0x151917)
    static let line = Color(hex: 0x1F2523)
    static let lineStrong = Color(hex: 0x2E3633)
    static let text = Color(hex: 0xC8D1CC)
    static let bright = Color(hex: 0xE6ECE8)
    static let dim = Color(hex: 0x8A958F)
    /// Reserved for the current selection, the primary action and a healthy state.
    static let accent = Color(hex: 0x3FD07A)
    static let accentInk = Color(hex: 0x06130B)
    static let accentWash = accent.opacity(0.07)
    static let warn = Color(hex: 0xD9A441)
    static let bad = Color(hex: 0xE5534B)
    static let badWash = bad.opacity(0.08)

    /// Below this window width only the essentials are shown, one line per account.
    static let compactWidth = 620.0
    static let maxContentWidth = 1180.0
    static let radius = 2.0

    /// Monospaced throughout, in a fixed scale: the panel is a dense table laid out to the point.
    static func mono(_ size: Double, _ weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }

    static let body = mono(13)
    static let small = mono(12)
    /// Column headers and terms: used uppercase and letter-spaced.
    static let label = mono(11)
    static let labelTracking = 0.9

    /// Only meters are coloured by state: green while there is room, amber when short, red when nearly gone.
    static func tone(free: Double) -> Color {
        free > 50 ? accent : free > 20 ? warn : bad
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red: Double(hex >> 16 & 0xFF) / 255,
            green: Double(hex >> 8 & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255)
    }
}

extension EnvironmentValues {
    /// One line per account, secondary controls hidden.
    @Entry var compact = false
    /// Never draw Liquid Glass, even where it exists (`ImageRenderer` cannot render the live material).
    @Entry var flatChrome = false
    @Entry var strings = Strings(lang: "en")
}
