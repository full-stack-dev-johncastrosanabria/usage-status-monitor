import SwiftUI

/// A row of words of which one is chosen (it wraps when it does not fit): model, effort, auto-switch, language.
struct OptionPicker: View {
    struct Option: Identifiable {
        let id: String
        let label: String
    }

    /// What is being chosen, for VoiceOver.
    let name: String
    let options: [Option]
    let selected: String?
    let select: (String) -> Void

    var body: some View {
        FlowLayout {
            ForEach(options) { option in
                Button(option.label) { select(option.id) }
                    .buttonStyle(ConsoleButtonStyle(kind: .option(selected: option.id == selected)))
                    .accessibilityAddTraits(option.id == selected ? .isSelected : [])
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(name)
    }
}
