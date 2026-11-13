// macOS app: a native window with the panel plus a menu bar indicator.
// The data comes from the local server (`usage server`), which this app starts and stops.

import SwiftUI

struct UsageMonitorApp: App {
    static let panelID = "panel"
    @State private var monitor = Monitor(live: true)

    var body: some Scene {
        Window("USAGE // MONITOR", id: Self.panelID) {
            PanelView(monitor: monitor)
                .frame(minWidth: 300, minHeight: 200)
        }
        .defaultSize(width: 1280, height: 880)
        .windowStyle(.hiddenTitleBar)

        MenuBarExtra {
            MenuContent(monitor: monitor)
        } label: {
            Text(monitor.menuTitle)
        }
    }
}

@main
enum Launch {
    /// `--snapshot <file.png> [--width <pt>]` renders the panel once to a PNG and exits (for looking at the
    /// interface without opening it); anything else starts the app.
    static func main() {
        if let file = value(after: "--snapshot") {
            let width = value(after: "--width").flatMap(Double.init) ?? 1280
            Task { @MainActor in
                exit(await Snapshot.write(to: file, width: width) ? 0 : 1)
            }
            // SwiftUI renders on the main thread, so the main run loop (not `dispatchMain`) drives the task above
            CFRunLoopRun()
            return
        }
        UsageMonitorApp.main()
    }

    private static func value(after flag: String) -> String? {
        let arguments = CommandLine.arguments
        guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}
