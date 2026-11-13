import SwiftUI

/// A horizontal run of small blocks filled up to `fraction` of the width: the bar of a meter.
@Animatable
struct SegmentBar: Shape {
    var fraction: Double
    @AnimatableIgnored var block = 7.0
    @AnimatableIgnored var gap = 1.4

    func path(in rect: CGRect) -> Path {
        let end = rect.minX + rect.width * min(max(fraction, 0), 1)
        var path = Path()
        for x in stride(from: rect.minX, to: end, by: block + gap) {
            path.addRect(CGRect(x: x, y: rect.minY, width: min(block, end - x), height: rect.height))
        }
        return path
    }
}
