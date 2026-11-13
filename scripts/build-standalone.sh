#!/bin/sh
# Builds a standalone `usage` (no Python needed on the target machine) into dist/standalone/usage/.
# A folder build, not a single file: it starts instantly, which matters for the Claude Code hook.
set -eu
cd "$(dirname "$0")/.."
uv run --with pyinstaller pyinstaller --noconfirm --clean --onedir --name usage \
    --paths src --collect-data usage_monitor \
    --distpath dist/standalone --workpath build/standalone --specpath build/standalone \
    scripts/standalone_entry.py
dist/standalone/usage/usage --version
