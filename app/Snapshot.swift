import SwiftUI

/// Renders the panel to a PNG, at its full height, with the data the server has right now.
@MainActor
enum Snapshot {
    static func write(to file: String, width: Double) async -> Bool {
        let missing = Strings.missingKeys
        guard missing.isEmpty else { return fail("missing translations: \(missing.joined(separator: ", "))") }

        let monitor = Monitor(live: false)
        await monitor.load()
        guard monitor.payload != nil else { return fail("no answer from http://127.0.0.1:\(Backend.port)/api/data") }

        let panel = PanelContent(monitor: monitor, compact: width < Theme.compactWidth)
            .frame(width: width)
            .fixedSize(horizontal: false, vertical: true)
            .background(Theme.bg)
            // `ImageRenderer` draws no live material, so the snapshot shows the controls without glass
            .environment(\.flatChrome, true)
            .environment(\.colorScheme, .dark)
        let renderer = ImageRenderer(content: panel)
        renderer.scale = 2
        guard let image = renderer.cgImage,
            let png = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:])
        else { return fail("could not render the panel") }
        do {
            try png.write(to: URL(fileURLWithPath: file))
            return true
        } catch {
            return fail(error.localizedDescription)
        }
    }

    private static func fail(_ message: String) -> Bool {
        FileHandle.standardError.write(Data("snapshot: \(message)\n".utf8))
        return false
    }
}
