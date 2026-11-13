// Draws the app icon at every size and writes PNGs:  swift scripts/make-icon.swift <output-dir>
// A dark tile with a terminal prompt inside a segmented gauge: the panel's usage meter, bent into a ring.
// One accent only, no glows: the same restraint as the interface.

import AppKit

func rgb(_ hex: Int, _ alpha: CGFloat = 1) -> NSColor {
    NSColor(
        red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
        blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}

let accent = rgb(0x3FD07A)  // the interface's phosphor green
let bright = rgb(0xE6ECE8)
let track = rgb(0x2E3633)

func draw(size: Int) -> Data {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8, samplesPerPixel: 4,
        hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let ctx = NSGraphicsContext.current!.cgContext
    let s = CGFloat(size) / 1024  // everything below is designed on a 1024 canvas
    ctx.scaleBy(x: s, y: s)
    let small = size < 64  // tiny sizes: fewer, bolder shapes

    // Tile (the macOS icon grid: 824pt body, 100pt margin)
    let tile = CGRect(x: 100, y: 100, width: 824, height: 824)
    let body = CGPath(roundedRect: tile, cornerWidth: 186, cornerHeight: 186, transform: nil)
    ctx.saveGState()
    ctx.addPath(body)
    ctx.clip()
    let gradient = CGGradient(
        colorsSpace: CGColorSpaceCreateDeviceRGB(),
        colors: [rgb(0x1A1F1D).cgColor, rgb(0x0B0D0C).cgColor] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 100), options: [])
    ctx.restoreGState()
    ctx.addPath(body)
    ctx.setStrokeColor(track.cgColor)
    ctx.setLineWidth(small ? 20 : 8)
    ctx.strokePath()

    // Gauge: a 270° ring of segments, the first 70% lit
    let center = CGPoint(x: 512, y: 512)
    let segments = small ? 9 : 20
    let lit = Int((Double(segments) * 0.7).rounded())
    let step = CGFloat.pi * 1.5 / CGFloat(segments)
    let start = CGFloat.pi * 1.25  // lower left, going clockwise
    let gap = step * (small ? 0.24 : 0.2)
    ctx.setLineWidth(small ? 104 : 56)
    ctx.setLineCap(.butt)
    for i in 0..<segments {
        ctx.setStrokeColor((i < lit ? accent : track).cgColor)
        ctx.addArc(
            center: center, radius: small ? 262 : 286,
            startAngle: start - CGFloat(i) * step - gap / 2, endAngle: start - CGFloat(i + 1) * step + gap / 2,
            clockwise: true)
        ctx.strokePath()
    }

    // The prompt: a chevron and a block cursor
    let weight: CGFloat = small ? 84 : 58
    ctx.setLineWidth(weight)
    ctx.setLineCap(.square)
    ctx.setLineJoin(.miter)
    ctx.setStrokeColor(accent.cgColor)
    ctx.move(to: CGPoint(x: 372, y: 612))
    ctx.addLine(to: CGPoint(x: 492, y: 512))
    ctx.addLine(to: CGPoint(x: 372, y: 412))
    ctx.strokePath()
    ctx.setFillColor(bright.cgColor)
    ctx.fill(CGRect(x: 540, y: 412 - weight / 2, width: 150, height: weight))

    NSGraphicsContext.current = nil
    return rep.representation(using: .png, properties: [:])!
}

let out = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ".")
for size in [16, 32, 48, 64, 128, 256, 512, 1024] {
    try draw(size: size).write(to: out.appendingPathComponent("icon-\(size).png"))
}
