#!/bin/sh
# Builds dist/macos/UsageMonitor-<version>-<arch>.dmg: the app with the standalone backend inside.
set -eu
cd "$(dirname "$0")/.."
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
OUT="dist/macos"
APP="$OUT/UsageMonitor.app"
DMG="$OUT/UsageMonitor-$VERSION-$(uname -m).dmg"

rm -rf "$OUT"
mkdir -p "$OUT"
scripts/build-standalone.sh >/dev/null
scripts/build-app.sh "$OUT" >/dev/null

# The backend goes inside the bundle; the app looks for Contents/Resources/usage first.
mkdir -p "$APP/Contents/Resources"
cp -R dist/standalone/usage "$APP/Contents/Resources/backend"
ln -s backend/usage "$APP/Contents/Resources/usage"
codesign --force --deep --sign - "$APP"  # ad hoc: the build is not notarised (see the README)

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -quiet -volname "Usage Monitor" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
echo "$DMG"
