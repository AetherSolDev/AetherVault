# Created: 2026-07-24
# Last Edited: 2026-08-05 15:52 CT (America/Chicago)
# Path: aethervault/__init__.py
# Purpose: Package init for AetherVault source. Defines PROJECT_ROOT and portable mode.

"""Package initializer providing PROJECT_ROOT, version constants, and portable mode controls."""

__version__ = "6.3.1"
VERSION = __version__
__app_name__ = "AetherVault"
APP_NAME = __app_name__

import os
import sys

if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.getcwd()
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
            with open(path, "w") as f:
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
