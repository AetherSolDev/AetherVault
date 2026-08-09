# Created: 2026-08-09
# Last Edited: 2026-08-09 06:36 CT (America/Chicago)
# Path: tests/test_main_gate.py
# Purpose: Regression tests for the terminal auto-detach gate in __main__.
"""Tests for the terminal auto-detach gate in aethervault/__main__."""

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
