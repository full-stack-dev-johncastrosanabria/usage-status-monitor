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
if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
    # Developer ID: sign every Mach-O inside the backend first, then the app, all with the hardened runtime.
    find "$APP/Contents/Resources/backend" -type f | while IFS= read -r f; do
        file -b "$f" | grep -q Mach-O || continue
        codesign --force --timestamp --options runtime --entitlements app/backend.entitlements \
            --sign "$MACOS_SIGN_IDENTITY" "$f"
    done
    codesign --force --timestamp --options runtime --sign "$MACOS_SIGN_IDENTITY" "$APP"
else
    codesign --force --deep --sign - "$APP"  # ad hoc: no certificate, the build is not notarised
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -quiet -volname "Usage Monitor" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
if [ -n "${MACOS_SIGN_IDENTITY:-}" ] && [ -n "${APPLE_ID:-}" ]; then
    codesign --timestamp --sign "$MACOS_SIGN_IDENTITY" "$DMG"
    xcrun notarytool submit "$DMG" --wait \
        --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_PASSWORD"
    xcrun stapler staple "$DMG"
fi
echo "$DMG"
