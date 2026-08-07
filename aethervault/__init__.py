# Created: 2026-07-24
# Last Edited: 2026-08-06 22:24 CT (America/Chicago)
# Path: aethervault/__init__.py
# Purpose: Package init for AetherVault source. Defines PROJECT_ROOT and portable mode.

"""Package initializer providing PROJECT_ROOT, version constants, and portable mode controls."""

__version__ = "6.5.0"
VERSION = __version__
__app_name__ = "AetherVault"
APP_NAME = __app_name__

import os
import sys


def _frozen_data_root() -> str:
    """Choose a stable, writable base dir for a frozen (PyInstaller) build.

    - Windows + macOS single-file executables: keep data next to the exe
      (portable-style; deterministic regardless of how the app was launched —
      Finder/LaunchServices do NOT reliably set cwd)
    - Linux AppImage --onefile: runs from an ephemeral /tmp/.mount_* that can
      be removed on exit -> use a stable per-user path instead
    """
    if sys.platform == "linux":
        root = os.path.join(os.path.expanduser("~"), ".local", "share", "AetherVault")
    elif sys.platform == "darwin" and ".app/Contents/MacOS" in os.path.realpath(sys.executable):
        # .app bundle (DMG install) — the bundle itself may sit in a read-only
        # DMG or be replaced on update; keep data in the per-user home dir.
        root = os.path.join(os.path.expanduser("~"), ".local", "share", "AetherVault")
    else:
        root = os.path.dirname(os.path.realpath(sys.executable))
    # If the app dir isn't writable (e.g. exe dropped in /Applications or
    # Program Files), fall back to a per-user path so data is never lost.
    try:
        os.makedirs(os.path.join(root, "data"), exist_ok=True)
        return root
    except OSError:
        return os.path.join(
            os.path.expanduser("~"), ".local", "share", "AetherVault"
        )


if getattr(sys, "frozen", False):
    PROJECT_ROOT = _frozen_data_root()
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORTABLE_MARKER = ".portable"


def is_portable() -> bool:
    """Return True if the portable marker file exists in PROJECT_ROOT."""
    return os.path.exists(os.path.join(PROJECT_ROOT, PORTABLE_MARKER))


def enable_portable_mode() -> bool:
    """Create the portable marker file and return True, or return False on failure."""
    try:
        path = os.path.join(PROJECT_ROOT, PORTABLE_MARKER)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("Portable mode enabled\n")
        return True
    except OSError:
        return False


def disable_portable_mode() -> bool:
    """Remove the portable marker file and return True, or return False on failure."""
    try:
        path = os.path.join(PROJECT_ROOT, PORTABLE_MARKER)
        if os.path.exists(path):
            os.remove(path)
        return True
    except OSError:
        return False
