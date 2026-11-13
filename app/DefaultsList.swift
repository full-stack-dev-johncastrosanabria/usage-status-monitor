import SwiftUI

/// Claude Code's defaults for new sessions (model, effort) and the automatic switch: a term and its options per line.
struct DefaultsList: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    let settings: Payload.Settings
    let autoSwitch: Bool
    let alertAt: Double

    var body: some View {
        VStack(spacing: 0) {
            if let error = settings.error {
                DefaultsRow(term: strings("model"), ruled: false) {
                    ErrorText(message: error)
                }
            } else {
                DefaultsRow(term: strings("model"), ruled: false) {
                    OptionPicker(name: strings("model"), options: models(more: false), selected: settings.model, select: monitor.setModel)
                }
                DefaultsRow(term: strings("moreModels")) {
                    OptionPicker(name: strings("moreModels"), options: models(more: true), selected: settings.model, select: monitor.setModel)
                }
                DefaultsRow(term: strings("effort")) {
                    OptionPicker(name: strings("effort"), options: efforts, selected: settings.effort, select: monitor.setEffort)
                    Hint(text: strings("effortHint"))
                }
            }
            DefaultsRow(term: strings("autoSwitch")) {
                OptionPicker(name: strings("autoSwitch"), options: switchStates, selected: autoSwitch ? "on" : "off", select: setAutoSwitch)
                Hint(text: strings("autoHint", ["p": Strings.number(alertAt)]))
            }
        }
        .tableFrame()
    }

    private var efforts: [OptionPicker.Option] {
        (settings.efforts ?? []).map { OptionPicker.Option(id: $0, label: $0) }
    }

    private var switchStates: [OptionPicker.Option] {
        ["on", "off"].map { OptionPicker.Option(id: $0, label: strings($0)) }
    }

    private func models(more: Bool) -> [OptionPicker.Option] {
        (settings.models ?? []).filter { $0.more == more }.map { OptionPicker.Option(id: $0.id, label: $0.label) }
    }

    private func setAutoSwitch(_ state: String) { monitor.setAutoSwitch(state == "on") }
}

/// A term on the left, what can be chosen for it on the right.
struct DefaultsRow<Content: View>: View {
    let term: String
    var ruled = true
    @ViewBuilder let content: Content

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            ColumnHeader(title: term)
                .frame(width: 130, alignment: .leading)
                .padding(.top, 5)  // on the baseline of the first option
            FlowLayout(spacing: 16, lineSpacing: 6) {
                content
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Theme.line)
                .frame(height: 1)
                .opacity(ruled ? 1 : 0)
        }
    }
}
