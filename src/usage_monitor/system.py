"""Small operating-system helpers shared across the package."""

from __future__ import annotations

import contextlib
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Extra Popen/run arguments for helper commands: on Windows, never flash a console window.
QUIET: dict[str, Any] = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


def atomic_write_text(path: Path, text: str) -> None:
    """Replaces `path` in one step, keeping the permissions of the file it replaces.

    The temporary file is unique (concurrent writers do not collide) and is created private (0600),
    which is also the mode a new file ends up with.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        with contextlib.suppress(OSError):  # no existing file, or a filesystem without modes
            Path(tmp).chmod(stat.S_IMODE(path.stat().st_mode))
        Path(tmp).replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp).unlink()
        raise
