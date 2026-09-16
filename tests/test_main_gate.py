# Created: 2026-08-09
# Last Edited: 2026-09-16 14:46 CT (America/Chicago)
# Path: tests/test_main_gate.py
# Purpose: Regression tests for the terminal auto-detach gate and headless startup in __main__.
"""Tests for the terminal auto-detach gate and headless startup in aethervault/__main__."""

import subprocess
import sys

import pytest

from aethervault.__main__ import _should_detach


class _FakeTTY:
    """Dummy stream that mimics sys.stdin; isatty() is controlled by the test."""

    def __init__(self, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


@pytest.mark.parametrize(
    "foreground, platform, stdin, expected",
    [
        # Linux, attached terminal, default foreground -> detach
        (False, "linux", _FakeTTY(True), True),
        # Linux, no tty (desktop launcher) -> no fork
        (False, "linux", _FakeTTY(False), False),
        # Linux, --foreground -> stay attached
        (True, "linux", _FakeTTY(True), False),
        # Linux, None stdin -> no fork
        (False, "linux", None, False),
        # macOS must never fork (multi-threaded Qt/AppKit -> CarbonCore crash)
        (False, "darwin", _FakeTTY(True), False),
        # Windows -> no fork
        (False, "win32", _FakeTTY(True), False),
        # Other Unix -> no fork
        (False, "freebsd", _FakeTTY(True), False),
    ],
)
def test_should_detach(foreground, platform, stdin, expected):
    assert _should_detach(foreground, platform, stdin) is expected


def test_main_module_imports_without_pyside6():
    """Importing __main__ must not pull in PySide6 (headless install support)."""
    code = "import sys, aethervault.__main__; assert 'PySide6' not in sys.modules; print('ok')"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_version_flag_works_headless():
    """`python -m aethervault --version` must not need the GUI extra."""
    result = subprocess.run(
        [sys.executable, "-m", "aethervault", "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "AetherVault v" in result.stdout


def test_gui_launch_without_pyside6_shows_install_hint():
    """A headless install that runs `aethervault` must fail with a helpful message."""
    code = (
        "import sys\n"
        "from importlib.abc import MetaPathFinder\n"
        "class Blocker(MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'PySide6' or name.startswith('PySide6.'):\n"
        "            raise ImportError('PySide6 blocked for test')\n"
        "        return None\n"
        "sys.meta_path.insert(0, Blocker())\n"
        "from aethervault.__main__ import run\n"
        "run()\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 1
    assert "PySide6" in result.stderr
    assert "aethervault-py[gui]" in result.stderr
