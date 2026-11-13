#!/bin/sh
# Builds the macOS app (no Xcode project) into ~/Applications/UsageMonitor.app.
# Usage: scripts/build-app.sh [destination-folder]
set -eu
cd "$(dirname "$0")/.."
APP="${1:-$HOME/Applications}/UsageMonitor.app"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
# macOS 14 is the oldest supported (LSMinimumSystemVersion); newer API, such as Liquid Glass, is behind #available
swiftc -O -swift-version 5 -parse-as-library -target "$(uname -m)-apple-macos14.0" app/*.swift -o "$APP/Contents/MacOS/UsageMonitor"
cp app/Info.plist "$APP/Contents/Info.plist"
# pyproject.toml is the one place the version is written
plutil -replace CFBundleShortVersionString -string "$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)" "$APP/Contents/Info.plist"
if [ -f assets/icon.icns ]; then
    cp assets/icon.icns "$APP/Contents/Resources/icon.icns"
    plutil -replace CFBundleIconFile -string icon "$APP/Contents/Info.plist"
fi
codesign --force --sign - "$APP"  # local (ad hoc) signature: enough to run it on this Mac
echo "$APP"
