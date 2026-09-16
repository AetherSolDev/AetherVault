# Created: 2026-09-16
# Last Edited: 2026-09-16 17:35 CT (America/Chicago)
# Path: tests/test_app_settings_persist.py
# Purpose: Functional test that GUI settings (theme) persist to disk.

"""Functional test: toggling the theme writes settings to disk."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from aethervault.core import engine
from aethervault.core.engine import load_settings, save_settings


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_theme_toggle_persists(tmp_path, monkeypatch, qapp):
    monkeypatch.setattr(engine, "APP_SETTINGS_FILE", str(tmp_path / ".app_settings.json"))
    save_settings({"theme": "dark", "lockout_minutes": 3, "remote_backup_dir": ""})

    from aethervault.gui.app import PySidePWManager

    window = PySidePWManager()
    try:
        before = window.settings.get("theme")
        window.toggle_theme()
        after = window.settings.get("theme")
        assert before != after
        assert load_settings().get("theme") == after
    finally:
        window.close()
