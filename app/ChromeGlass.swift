import SwiftUI

/// Liquid Glass for the window chrome (the header's controls) on macOS 26 and later; nothing before that.
/// Deliberately untinted and never used for table rows or data: this is a sober tool.
struct ChromeGlass: ViewModifier {
    static var isAvailable: Bool {
        if #available(macOS 26.0, *) { true } else { false }
    }

    @Environment(\.flatChrome) private var flat
    var enabled = true
    /// The glass reacts to the pointer (buttons).
    var interactive = false

    func body(content: Content) -> some View {
        if #available(macOS 26.0, *), enabled, !flat {
            content.glassEffect(.regular.interactive(interactive), in: .rect(cornerRadius: Theme.radius))
        } else {
            content
        }
    }
}

/// Neighbouring glass shapes are drawn together, as the system asks; before macOS 26 it is nothing.
struct GlassGroup<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        if #available(macOS 26.0, *) {
            GlassEffectContainer { content }
        } else {
            content
        }
    }
}
