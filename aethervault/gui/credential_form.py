# Created: 2026-07-27
# Last Edited: 2026-08-05 15:52 CT (America/Chicago)
# Path: aethervault/gui/credential_form.py
# Purpose: Credential detail/edit form widget for the right panel.

"""Credential detail/edit form widget for the right panel."""

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from aethervault.shared.models import CredentialEntry
from aethervault.gui.click_to_copy_filter import ClickToCopyFilter
from aethervault.gui.password_strength import PasswordStrengthBar


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

        notes_row = row
        form_grid.addWidget(QLabel("Notes:"), notes_row, 0, alignment=Qt.AlignTop)
        notes_container = QWidget()
        notes_container_layout = QVBoxLayout(notes_container)
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
        self.notes_entry.textChanged.connect(self._on_field_modified)
        self.notes_entry.installEventFilter(
            ClickToCopyFilter(
                self,
                "notes",
                lambda text, n="notes": self.copy_requested.emit(text, n),
            )
        )
        notes_container_layout.addWidget(self.notes_entry)
        form_grid.addWidget(notes_container, notes_row, 1, 1, 2)

        form_grid.setColumnMinimumWidth(0, 90)
        form_grid.setColumnStretch(1, 1)
        form_grid.setVerticalSpacing(4)
        layout.addLayout(form_grid, stretch=2)

        cf_label = QLabel("Custom Fields:")
        layout.addWidget(cf_label)
        self.custom_fields_table = QTableWidget()
        self.custom_fields_table.setColumnCount(2)
        self.custom_fields_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.custom_fields_table.horizontalHeader().setStretchLastSection(True)
        self.custom_fields_table.horizontalHeader().setFixedHeight(50)
        self.custom_fields_table.verticalHeader().hide()
        self.custom_fields_table.setMinimumHeight(80)
        layout.addWidget(self.custom_fields_table, stretch=1)
        cf_buttons = QHBoxLayout()
        self.cf_add_btn = QPushButton("+ Add Field")
        self.cf_add_btn.clicked.connect(self._add_custom_field_row)
        self.cf_remove_btn = QPushButton("- Remove Selected")
        self.cf_remove_btn.clicked.connect(self._remove_custom_field_row)
        cf_buttons.addWidget(self.cf_add_btn)
        cf_buttons.addWidget(self.cf_remove_btn)
        cf_buttons.addStretch()
        layout.addLayout(cf_buttons)

        fbl = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(lambda: self.save_requested.emit(self.get_form_data()))
        self.save_btn.hide()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_btn.hide()
        fbl.addWidget(self.save_btn)
        fbl.addWidget(self.cancel_btn)
        fbl.addStretch()
        layout.addLayout(fbl)

        self.gen_pass_btn.hide()
        self._set_readonly(True)

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
        data["custom_fields"] = self._custom_fields_to_json()
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
        self._custom_fields_from_entry(entry.custom_fields or "")
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
        self.custom_fields_table.setRowCount(0)
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
        self.custom_fields_table.setEditTriggers(
            QTableWidget.NoEditTriggers if ro else QTableWidget.DoubleClicked
        )
        self.cf_add_btn.setVisible(not ro)
        self.cf_remove_btn.setVisible(not ro)
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

    def set_password(self, password: str):
        self.password_entry_ref.setText(password)
        self._on_field_modified()

    def _add_custom_field_row(self):
        r = self.custom_fields_table.rowCount()
        self.custom_fields_table.insertRow(r)
        self.custom_fields_table.setItem(r, 0, QTableWidgetItem(""))
        self.custom_fields_table.setItem(r, 1, QTableWidgetItem(""))
        self._on_field_modified()

    def _remove_custom_field_row(self):
        r = self.custom_fields_table.currentRow()
        if r >= 0:
            self.custom_fields_table.removeRow(r)
            self._on_field_modified()

    def _custom_fields_from_entry(self, raw: str):
        self.custom_fields_table.setRowCount(0)
        if not raw:
            return
        try:
            pairs = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(pairs, list):
            return
        for pair in pairs:
            if isinstance(pair, dict):
                r = self.custom_fields_table.rowCount()
                self.custom_fields_table.insertRow(r)
                self.custom_fields_table.setItem(r, 0, QTableWidgetItem(pair.get("field", "")))
                self.custom_fields_table.setItem(r, 1, QTableWidgetItem(pair.get("value", "")))

    def _custom_fields_to_json(self) -> str:
        pairs = []
        for r in range(self.custom_fields_table.rowCount()):
            f = self.custom_fields_table.item(r, 0)
            v = self.custom_fields_table.item(r, 1)
            pairs.append({
                "field": f.text() if f else "",
                "value": v.text() if v else "",
            })
        return json.dumps(pairs)
