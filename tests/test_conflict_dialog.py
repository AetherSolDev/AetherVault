# Created: 2026-09-16
# Last Edited: 2026-09-16 15:45 CT (America/Chicago)
# Path: tests/test_conflict_dialog.py
# Purpose: Regression tests for ImportConflictDialog (F22: missing QWidget import).

"""Regression tests for the import conflict dialog."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from aethervault.gui.conflict_dialog import ImportConflictDialog

CONFLICTS = [{
    "vault": {"title": "GitHub", "username": "octocat", "password": "old"},
    "import": {"title": "GitHub", "username": "octocat", "password": "new"},
}]


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_constructs_without_error(qapp):
    """F22: the dialog used QWidget without importing it and crashed on open."""
    dialog = ImportConflictDialog(CONFLICTS)
    assert dialog.decisions == {("github", "octocat"): "keep_vault"}


def test_bulk_set_replace(qapp):
    dialog = ImportConflictDialog(CONFLICTS)
    dialog._bulk_set("replace")
    assert dialog.decisions[("github", "octocat")] == "replace"


def test_bulk_set_keep_vault(qapp):
    dialog = ImportConflictDialog(CONFLICTS)
    dialog._bulk_set("replace")
    dialog._bulk_set("keep_vault")
    assert dialog.decisions[("github", "octocat")] == "keep_vault"
