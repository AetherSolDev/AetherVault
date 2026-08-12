# Created: 2026-08-05
# Last Edited: 2026-08-12 16:33 CT (America/Chicago)
# Path: tests/test_credential_form.py
# Purpose: Unit tests for the CredentialForm copy buttons (regression for late-binding lambda bug)
#          and the collapsible notes / custom-fields dialog integration (v6.6.1).

"""Unit tests for the CredentialForm copy buttons and notes/custom-fields integration."""

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


class TestNotesCollapsible:
    def test_notes_collapsed_by_default(self, form):
        """Notes section starts collapsed with the preview visible."""
        assert form._notes_expanded is False
        assert form.notes_container.isHidden() is True

    def test_toggle_expands_and_collapses(self, form):
        form.show()
        form.notes_toggle.click()
        assert form._notes_expanded is True
        assert form.notes_container.isVisibleTo(form) is True
        assert form.notes_preview.isHidden() is True

        form.notes_toggle.click()
        assert form._notes_expanded is False
        assert form.notes_container.isVisibleTo(form) is False
        assert form.notes_preview.isVisibleTo(form) is True

    def test_notes_preview_shows_plain_text(self, form):
        """Preview strips HTML formatting and shows plain text, truncated to 80 chars."""
        form.notes_entry.setHtml("<p>line one<br>line two with <b>tags</b></p>")
        form._update_notes_preview()
        preview = form.notes_preview.text()
        assert "line one line two with tags" in preview
        assert len(preview) <= 85

    def test_fill_form_sets_notes_and_preview(self, form):
        entry = CredentialEntry(title="T", password="p", notes="<p>hello <b>world</b></p>")
        form.fill_form(entry)
        assert "hello world" in form.notes_preview.text()

    def test_fill_form_keeps_custom_fields_json(self, form):
        entry = CredentialEntry(
            title="T", password="p",
            custom_fields='[{"field": "PIN", "value": "1234"}, {"field": "OTP", "value": "999"}]',
        )
        form.fill_form(entry)
        assert "PIN" in form._custom_fields_json
        assert "OTP" in form._custom_fields_json
        assert form.get_form_data()["custom_fields"] == entry.custom_fields


class TestCustomFieldsDialogIntegration:
    def test_roundtrip_via_dialog(self, form):
        from aethervault.gui.dialogs import CustomFieldsDialog
        dlg = CustomFieldsDialog('[{"field": "API", "value": "key"}]')
        dlg._add_row()
        dlg.table.item(1, 0).setText("URL")
        dlg.table.item(1, 1).setText("https://example.com")
        out = dlg.get_custom_fields_json()
        assert '"API"' in out
        assert '"URL"' in out

    def test_form_stores_dialog_result(self, form):
        from aethervault.gui.dialogs import CustomFieldsDialog
        dlg = CustomFieldsDialog()
        dlg._add_row()
        dlg.table.item(0, 0).setText("Key")
        dlg.table.item(0, 1).setText("Value")
        form._custom_fields_json = dlg.get_custom_fields_json()
        form._update_cf_count()
        assert form.cf_count_label.text() == "(1 field)"
        assert form.get_form_data()["custom_fields"] == '[{"field": "Key", "value": "Value"}]'
