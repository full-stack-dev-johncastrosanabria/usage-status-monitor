#!/bin/sh
# Regenerates every icon file in assets/ from scripts/make-icon.swift (macOS only).
set -eu
cd "$(dirname "$0")/.."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
swift scripts/make-icon.swift "$TMP"

# macOS: .icns
SET="$TMP/icon.iconset"
mkdir "$SET"
for s in 16 32 128 256 512; do
    cp "$TMP/icon-$s.png" "$SET/icon_${s}x${s}.png"
    cp "$TMP/icon-$((s * 2)).png" "$SET/icon_${s}x${s}@2x.png"
done
iconutil -c icns "$SET" -o assets/icon.icns

# Windows: .ico holding PNG images (supported since Vista)
python3 - "$TMP" <<'PY'
import struct, sys
from pathlib import Path

sizes = (16, 32, 48, 64, 128, 256)
images = [Path(sys.argv[1], f"icon-{s}.png").read_bytes() for s in sizes]
header = struct.pack("<HHH", 0, 1, len(sizes))
offset = len(header) + 16 * len(sizes)
entries = b""
for size, data in zip(sizes, images):
    entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
    offset += len(data)
Path("assets/icon.ico").write_bytes(header + entries + b"".join(images))
PY

# Linux, README and the Claude Code plugin
cp "$TMP/icon-256.png" assets/icon-256.png
cp "$TMP/icon-1024.png" assets/icon-1024.png
cp "$TMP/icon-512.png" plugin/.claude-plugin/icon.png
ls -l assets plugin/.claude-plugin/icon.png
