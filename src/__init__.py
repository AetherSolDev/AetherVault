# Created: 2026-07-24
# Last Edited: 2026-07-24 14:13 CT (America/Chicago)
# Path: src/__init__.py
# Purpose: Package init for AetherLock source. Defines PROJECT_ROOT and portable mode.

__version__ = "6.0.0"
VERSION = __version__
__app_name__ = "AetherLock"
APP_NAME = __app_name__

import os
import sys

if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.getcwd()
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORTABLE_MARKER = ".portable"


def is_portable() -> bool:
    return os.path.exists(os.path.join(PROJECT_ROOT, PORTABLE_MARKER))


def enable_portable_mode() -> bool:
    try:
        path = os.path.join(PROJECT_ROOT, PORTABLE_MARKER)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write("Portable mode enabled\n")
        return True
    except OSError:
        return False


def disable_portable_mode() -> bool:
    try:
        path = os.path.join(PROJECT_ROOT, PORTABLE_MARKER)
        if os.path.exists(path):
            os.remove(path)
        return True
    except OSError:
        return False
