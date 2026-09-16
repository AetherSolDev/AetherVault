# Created: 2026-07-27
# Last Edited: 2026-09-16 16:08 CT (America/Chicago)
# Path: aethervault/gui/credential_form.py
# Purpose: Credential detail/edit form widget for the right panel.

"""Credential detail/edit form widget for the right panel."""

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from aethervault.shared.models import CredentialEntry
from aethervault.gui.click_to_copy_filter import ClickToCopyFilter
from aethervault.gui.dialogs import CustomFieldsDialog, TOTPSetupDialog
from aethervault.gui.password_strength import PasswordStrengthBar
from aethervault.gui.totp_section import TotpSection


class CredentialForm(QWidget):
    save_requested = Signal(dict)
    cancel_requested = Signal()
    copy_requested = Signal(str, str)
    generate_password_requested = Signal()
    form_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_entry_id = None
        self.is_form_modified = False
        self.is_editing = False
        self.input_fields = {}
        self._custom_fields_json = "[]"
        self._notes_expanded = False
        self._totp_secret = ""
        self._recovery_codes = ""
        self._copy_buttons = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form_grid = QGridLayout()

        self.input_fields = {}
        fields = [
            ("Title", "title"), ("URL", "url"), ("Username", "username"),
            ("Password", "password"), ("Email", "email"), ("Phone", "phone"),
            ("Address", "address"), ("Category", "category"),
        ]

        row = 0
        for label_text, key in fields:
            label = QLabel(label_text + ":")
            line_edit = QLineEdit()
            self.input_fields[key] = line_edit
            line_edit.installEventFilter(
                ClickToCopyFilter(
                    self,
                    key,
                    lambda text, name=key: self.copy_requested.emit(text, name),
                )
            )
            form_grid.addWidget(label, row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
            if key == "password":
                self.password_entry_ref = line_edit
                self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Password)
                pc = QWidget()
                pl = QHBoxLayout(pc)
                pl.setContentsMargins(0, 0, 0, 0)
                pl.addWidget(line_edit)
                self.toggle_pass_btn = QPushButton("\U0001f441")
                self.toggle_pass_btn.setCheckable(True)
                self.toggle_pass_btn.setFixedWidth(36)
                self.toggle_pass_btn.setToolTip("Show / Hide password")
                self.toggle_pass_btn.clicked.connect(self._toggle_password_visibility)
                pl.addWidget(self.toggle_pass_btn)
                form_grid.addWidget(pc, row, 1)

                self.strength_bar = PasswordStrengthBar()
                form_grid.addWidget(self.strength_bar, row + 1, 1, 1, 2)
                line_edit.textChanged.connect(self._on_password_changed)
                self.strength_bar.hide()

                al = QHBoxLayout()
                al.setContentsMargins(0, 0, 0, 0)
                self.gen_pass_btn = QPushButton("Generate")
                self.gen_pass_btn.setToolTip("Open secure password generator")
                self.gen_pass_btn.clicked.connect(self.generate_password_requested.emit)
                al.addWidget(self.gen_pass_btn)
                copy_pass_btn = QPushButton("Copy")
                copy_pass_btn.setToolTip("Copy password to clipboard")
                copy_pass_btn.clicked.connect(
                    lambda checked, le=line_edit: self.copy_requested.emit(le.text(), "password")
                )
                al.addWidget(copy_pass_btn)
                self._copy_buttons.append(copy_pass_btn)
                form_grid.addLayout(al, row, 2)
                row += 1
            else:
                form_grid.addWidget(line_edit, row, 1)
                if key in ["url", "username", "email"]:
                    copy_btn = QPushButton("Copy")
                    copy_btn.setToolTip(f"Copy {label_text} to clipboard")
                    copy_btn.clicked.connect(
                        lambda checked, le=line_edit, n=label_text.lower():
                            self.copy_requested.emit(le.text(), n)
                    )
                    form_grid.addWidget(copy_btn, row, 2)
                    self._copy_buttons.append(copy_btn)
            if key != "password":
                line_edit.textChanged.connect(self._on_field_modified)
            row += 1

        tags_row = row
        form_grid.addWidget(QLabel("Tags:"), tags_row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        self.tags_entry = QLineEdit()
        self.tags_entry.setPlaceholderText("tag1, tag2, tag3")
        self.tags_entry.textChanged.connect(self._on_field_modified)
        self.input_fields["tags"] = self.tags_entry
        form_grid.addWidget(self.tags_entry, tags_row, 1, 1, 2)
        row += 1

        form_grid.setColumnMinimumWidth(0, 90)
        form_grid.setColumnStretch(1, 1)
        form_grid.setVerticalSpacing(4)
        layout.addLayout(form_grid, stretch=2)

        # Notes — collapsible section with preview
        self.notes_toggle = QToolButton()
        self.notes_toggle.setText("\u25b6 Notes")  # ▶ Notes
        self.notes_toggle.setToolTip("Show or hide the notes editor for this entry")
        self.notes_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.notes_toggle.setCheckable(True)
        self.notes_toggle.setAutoRaise(True)
        self.notes_toggle.clicked.connect(self._toggle_notes)
        layout.addWidget(self.notes_toggle)

        self.notes_preview = QLabel()
        self.notes_preview.setWordWrap(True)
        self.notes_preview.setTextFormat(Qt.PlainText)
        self.notes_preview.setStyleSheet("color: gray;")
        layout.addWidget(self.notes_preview)

        self.notes_container = QWidget()
        notes_container_layout = QVBoxLayout(self.notes_container)
        notes_container_layout.setContentsMargins(0, 0, 0, 0)
        notes_container_layout.setSpacing(2)
        nt = QHBoxLayout()
        nt.setSpacing(2)
        self.notes_bold_btn = QPushButton("B")
        self.notes_bold_btn.setFixedWidth(30)
        self.notes_bold_btn.setCheckable(True)
        self.notes_bold_btn.clicked.connect(lambda: self.notes_entry.setFontWeight(
            QFont.Bold if self.notes_bold_btn.isChecked() else QFont.Normal
        ))
        nt.addWidget(self.notes_bold_btn)
        self.notes_italic_btn = QPushButton("I")
        self.notes_italic_btn.setFixedWidth(30)
        self.notes_italic_btn.setCheckable(True)
        self.notes_italic_btn.clicked.connect(lambda: self.notes_entry.setFontItalic(
            self.notes_italic_btn.isChecked()
        ))
        nt.addWidget(self.notes_italic_btn)
        self.notes_underline_btn = QPushButton("U")
        self.notes_underline_btn.setFixedWidth(30)
        self.notes_underline_btn.setCheckable(True)
        self.notes_underline_btn.clicked.connect(lambda: self.notes_entry.setFontUnderline(
            self.notes_underline_btn.isChecked()
        ))
        nt.addWidget(self.notes_underline_btn)
        nt.addStretch()
        notes_container_layout.addLayout(nt)
        self.notes_entry = QTextEdit()
        self.notes_entry.textChanged.connect(self._on_notes_changed)
        self.notes_entry.setMinimumHeight(120)
        self.notes_entry.installEventFilter(
            ClickToCopyFilter(
                self,
                "notes",
                lambda text, n="notes": self.copy_requested.emit(text, n),
            )
        )
        notes_container_layout.addWidget(self.notes_entry)
        layout.addWidget(self.notes_container)
        self.notes_container.hide()

        # Custom Fields — button opens dialog
        cf_row = QHBoxLayout()
        self.cf_btn = QPushButton("Custom Fields...")
        self.cf_btn.setToolTip("Edit custom fields for this entry")
        self.cf_btn.clicked.connect(self._open_custom_fields_dialog)
        self.cf_count_label = QLabel()
        self.cf_count_label.setStyleSheet("color: gray;")
        cf_row.addWidget(self.cf_btn)
        cf_row.addWidget(self.cf_count_label)
        cf_row.addStretch()
        layout.addLayout(cf_row)

        # 2FA / TOTP — setup button (no secret) or live code section (secret present)
        totp_row = QHBoxLayout()
        self.totp_btn = QPushButton("Set up 2FA...")
        self.totp_btn.setToolTip("Add a TOTP authenticator secret to this entry")
        self.totp_btn.clicked.connect(self._open_totp_dialog)
        totp_row.addWidget(self.totp_btn)
        totp_row.addStretch()
        layout.addLayout(totp_row)

        self.totp_section = TotpSection()
        self.totp_section.copy_requested.connect(self.copy_requested.emit)
        self.totp_section.remove_requested.connect(self._remove_totp)
        layout.addWidget(self.totp_section)

        layout.addStretch(1)

        fbl = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save this entry (Ctrl+S)")
        self.save_btn.clicked.connect(lambda: self.save_requested.emit(self.get_form_data()))
        self.save_btn.hide()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setToolTip("Discard changes (Esc)")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_btn.hide()
        fbl.addWidget(self.save_btn)
        fbl.addWidget(self.cancel_btn)
        fbl.addStretch()
        layout.addLayout(fbl)

        self.gen_pass_btn.hide()
        self._set_readonly(True)

    def _toggle_notes(self):
        """Expand or collapse the notes editor section."""
        self._notes_expanded = self.notes_toggle.isChecked()
        self.notes_toggle.setText("\u25bc Notes" if self._notes_expanded else "\u25b6 Notes")
        self.notes_container.setVisible(self._notes_expanded)
        self.notes_preview.setVisible(not self._notes_expanded)

    def _on_notes_changed(self):
        self._update_notes_preview()
        self._on_field_modified()

    def _update_notes_preview(self):
        text = self.notes_entry.toPlainText().strip()
        if text:
            single = " ".join(text.split())
            self.notes_preview.setText(single[:80] + ("..." if len(single) > 80 else ""))
        else:
            self.notes_preview.setText("No notes.")

    def _open_custom_fields_dialog(self):
        dlg = CustomFieldsDialog(self._custom_fields_json, self)
        if dlg.exec() == QDialog.Accepted:
            self._custom_fields_json = dlg.get_custom_fields_json()
            self._update_cf_count()
            self._on_field_modified()

    def _open_totp_dialog(self):
        dlg = TOTPSetupDialog(self._totp_secret, self._recovery_codes, self)
        if dlg.exec() == QDialog.Accepted:
            self._totp_secret = dlg.get_raw()
            self._recovery_codes = dlg.get_recovery_codes()
            self._refresh_totp()
            self._on_field_modified()

    def _remove_totp(self):
        self._totp_secret = ""
        self._recovery_codes = ""
        self._refresh_totp()
        self._on_field_modified()

    def _refresh_totp(self):
        """Show the live code section when a secret is set, else the setup button."""
        if self._totp_secret:
            self.totp_section.set_entry(self._totp_secret, self._recovery_codes)
            self.totp_section.show()
            self.totp_btn.hide()
        else:
            self.totp_section.clear()
            self.totp_section.hide()
            self.totp_btn.show()

    def _update_cf_count(self):
        try:
            pairs = json.loads(self._custom_fields_json)
            count = len(pairs) if isinstance(pairs, list) else 0
        except (json.JSONDecodeError, TypeError):
            count = 0
        self.cf_count_label.setText(f"({count} field{'s' if count != 1 else ''})")

    def _toggle_password_visibility(self, checked):
        if checked:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_password_changed(self, text):
        if self.is_editing:
            self.strength_bar.evaluate(text)
            self._on_field_modified()

    def _on_field_modified(self):
        if self.is_editing:
            self.is_form_modified = True
            self.save_btn.setEnabled(True)
            self.form_modified.emit()

    def get_form_data(self) -> dict:
        data = {k: e.text() for k, e in self.input_fields.items()}
        data["notes"] = self.notes_entry.toHtml()
        data["custom_fields"] = self._custom_fields_json
        data["totp_secret"] = self._totp_secret
        data["recovery_codes"] = self._recovery_codes
        data["db_id"] = self.current_entry_id
        return data

    def fill_form(self, entry: CredentialEntry):
        for key, le in self.input_fields.items():
            v = getattr(entry, key, "") or ""
            le.blockSignals(True)
            le.setText(v)
            le.blockSignals(False)
        self.notes_entry.blockSignals(True)
        self.notes_entry.setText(entry.notes or "")
        self.notes_entry.blockSignals(False)
        self._custom_fields_json = entry.custom_fields or "[]"
        self._update_cf_count()
        self._totp_secret = entry.totp_secret or ""
        self._recovery_codes = entry.recovery_codes or ""
        self._refresh_totp()
        self._update_notes_preview()
        self.current_entry_id = entry.db_id
        self.is_form_modified = False
        if self.password_entry_ref.echoMode() == QLineEdit.EchoMode.Normal:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setChecked(False)

    def clear_form(self):
        for le in self.input_fields.values():
            le.blockSignals(True)
            le.clear()
            le.blockSignals(False)
        self.notes_entry.blockSignals(True)
        self.notes_entry.clear()
        self.notes_entry.blockSignals(False)
        self._custom_fields_json = "[]"
        self._update_cf_count()
        self._totp_secret = ""
        self._recovery_codes = ""
        self._refresh_totp()
        self._update_notes_preview()
        if self.password_entry_ref.echoMode() == QLineEdit.EchoMode.Normal:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setChecked(False)
        self.current_entry_id = None
        self.is_form_modified = False

    def _set_readonly(self, ro: bool):
        for le in self.input_fields.values():
            le.setReadOnly(ro)
        self.notes_entry.setReadOnly(ro)
        self.toggle_pass_btn.setEnabled(not ro)
        self.notes_toggle.setEnabled(True)
        self.cf_btn.setEnabled(True)
        self.cf_btn.setVisible(True)
        self.totp_btn.setEnabled(not ro)
        self.totp_section.set_editable(not ro)
        for btn in [self.notes_bold_btn, self.notes_italic_btn, self.notes_underline_btn]:
            btn.setVisible(not ro)

    def enter_view_mode(self):
        self.is_editing = False
        self._set_readonly(True)
        self.gen_pass_btn.hide()
        self.save_btn.hide()
        self.cancel_btn.hide()
        self.strength_bar.hide()

    def enter_edit_mode(self):
        if self.current_entry_id is None:
            return
        self.is_editing = True
        self._set_readonly(False)
        self.gen_pass_btn.show()
        self.save_btn.show()
        self.cancel_btn.show()
        self.save_btn.setEnabled(False)
        self.is_form_modified = False
        self.password_entry_ref.setFocus()

    def enter_new_mode(self):
        self.is_editing = True
        self.clear_form()
        self._set_readonly(False)
        self.gen_pass_btn.show()
        self.save_btn.show()
        self.cancel_btn.show()
        self.save_btn.setEnabled(False)
        self.is_form_modified = False
        self.input_fields["title"].setFocus()

    def resizeEvent(self, event):
        """Hide the per-field Copy buttons on narrow forms — clicking a field copies it."""
        super().resizeEvent(event)
        show_copy = self.width() >= 560
        for btn in getattr(self, "_copy_buttons", []):
            btn.setVisible(show_copy)

    def set_password(self, password: str):
        self.password_entry_ref.setText(password)
        self._on_field_modified()
