import SwiftUI

/// The menu bar item's menu; its language follows the one chosen in the panel.
struct MenuContent: View {
    @Environment(\.openWindow) private var openWindow
    let monitor: Monitor

    var body: some View {
        let strings = monitor.strings
        if let problem = monitor.problem {
            Text(strings(problem))
            Divider()
        }
        Button(strings("menuOpen"), action: openPanel)
        Button(strings("menuSwitch"), action: switchToBest)
            .disabled(monitor.payload?.bestAccount == nil)
        Button(strings("menuRefresh"), action: monitor.refresh)
        Divider()
        Button(strings("menuQuit"), action: quit)
            .keyboardShortcut("q")
    }

    private func openPanel() {
        openWindow(id: UsageMonitorApp.panelID)
        NSApp.activate()
    }

    private func switchToBest() { monitor.switchAccount() }

    private func quit() { NSApp.terminate(nil) }
}
