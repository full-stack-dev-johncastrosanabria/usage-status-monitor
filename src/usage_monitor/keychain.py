"""Read-only access to the system credential store.

macOS: Keychain (`security`). Linux: Secret Service (`secret-tool`). Windows: Credential Manager.
"""

from __future__ import annotations

import subprocess
import sys


def read_secret(service: str, account: str | None = None) -> str | None:
    if sys.platform == "darwin":
        return _run(["security", "find-generic-password", "-s", service, *(["-a", account] if account else []), "-w"])
    if sys.platform == "win32":
        return _wincred(f"{service}:{account}" if account else service)
    return _run(["secret-tool", "lookup", "service", service, *(["username", account] if account else [])])


def _run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):  # tool not installed, or the store is locked
        return None
    return out or None


def _wincred(target: str) -> str | None:
    """CredReadW of a generic credential (the format go-keyring and keytar write)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Credential(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        )

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(Credential)),
    )
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = (ctypes.c_void_p,)

    cred = ctypes.POINTER(Credential)()
    generic = 1  # CRED_TYPE_GENERIC
    if not advapi.CredReadW(target, generic, 0, ctypes.byref(cred)):
        return None
    try:
        blob = ctypes.string_at(cred.contents.CredentialBlob, cred.contents.CredentialBlobSize)
    finally:
        advapi.CredFree(cred)
    return blob.decode("utf-8", errors="replace") or None
