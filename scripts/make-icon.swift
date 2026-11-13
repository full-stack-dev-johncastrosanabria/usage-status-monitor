// Draws the app icon at every size and writes PNGs:  swift scripts/make-icon.swift <output-dir>
// A dark tile with a segmented neon gauge (the panel's usage bars, bent into a ring) around the "//" mark.

import AppKit

let cyan = NSColor(red: 0, green: 0.94, blue: 1, alpha: 1)
let lime = NSColor(red: 0.65, green: 1, blue: 0.24, alpha: 1)
let magenta = NSColor(red: 1, green: 0.17, blue: 0.84, alpha: 1)

func mix(_ a: NSColor, _ b: NSColor, _ t: CGFloat) -> NSColor {
    NSColor(
        red: a.redComponent + (b.redComponent - a.redComponent) * t,
        green: a.greenComponent + (b.greenComponent - a.greenComponent) * t,
        blue: a.blueComponent + (b.blueComponent - a.blueComponent) * t,
        alpha: 1)
}

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
        colors: [
            NSColor(red: 0.07, green: 0.11, blue: 0.19, alpha: 1).cgColor,
            NSColor(red: 0.02, green: 0.027, blue: 0.05, alpha: 1).cgColor,
        ] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 100), options: [])
    if !small {  // faint grid, as in the panel background
        ctx.setStrokeColor(cyan.withAlphaComponent(0.07).cgColor)
        ctx.setLineWidth(3)
        for i in stride(from: 100, through: 924, by: 103) {
            ctx.move(to: CGPoint(x: CGFloat(i), y: 100)); ctx.addLine(to: CGPoint(x: CGFloat(i), y: 924))
            ctx.move(to: CGPoint(x: 100, y: CGFloat(i))); ctx.addLine(to: CGPoint(x: 924, y: CGFloat(i)))
        }
        ctx.strokePath()
        // corner glows
        for (color, at) in [(cyan, CGPoint(x: 220, y: 860)), (magenta, CGPoint(x: 860, y: 200))] {
            let glow = CGGradient(
                colorsSpace: CGColorSpaceCreateDeviceRGB(),
                colors: [color.withAlphaComponent(0.22).cgColor, color.withAlphaComponent(0).cgColor] as CFArray,
                locations: [0, 1])!
            ctx.drawRadialGradient(glow, startCenter: at, startRadius: 0, endCenter: at, endRadius: 520, options: [])
        }
    }
    ctx.restoreGState()
    ctx.addPath(body)
    ctx.setStrokeColor(cyan.withAlphaComponent(0.45).cgColor)
    ctx.setLineWidth(small ? 20 : 8)
    ctx.strokePath()

    // Gauge: a 270° ring of segments, the first 70% lit (lime → cyan)
    let center = CGPoint(x: 512, y: 512)
    let segments = small ? 9 : 24
    let lit = Int((Double(segments) * 0.7).rounded())
    let sweep = CGFloat.pi * 1.5
    let start = CGFloat.pi * 1.25  // lower left, going clockwise
    let step = sweep / CGFloat(segments)
    let gap = step * (small ? 0.22 : 0.18)
    let radius: CGFloat = 268
    ctx.setLineWidth(small ? 110 : 76)
    ctx.setLineCap(.butt)
    for i in 0..<segments {
        let a0 = start - CGFloat(i) * step - gap / 2
        let a1 = start - CGFloat(i + 1) * step + gap / 2
        let on = i < lit
        let color = on ? mix(lime, cyan, CGFloat(i) / CGFloat(max(lit - 1, 1))) : NSColor.white.withAlphaComponent(0.09)
        ctx.saveGState()
        if on && !small { ctx.setShadow(offset: .zero, blur: 44, color: color.withAlphaComponent(0.85).cgColor) }
        ctx.setStrokeColor(color.cgColor)
        ctx.addArc(center: center, radius: radius, startAngle: a0, endAngle: a1, clockwise: true)
        ctx.strokePath()
        ctx.restoreGState()
    }

    // The "//" mark
    ctx.saveGState()
    if !small { ctx.setShadow(offset: .zero, blur: 50, color: magenta.withAlphaComponent(0.9).cgColor) }
    ctx.setFillColor(magenta.cgColor)
    let w: CGFloat = small ? 78 : 58, h: CGFloat = 250, lean: CGFloat = 92, spread: CGFloat = small ? 70 : 62
    for dx in [-spread, spread] {
        let x = center.x + dx
        ctx.move(to: CGPoint(x: x - lean / 2 - w / 2, y: center.y - h / 2))
        ctx.addLine(to: CGPoint(x: x - lean / 2 + w / 2, y: center.y - h / 2))
        ctx.addLine(to: CGPoint(x: x + lean / 2 + w / 2, y: center.y + h / 2))
        ctx.addLine(to: CGPoint(x: x + lean / 2 - w / 2, y: center.y + h / 2))
        ctx.closePath()
    }
    ctx.fillPath()
    ctx.restoreGState()

    NSGraphicsContext.current = nil
    return rep.representation(using: .png, properties: [:])!
}

let out = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ".")
for size in [16, 32, 48, 64, 128, 256, 512, 1024] {
    try draw(size: size).write(to: out.appendingPathComponent("icon-\(size).png"))
}
