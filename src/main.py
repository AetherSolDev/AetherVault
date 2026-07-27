# Created: 2026-07-24
# Last Edited: 2026-07-27 13:47 CT (America/Chicago)
# Path: src/main.py
# Purpose: Application entry point with CLI switches (--version, --debug, --upgrade).

"""Application entry point with CLI switches (--version, --debug, --upgrade)."""

import argparse
import json
import logging
import sys
import textwrap
import urllib.request
import urllib.error

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from src import VERSION
from src.gui.app import PySidePWManager

GITHUB_API = "https://api.github.com/repos/brandonmunoz1975-ops/AetherVault/releases/latest"


def check_for_upgrades() -> bool:
    """Check GitHub for a newer release. Returns True if upgrade was performed."""
    try:
        req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "AetherVault"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("No releases published yet. Check back later.")
        else:
            print(f"Upgrade check failed (HTTP {e.code})")
        return False
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print(f"Upgrade check failed: {e}")
        return False

    latest_tag = data.get("tag_name", "").lstrip("v")
    if not latest_tag:
        print("Could not determine latest version.")
        return False

    def parse_ver(v: str):
        parts = v.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    current = parse_ver(VERSION)
    latest = parse_ver(latest_tag)

    if latest <= current:
        print(f"You're up to date! (v{VERSION})")
        return False

    print(f"New version available: v{latest_tag} (current: v{VERSION})")
    print(textwrap.dedent(f"""
    To upgrade via pip:
        pip install --upgrade git+https://github.com/brandonmunoz1975-ops/AetherVault.git

    Or download the latest release from:
        https://github.com/brandonmunoz1975-ops/AetherVault/releases/latest
    """))
    return True


def run():
    """Parse CLI arguments and run the application."""
    parser = argparse.ArgumentParser(description="AetherVault — secure password manager")
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging to terminal",
    )
    parser.add_argument(
        "--upgrade", "-u",
        action="store_true",
        help="Check GitHub for a newer release",
    )
    args = parser.parse_args()

    if args.version:
        print(f"AetherVault v{VERSION}")
        sys.exit(0)

    if args.upgrade:
        check_for_upgrades()
        sys.exit(0)

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stderr,
            format="%(levelname)s:%(name)s:%(message)s",
        )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PySidePWManager()
    window.show()
    QTimer.singleShot(500, window.check_setup_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
