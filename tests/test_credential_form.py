# Created: 2026-08-05
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: tests/test_credential_form.py
# Purpose: Unit tests for the CredentialForm copy buttons, notes/custom-fields, and TOTP.

"""Unit tests for the CredentialForm copy buttons, notes/custom-fields, and TOTP."""

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


class TestTotpIntegration:
    """A21 — TOTP section in the credential form."""

    SECRET = "JBSWY3DPEHPK3PXP"

    def test_section_hidden_and_button_shown_without_secret(self, form):
        form.fill_form(CredentialEntry(title="T", password="p"))
        assert form.totp_section.isHidden() is True
        assert form.totp_btn.isHidden() is False

    def test_section_shown_with_secret(self, form):
        form.fill_form(CredentialEntry(title="T", password="p", totp_secret=self.SECRET))
        assert form.totp_section.isHidden() is False
        assert form.totp_btn.isHidden() is True
        assert len(form.totp_section.current_code()) == 6
        assert form.totp_section.current_code().isdigit()

    def test_countdown_in_range(self, form):
        form.fill_form(CredentialEntry(title="T", password="p", totp_secret=self.SECRET))
        assert 0 <= form.totp_section.countdown.value() <= 30

    def test_form_data_includes_totp(self, form):
        entry = CredentialEntry(title="T", password="p", totp_secret=self.SECRET,
                                recovery_codes="a\nb")
        form.fill_form(entry)
        data = form.get_form_data()
        assert data["totp_secret"] == self.SECRET
        assert data["recovery_codes"] == "a\nb"

    def test_remove_clears_totp_and_marks_modified(self, form):
        form.fill_form(CredentialEntry(title="T", password="p", totp_secret=self.SECRET))
        form.is_editing = True
        form.totp_section.remove_requested.emit()
        assert form._totp_secret == ""
        assert form._recovery_codes == ""
        assert form.totp_section.isHidden() is True
        assert form.get_form_data()["totp_secret"] == ""

    def test_copy_code_emits_code(self, form):
        form.fill_form(CredentialEntry(title="T", password="p", totp_secret=self.SECRET))
        emissions = []
        form.copy_requested.connect(lambda text, name: emissions.append((name, text)))
        form.totp_section.copy_btn.click()
        assert emissions
        assert emissions[0][0] == "2FA code"
        assert emissions[0][1].isdigit() and len(emissions[0][1]) == 6

    def test_otpauth_uri_honours_custom_digits(self, form):
        import base64
        secret = base64.b32encode(b"12345678901234567890").decode("ascii")
        uri = f"otpauth://totp/Acme:joe?secret={secret}&digits=8"
        form.fill_form(CredentialEntry(title="T", password="p", totp_secret=uri))
        assert len(form.totp_section.current_code()) == 8


class TestTotpSetupDialog:
    def test_raw_secret_round_trip(self, qapp):
        from aethervault.gui.dialogs import TOTPSetupDialog
        dlg = TOTPSetupDialog()
        dlg.secret_input.setText("JBSWY3DPEHPK3PXP")
        dlg.recovery_input.setPlainText("one\ntwo")
        dlg.accept()
        assert dlg.get_secret() == "JBSWY3DPEHPK3PXP"
        assert dlg.get_raw() == "JBSWY3DPEHPK3PXP"
        assert dlg.get_recovery_codes() == "one\ntwo"

    def test_otpauth_uri_round_trip(self, qapp):
        import base64
        from aethervault.gui.dialogs import TOTPSetupDialog
        secret = base64.b32encode(b"12345678901234567890").decode("ascii")
        uri = f"otpauth://totp/Acme:joe?secret={secret}&digits=8&period=60"
        dlg = TOTPSetupDialog()
        dlg.secret_input.setText(uri)
        dlg.accept()
        assert dlg.get_secret() == secret
        assert dlg.get_raw() == uri
        assert dlg.get_config()["digits"] == 8

    def test_invalid_secret_is_rejected(self, qapp, monkeypatch):
        from aethervault.gui import dialogs
        from aethervault.gui.dialogs import TOTPSetupDialog
        monkeypatch.setattr(dialogs.QMessageBox, "warning", lambda *a, **k: None)
        dlg = TOTPSetupDialog()
        dlg.secret_input.setText("@@@@")
        dlg.accept()
        assert dlg.get_secret() == ""

    def test_wrong_verify_code_is_rejected(self, qapp, monkeypatch):
        from aethervault.gui import dialogs
        from aethervault.gui.dialogs import TOTPSetupDialog
        monkeypatch.setattr(dialogs.QMessageBox, "warning", lambda *a, **k: None)
        dlg = TOTPSetupDialog()
        dlg.secret_input.setText("JBSWY3DPEHPK3PXP")
        dlg.verify_input.setText("000000")
        dlg.accept()
        assert dlg.get_secret() == ""
