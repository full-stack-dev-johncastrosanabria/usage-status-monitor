import SwiftUI

/// Lays its children out in a row and wraps to the next line when they do not fit (options, tools, hints).
struct FlowLayout: Layout {
    var spacing = 4.0
    var lineSpacing = 4.0

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        arrange(subviews, width: proposal.width ?? .infinity).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let origins = arrange(subviews, width: bounds.width).origins
        for (subview, origin) in zip(subviews, origins) {
            subview.place(
                at: CGPoint(x: bounds.minX + origin.x, y: bounds.minY + origin.y),
                proposal: ProposedViewSize(width: bounds.width, height: nil))
        }
    }

    private func arrange(_ subviews: Subviews, width: Double) -> (origins: [CGPoint], size: CGSize) {
        let sizes = subviews.map { $0.sizeThatFits(ProposedViewSize(width: width, height: nil)) }
        var origins: [CGPoint] = []
        var rowStart = 0
        var x = 0.0
        var y = 0.0
        var rowHeight = 0.0
        var widest = 0.0
        // children of a row are centred on it
        func centreRow() {
            for index in rowStart..<origins.count {
                origins[index].y += (rowHeight - sizes[index].height) / 2
            }
        }
        for size in sizes {
            if x > 0, x + size.width > width {
                centreRow()
                rowStart = origins.count
                x = 0
                y += rowHeight + lineSpacing
                rowHeight = 0
            }
            origins.append(CGPoint(x: x, y: y))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            widest = max(widest, x - spacing)
        }
        centreRow()
        return (origins, CGSize(width: widest, height: y + rowHeight))
    }
}
