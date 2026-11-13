import SwiftUI

/// The window: the panel on its background, switching to the compact layout when it gets narrow.
struct PanelView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let monitor: Monitor
    @State private var compact = false

    var body: some View {
        ScrollView {
            PanelContent(monitor: monitor, compact: compact)
        }
        .scrollContentBackground(.visible)
        .background(Theme.bg)
        .overlay(alignment: .bottom) {
            if let toast = monitor.toast {
                Toast(message: toast)
                    .transition(reduceMotion ? .opacity : .opacity.combined(with: .offset(y: 8)))
            }
        }
        .animation(.easeOut(duration: 0.15), value: monitor.toast)
        .onGeometryChange(for: Bool.self) { proxy in
            proxy.size.width < Theme.compactWidth
        } action: { narrow in
            compact = narrow
        }
        .preferredColorScheme(.dark)
    }
}

/// What an action did, for a few seconds.
struct Toast: View {
    let message: String

    var body: some View {
        Text(message)
            .font(Theme.small)
            .foregroundStyle(Theme.text)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(Theme.raised)
            .border(Theme.lineStrong)
            .padding(.horizontal, 16)
            .padding(.bottom, 20)
    }
}
