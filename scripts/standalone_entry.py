"""Entry point for the standalone build (PyInstaller); see scripts/build-standalone.sh."""

import sys

from usage_monitor.cli import main

sys.exit(main())
