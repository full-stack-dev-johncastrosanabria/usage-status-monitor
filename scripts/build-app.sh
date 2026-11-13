#!/bin/sh
# Builds the macOS app (no Xcode project) into ~/Applications/UsageMonitor.app.
# Usage: scripts/build-app.sh [destination-folder]
set -eu
cd "$(dirname "$0")/.."
APP="${1:-$HOME/Applications}/UsageMonitor.app"

mkdir -p "$APP/Contents/MacOS"
swiftc -O -swift-version 5 -parse-as-library app/UsageMonitor.swift -o "$APP/Contents/MacOS/UsageMonitor"
cp app/Info.plist "$APP/Contents/Info.plist"
codesign --force --sign - "$APP"  # local (ad hoc) signature: enough to run it on this Mac
echo "$APP"
