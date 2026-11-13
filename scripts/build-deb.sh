#!/bin/sh
# Builds dist/linux/usage-monitor_<version>_all.deb: the `usage` CLI/server and the GTK 4 app (pure Python).
# Uses dpkg-deb when it is installed, otherwise runs it in a debian:trixie container (Docker).
# Usage: scripts/build-deb.sh
set -eu
cd "$(dirname "$0")/.."
VERSION=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)
NAME="usage-monitor_${VERSION}_all"
STAGE="build/deb/$NAME"
LIB="$STAGE/usr/lib/usage-monitor"
APP_ID=dev.usage_monitor.Linux  # the GTK application id (linux/usage_monitor_gtk/app.py)

rm -rf "$STAGE"
mkdir -p "$LIB" "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/share/applications" dist/linux
cp -R src/usage_monitor linux/usage_monitor_gtk "$LIB/"
find "$LIB" -name __pycache__ -type d -prune -exec rm -rf {} +

cat > "$STAGE/usr/bin/usage" <<'EOF'
#!/bin/sh
PYTHONPATH=/usr/lib/usage-monitor exec python3 -m usage_monitor "$@"
EOF
cat > "$STAGE/usr/bin/usage-monitor" <<'EOF'
#!/bin/sh
PYTHONPATH=/usr/lib/usage-monitor exec python3 -m usage_monitor_gtk "$@"
EOF

cat > "$STAGE/usr/share/applications/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Usage Monitor
Comment=How much is left on your AI accounts
Exec=usage-monitor
Icon=usage-monitor
Terminal=false
Categories=Utility;Development;
Keywords=Claude;Codex;ChatGPT;usage;quota;
StartupWMClass=$APP_ID
EOF

if [ -f assets/icon-256.png ]; then
    mkdir -p "$STAGE/usr/share/icons/hicolor/256x256/apps"
    cp assets/icon-256.png "$STAGE/usr/share/icons/hicolor/256x256/apps/usage-monitor.png"
fi
if [ -f assets/icon.svg ]; then
    mkdir -p "$STAGE/usr/share/icons/hicolor/scalable/apps"
    cp assets/icon.svg "$STAGE/usr/share/icons/hicolor/scalable/apps/usage-monitor.svg"
fi

cat > "$STAGE/DEBIAN/control" <<EOF
Package: usage-monitor
Version: $VERSION
Architecture: all
Maintainer: usage-monitor contributors <noreply@users.noreply.github.com>
Installed-Size: $(du -sk "$STAGE/usr" | cut -f1)
Depends: python3 (>= 3.12), python3-gi, gir1.2-gtk-4.0
Suggests: fonts-jetbrains-mono, fonts-noto-cjk, libsecret-tools, libnotify-bin
Section: utils
Priority: optional
Homepage: https://github.com/full-stack-dev-johncastrosanabria/usage-status-monitor
Description: how much is left on your AI accounts
 Usage left on Claude (several accounts), ChatGPT/Codex, Antigravity and
 DeepSeek, with alerts and Claude Code account switching. Provides the
 usage command and the usage-monitor desktop app (GTK 4).
EOF

find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$STAGE/usr/bin/usage" "$STAGE/usr/bin/usage-monitor"

OUT="dist/linux/$NAME.deb"
if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --root-owner-group --build "$STAGE" "$OUT"
else
    docker run --rm -v "$PWD:/w" -w /w debian:trixie dpkg-deb --root-owner-group --build "$STAGE" "$OUT"
fi
echo "$OUT"
