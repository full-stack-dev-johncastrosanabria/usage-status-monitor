import SwiftUI

/// Name and status on one side, the global actions on the other; they stack when the window is too narrow.
struct HeaderView: View {
    @Environment(\.compact) private var compact

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .bottom, spacing: 20) {
                HeaderTitle()
                Spacer(minLength: 0)
                HeaderTools()
            }
            VStack(alignment: .leading, spacing: compact ? 8 : 12) {
                HeaderTitle()
                HeaderTools()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, compact ? 10 : 14)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Theme.lineStrong)
                .frame(height: 1)
        }
    }
}

struct HeaderTitle: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    @Environment(\.compact) private var compact

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text("usage-monitor")
                    .font(Theme.mono(14, .semibold))
                    .foregroundStyle(Theme.bright)
                    .accessibilityAddTraits(.isHeader)
                if monitor.payload?.demo == true {
                    Tag(text: strings("demo"), color: Theme.warn)
                }
            }
            .fixedSize()
            if !compact {
                StatusLine()
            }
        }
    }
}

/// "online · updated 2 min ago · ...", or that the server does not answer.
struct StatusLine: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings

    var body: some View {
        let color = monitor.offline ? Theme.bad : Theme.accent
        HStack(spacing: 8) {
            Circle()
                .fill(color)
                .frame(width: 7, height: 7)
                .accessibilityHidden(true)
            Text(text)
                .font(Theme.small)
                .foregroundStyle(monitor.offline ? Theme.bad : Theme.dim)
                .lineLimit(1)
        }
    }

    private var text: String {
        if monitor.offline { return strings("offline") }
        guard let payload = monitor.payload else { return "…" }
        let minutes = Int((Date.now.timeIntervalSince(payload.updatedDate ?? .now) / 60).rounded())
        let status = strings(
            "status",
            [
                "ago": minutes < 1 ? strings("justNow") : strings("minAgo", ["m": String(minutes)]),
                "m": Strings.number(payload.every / 60),
                "p": Strings.number(payload.alertAt),
            ])
        return "\(strings("online")) · \(status)"
    }
}

/// Language, Refresh and the switch to the account with the most room; only the last one in the compact layout.
/// These are the window's chrome: the only place where Liquid Glass is used.
struct HeaderTools: View {
    @Environment(Monitor.self) private var monitor
    @Environment(\.strings) private var strings
    @Environment(\.compact) private var compact

    var body: some View {
        GlassGroup {
            FlowLayout(spacing: 8, lineSpacing: 8) {
                if !compact {
                    OptionPicker(
                        name: strings("language"), options: languages, selected: strings.lang, select: monitor.setLanguage
                    )
                    .padding(2)
                    .modifier(ChromeGlass())
                    .padding(.trailing, 8)
                    Button(strings(monitor.refreshing ? "refreshing" : "refresh"), action: monitor.refresh)
                        .buttonStyle(ConsoleButtonStyle(chrome: true))
                        .disabled(monitor.refreshing)
                }
                Button(switchTitle, action: switchToBest)
                    .buttonStyle(ConsoleButtonStyle(kind: .primary, chrome: true))
                    .disabled(monitor.payload?.bestAccount == nil)
            }
        }
    }

    private var languages: [OptionPicker.Option] {
        (monitor.payload?.languages ?? [:]).sorted { $0.key < $1.key }.map { OptionPicker.Option(id: $0.key, label: $0.value) }
    }

    private var switchTitle: String {
        guard let best = monitor.payload?.bestAccount else { return strings("noBest") }
        return strings("switchBest", ["n": String(best.n), "p": Strings.percent(best.score ?? 0)])
    }

    private func switchToBest() { monitor.switchAccount() }
}
