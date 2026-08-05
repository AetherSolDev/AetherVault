# Created: 2026-08-05
# Last Edited: 2026-08-05 15:25 CT (America/Chicago)
# Path: tests/test_credential_form.py
# Purpose: Unit tests for the CredentialForm copy buttons (regression for late-binding lambda bug).

"""Unit tests for the CredentialForm copy buttons."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from aethervault.shared.models import CredentialEntry
from aethervault.gui.credential_form import CredentialForm


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def form(qapp):
    f = CredentialForm()
    yield f


def _click_copy_buttons(form):
    """Return dict of field->emitted text from all Copy buttons."""
    emissions = []
    form.copy_requested.connect(lambda text, name: emissions.append((name, text)))
    for btn in form.findChildren(QPushButton):
        tip = btn.toolTip()
        if tip.startswith("Copy"):
            btn.click()
    return emissions


class TestCredentialFormCopy:
    def test_password_copy_button_copies_password_not_last_field(self, form):
        """Regression: password Copy button must emit the password field's text,
        not the last field created in the form loop (late-binding bug)."""
        entry = CredentialEntry(
            title="GitHub",
            url="https://github.com",
            username="octocat",
            password="super-secret-123",
            category="Social",
            email="octo@example.com",
        )
        form.fill_form(entry)

        emissions = _click_copy_buttons(form)
        emissions_by_field = dict(emissions)

        assert emissions_by_field["password"] == "super-secret-123"
        assert emissions_by_field["username"] == "octocat"
        assert emissions_by_field["url"] == "https://github.com"
        assert emissions_by_field["email"] == "octo@example.com"

    def test_password_copy_button_not_capturing_category(self, form):
        """Ensure the password copy button no longer emits the category field text."""
        entry = CredentialEntry(
            title="X",
            password="pw-abc",
            category="Work",
        )
        form.fill_form(entry)

        emissions = _click_copy_buttons(form)
        emissions_by_field = dict(emissions)

        assert emissions_by_field["password"] == "pw-abc"
        assert emissions_by_field["password"] != "Work"
