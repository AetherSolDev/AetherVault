# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
# Path: aethervault/gui/password_strength.py
# Purpose: Progress bar widget that evaluates and displays password strength.

"""Progress bar widget that evaluates and displays password strength."""

from PySide6.QtWidgets import QProgressBar

from aethervault.core_logic import score_password


class PasswordStrengthBar(QProgressBar):
    """Progress bar that evaluates and displays password strength."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(True)
        self.setFixedHeight(15)
        self.hide()

    def evaluate(self, password: str):
        if not password:
            self.hide()
            return
        self.show()
        score = score_password(password)
        self.setValue(score)
        if score < 30:
            self.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff5555; border-radius: 3px; }"
            )
        elif score < 60:
            self.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff9f43; border-radius: 3px; }"
            )
        elif score < 80:
            self.setStyleSheet(
                "QProgressBar::chunk { background-color: #54a0ff; border-radius: 3px; }"
            )
        else:
            self.setStyleSheet(
                "QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }"
            )
