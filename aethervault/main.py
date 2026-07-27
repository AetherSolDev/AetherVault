# Created: 2026-07-24
# Last Edited: 2026-07-27 16:20 CT (America/Chicago)
# Path: aethervault/main.py
# Purpose: Application entry point with CLI switches (--version, --debug, --upgrade, --foreground).

"""Application entry point with CLI switches (--version, --debug, --upgrade, --foreground)."""

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.request
import urllib.error
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from aethervault import PROJECT_ROOT, VERSION
from aethervault.gui.app import PySidePWManager

GITHUB_TAGS_API = "https://api.github.com/repos/brandonmunoz1975-ops/AetherVault/tags"


GIT_REPO_URL = "https://github.com/brandonmunoz1975-ops/AetherVault.git"
RELEASES_URL = "https://github.com/brandonmunoz1975-ops/AetherVault/releases/latest"


def _is_git_repo() -> bool:
    """Return True if PROJECT_ROOT contains a .git directory."""
    return os.path.isdir(os.path.join(PROJECT_ROOT, ".git"))


def _get_pip_command() -> str:
    """Return the appropriate pip command (venv or system)."""
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        return os.path.join(sys.prefix, "bin", "pip")
    return "pip"


def _fetch_latest_tag() -> Optional[str]:
    """Fetch the latest version tag from GitHub. Returns tag string or None."""
    try:
        req = urllib.request.Request(GITHUB_TAGS_API, headers={"User-Agent": "AetherVault"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Upgrade check failed (HTTP {e.code})")
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print(f"Upgrade check failed: {e}")
        return None

    if not tags:
        print("No version tags found on GitHub.")
        return None

    latest_tag = tags[0].get("name", "").lstrip("v")
    if not latest_tag:
        print("Could not determine latest version.")
        return None

    return latest_tag


def _perform_upgrade(latest_tag: str) -> bool:
    """Perform the actual upgrade. Returns True on success."""
    print(f"Upgrading AetherVault v{VERSION} → v{latest_tag} ...")
    print()

    try:
        if _is_git_repo():
            print("1. Pulling latest code via git ...", end=" ", flush=True)
            result = subprocess.run(
                ["git", "pull"],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print("FAILED")
                print(result.stderr)
                return False
            print("done")

            print("2. Reinstalling package ...", end=" ", flush=True)
            pip_cmd = _get_pip_command()
            result = subprocess.run(
                [pip_cmd, "install", "-e", "."],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                print("FAILED")
                print(result.stderr)
                return False
            print("done")
        else:
            print("1. Upgrading via pip ...", end=" ", flush=True)
            pip_cmd = _get_pip_command()
            result = subprocess.run(
                [pip_cmd, "install", "--upgrade", f"git+{GIT_REPO_URL}"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                print("FAILED")
                print(result.stderr)
                return False
            print("done")

        print(f"\nUpgrade to v{latest_tag} complete!")
        return True

    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"FAILED — {e}")
        return False


def check_for_upgrades() -> bool:
    """Check GitHub tags for a newer version and upgrade if available. Returns True on success."""
    latest_tag = _fetch_latest_tag()
    if latest_tag is None:
        return False

    def parse_ver(v: str):
        parts = v.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    current = parse_ver(VERSION)
    latest = parse_ver(latest_tag)

    if latest <= current:
        print(f"You're up to date! (v{VERSION})")
        return False

    return _perform_upgrade(latest_tag)


def detach_from_terminal():
    """Fork and release the terminal (Unix only). Parent exits, child continues."""
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        os.setsid()
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
    except OSError:
        pass


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
        help="Check for updates and auto-upgrade (git pull + pip install)",
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Keep terminal attached (for debugging)",
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

    if not args.foreground and sys.platform != "win32":
        detach_from_terminal()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PySidePWManager()
    window.show()
    QTimer.singleShot(500, window.check_setup_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
