# Created: 2026-09-16
# Last Edited: 2026-09-16 17:35 CT (America/Chicago)
# Path: tests/test_portable.py
# Purpose: Functional tests for portable-mode marker handling.

"""Tests for portable mode (marker file) toggling."""

import aethervault
from aethervault import disable_portable_mode, enable_portable_mode, is_portable


def test_portable_toggle(tmp_path, monkeypatch):
    monkeypatch.setattr(aethervault, "PROJECT_ROOT", str(tmp_path))

    assert is_portable() is False
    assert enable_portable_mode() is True
    assert is_portable() is True
    assert (tmp_path / ".portable").exists()

    assert disable_portable_mode() is True
    assert is_portable() is False
    assert not (tmp_path / ".portable").exists()


def test_enable_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(aethervault, "PROJECT_ROOT", str(tmp_path))
    assert enable_portable_mode() is True
    assert enable_portable_mode() is True
    assert is_portable() is True
