# Created: 2025-12-04
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: aethervault/gui/dialogs.py
# Purpose: Dialog classes for password generation, custom fields, TOTP setup, and docs.

"""Dialog classes for password generation, custom fields, TOTP setup, and documentation."""

import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QGridLayout,
    QWidget,
)

from aethervault import PROJECT_ROOT
from aethervault.core.password import generate_strong_password
from aethervault.core.totp import resolve_config, verify_code


def resource_path(relative_path):
    """Resolve a file path relative to the application bundle, project root, or package data."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = PROJECT_ROOT
    candidate = os.path.join(base_path, relative_path)
    if os.path.exists(candidate):
        return candidate
    pkg_candidate = os.path.join(base_path, "aethervault", relative_path)
    if os.path.exists(pkg_candidate):
        return pkg_candidate
    return candidate


class PasswordGeneratorDialog(QDialog):
    """A dialog window for generating a secure password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        """Initialize the dialog, build the UI, and generate an initial password."""
        self.setWindowTitle("Generate Secure Password")
        self.setMinimumSize(400, 350)
        self.resize(400, 350)
        self.generated_password = ""
        main_layout = QVBoxLayout(self)

        pass_group = QWidget()
        pass_layout = QHBoxLayout(pass_group)
        self.password_display = QLineEdit()
        self.password_display.setReadOnly(True)
        self.password_display.setFont(QFont("Monospace", 10))
        pass_layout.addWidget(self.password_display)
        regenerate_btn = QPushButton("\u21bb")
        regenerate_btn.setToolTip("Generate a new password")
        regenerate_btn.setFixedSize(30, 30)
        regenerate_btn.clicked.connect(self._generate_and_display)
        pass_layout.addWidget(regenerate_btn)
        main_layout.addWidget(pass_group)

        options_layout = QGridLayout()
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.addWidget(QLabel("Length:"), 0, 0)
        self.length_spinbox = QSpinBox()
        self.length_spinbox.setRange(8, 64)
        self.length_spinbox.setValue(18)
        self.length_spinbox.valueChanged.connect(self._generate_and_display)
        options_layout.addWidget(self.length_spinbox, 0, 1)

        self.check_lower = QCheckBox("Lowercase (a-z)")
        self.check_lower.setChecked(True)
        self.check_lower.stateChanged.connect(self._generate_and_display)
        options_layout.addWidget(self.check_lower, 1, 0)
        self.check_upper = QCheckBox("Uppercase (A-Z)")
        self.check_upper.setChecked(True)
        self.check_upper.stateChanged.connect(self._generate_and_display)
        options_layout.addWidget(self.check_upper, 1, 1)
        self.check_digit = QCheckBox("Digits (0-9)")
        self.check_digit.setChecked(True)
        self.check_digit.stateChanged.connect(self._generate_and_display)
        options_layout.addWidget(self.check_digit, 2, 0)
        self.check_symbol = QCheckBox("Symbols (!@#$)")
        self.check_symbol.setChecked(True)
        self.check_symbol.stateChanged.connect(self._generate_and_display)
        options_layout.addWidget(self.check_symbol, 2, 1)
        main_layout.addLayout(options_layout)
        main_layout.addStretch()

        button_layout = QHBoxLayout()
        use_btn = QPushButton("Use Password")
        cancel_btn = QPushButton("Cancel")
        use_btn.clicked.connect(self._accept_password)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(use_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        self._generate_and_display()

    def _get_options(self):
        """Return a dict of current password-generation options from the UI."""
        return {
            "length": self.length_spinbox.value(),
            "use_lower": self.check_lower.isChecked(),
            "use_upper": self.check_upper.isChecked(),
            "use_digit": self.check_digit.isChecked(),
            "use_symbol": self.check_symbol.isChecked(),
        }

    def _generate_and_display(self):
        """Generate a new password using current options and show it in the display."""
        options = self._get_options()
        if (
            not (
                options["use_lower"]
                or options["use_upper"]
                or options["use_digit"]
                or options["use_symbol"]
            )
            or options["length"] < 1
        ):
            self.password_display.setText("Select character set(s) and length > 0.")
            return
        new_password = generate_strong_password(**options)
        self.password_display.setText(new_password)

    def _accept_password(self):
        """Store the displayed password and accept the dialog."""
        self.generated_password = self.password_display.text()
        self.accept()

    def get_password(self) -> str:
        """Return the accepted password, or empty string if none was accepted."""
        return self.generated_password


class CustomFieldsDialog(QDialog):
    """A dialog window for editing the entry's custom fields (field/value pairs)."""

    def __init__(self, raw_json: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Fields")
        self.setMinimumSize(420, 300)
        self.resize(420, 320)
        main_layout = QVBoxLayout(self)

        main_layout.addWidget(QLabel("Add fields to store extra information:"))
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Field", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setFixedHeight(50)
        self.table.verticalHeader().hide()
        self.table.setMinimumHeight(150)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        main_layout.addWidget(self.table, stretch=1)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Field")
        self.add_btn.clicked.connect(self._add_row)
        self.remove_btn = QPushButton("- Remove Selected")
        self.remove_btn.clicked.connect(self._remove_row)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        ok_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        ok_row.addStretch()
        ok_row.addWidget(ok_btn)
        ok_row.addWidget(cancel_btn)
        main_layout.addLayout(ok_row)

        self._load_from_json(raw_json)

    def _load_from_json(self, raw: str):
        """Populate the table from a JSON array string."""
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
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(pair.get("field", "")))
                self.table.setItem(r, 1, QTableWidgetItem(pair.get("value", "")))

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(""))
        self.table.setItem(r, 1, QTableWidgetItem(""))

    def _remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def get_custom_fields_json(self) -> str:
        """Return the table contents serialized as a JSON array string."""
        pairs = []
        for r in range(self.table.rowCount()):
            f = self.table.item(r, 0)
            v = self.table.item(r, 1)
            pairs.append({
                "field": f.text() if f else "",
                "value": v.text() if v else "",
            })
        return json.dumps(pairs)


class DocumentationDialog(QDialog):
    """A dialog window to display the application's documentation from a file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        """Initialize the dialog, build the UI, and load documentation content."""
        self.setWindowTitle("AetherVault Documentation")
        self.setMinimumSize(700, 500)
        self.layout = QVBoxLayout(self)
        self.text_editor = QTextEdit()
        self.text_editor.setReadOnly(True)
        self.layout.addWidget(self.text_editor)
        self.help_file_path = resource_path(os.path.join("docs", "USER_GUIDE.md"))
        self.load_documentation()

    def load_documentation(self):
        """Read the documentation file and display its contents, or show an error."""
        try:
            with open(self.help_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_editor.setPlainText(content)
        except FileNotFoundError:
            self.text_editor.setPlainText(
                "ERROR: Documentation file (docs/USER_GUIDE.md) not found.\n"
                "Please ensure the file is bundled correctly with PyInstaller."
            )
        except OSError as e:
            self.text_editor.setPlainText(f"ERROR: Failed to load documentation: {e}")


class TOTPSetupDialog(QDialog):
    """Paste an ``otpauth://`` URI or base32 secret, with optional recovery codes.

    Callers read the result with :meth:`get_config` / :meth:`get_secret` /
    :meth:`get_recovery_codes` after ``exec()`` returns ``Accepted``.
    """

    def __init__(self, secret: str = "", recovery_codes: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Up 2FA / TOTP")
        self.setMinimumWidth(460)
        self._config: dict = {}
        self._recovery_codes = recovery_codes or ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Authenticator secret or otpauth:// URI:"))
        self.secret_input = QLineEdit()
        self.secret_input.setPlaceholderText("otpauth://totp/...   or   JBSWY3DPEHPK3PXP")
        self.secret_input.setToolTip(
            "Paste the secret shown during the site's 2FA setup, or the full otpauth:// URI"
        )
        layout.addWidget(self.secret_input)

        layout.addWidget(QLabel("Recovery codes (optional):"))
        self.recovery_input = QTextEdit()
        self.recovery_input.setPlaceholderText("One code per line")
        self.recovery_input.setMinimumHeight(80)
        layout.addWidget(self.recovery_input)

        layout.addWidget(QLabel("Verify current code (optional):"))
        self.verify_input = QLineEdit()
        self.verify_input.setPlaceholderText("e.g. 123456")
        self.verify_input.setToolTip(
            "Enter the code your authenticator shows right now to confirm the secret"
        )
        layout.addWidget(self.verify_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if secret:
            self.secret_input.setText(secret)
        if recovery_codes:
            self.recovery_input.setPlainText(recovery_codes)

    def _resolve(self) -> dict:
        text = self.secret_input.text().strip()
        if not text:
            raise ValueError("Paste an otpauth:// URI or a base32 secret.")
        return resolve_config(text)

    def accept(self):
        try:
            config = self._resolve()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid 2FA Secret", str(e))
            return
        code = self.verify_input.text().strip()
        if code and not verify_code(
            config["secret"], code, digits=config["digits"],
            period=config["period"], algorithm=config["algorithm"],
        ):
            QMessageBox.warning(
                self, "Verification Failed",
                "That code doesn't match. Check your device clock and try again.",
            )
            return
        self._config = config
        self._recovery_codes = self.recovery_input.toPlainText()
        super().accept()

    def get_secret(self) -> str:
        """Return the resolved base32 secret."""
        return self._config.get("secret", "")

    def get_raw(self) -> str:
        """Return the raw text the user entered (base32 secret or otpauth URI)."""
        return self.secret_input.text().strip()

    def get_config(self) -> dict:
        """Return the full resolved config (secret, period, digits, algorithm, ...)."""
        return dict(self._config)

    def get_recovery_codes(self) -> str:
        """Return the (possibly empty) recovery-codes text."""
        return self._recovery_codes
