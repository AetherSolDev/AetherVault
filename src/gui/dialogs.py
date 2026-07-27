# Created: 2025-12-04
# Last Edited: 2026-07-27 13:47 CT (America/Chicago)
# Path: src/gui/dialogs.py
# Purpose: Dialog classes for password generation and documentation viewing.

"""Dialog classes for password generation and documentation viewing."""

import os
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QGridLayout,
    QWidget,
)

from src import PROJECT_ROOT
from src.core_logic import generate_strong_password


def resource_path(relative_path):
    """Resolve a file path relative to the application bundle or project root."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = PROJECT_ROOT
    return os.path.join(base_path, relative_path)


class PasswordGeneratorDialog(QDialog):
    """A dialog window for generating a secure password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        """Initialize the dialog, build the UI, and generate an initial password."""
        self.setWindowTitle("Generate Secure Password")
        self.setFixedSize(400, 350)
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
        except Exception as e:
            self.text_editor.setPlainText(f"ERROR: Failed to load documentation: {e}")
