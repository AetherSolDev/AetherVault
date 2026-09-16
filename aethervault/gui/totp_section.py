# Created: 2026-09-16
# Last Edited: 2026-09-16 16:08 CT (America/Chicago)
# Path: aethervault/gui/totp_section.py
# Purpose: Live TOTP code + countdown widget shown in the credential form (A21).

"""Live TOTP code widget with a 30s countdown and recovery-codes viewer."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from aethervault.core.totp import generate_code, resolve_config


class TotpSection(QWidget):
    """Displays a rolling TOTP code for an entry, with copy/remove actions.

    Hidden until :meth:`set_entry` is called with a non-empty secret. Emits
    ``copy_requested(text, label)`` so the host window can reuse its clipboard
    handling (including the 15s auto-clear).
    """

    copy_requested = Signal(str, str)
    remove_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secret = ""
        self._period = 30
        self._digits = 6
        self._algorithm = "SHA1"
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._build_ui()
        self.setVisible(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.code_label = QLabel("------")
        self.code_label.setFont(QFont("Monospace", 16))
        self.code_label.setToolTip("Current one-time code — updates automatically")
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(self.code_label)

        self.countdown = QProgressBar()
        self.countdown.setRange(0, 30)
        self.countdown.setValue(30)
        self.countdown.setTextVisible(False)
        self.countdown.setFixedSize(90, 12)
        self.countdown.setToolTip("Time remaining before the code changes")
        row.addWidget(self.countdown)

        self.copy_btn = QPushButton("Copy Code")
        self.copy_btn.setToolTip("Copy the current code (clipboard clears after 15s)")
        self.copy_btn.clicked.connect(self._copy_code)
        row.addWidget(self.copy_btn)

        self.remove_btn = QPushButton("Remove 2FA")
        self.remove_btn.setToolTip("Remove the TOTP secret and recovery codes from this entry")
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        row.addWidget(self.remove_btn)
        row.addStretch()
        layout.addLayout(row)

        self.recovery_toggle = QToolButton()
        self.recovery_toggle.setText("\u25b6 Recovery Codes")
        self.recovery_toggle.setCheckable(True)
        self.recovery_toggle.setAutoRaise(True)
        self.recovery_toggle.setToolTip("Show the saved recovery codes")
        self.recovery_toggle.clicked.connect(self._toggle_recovery)
        layout.addWidget(self.recovery_toggle)

        self.recovery_view = QTextEdit()
        self.recovery_view.setReadOnly(True)
        self.recovery_view.setMinimumHeight(70)
        self.recovery_view.hide()
        layout.addWidget(self.recovery_view)

        self.recovery_copy_btn = QPushButton("Copy Recovery Codes")
        self.recovery_copy_btn.setToolTip("Copy every recovery code to the clipboard")
        self.recovery_copy_btn.clicked.connect(
            lambda: self.copy_requested.emit(
                self.recovery_view.toPlainText(), "recovery codes"
            )
        )
        self.recovery_copy_btn.hide()
        layout.addWidget(self.recovery_copy_btn)

    def set_entry(self, value: str, recovery_codes: str = "") -> None:
        """Show the code for ``value`` (a base32 secret or otpauth URI)."""
        self.clear()
        if not value:
            return
        try:
            config = resolve_config(value)
        except ValueError:
            self.code_label.setText("invalid")
            self.show()
            return
        self._secret = config["secret"]
        self._period = config["period"]
        self._digits = config["digits"]
        self._algorithm = config["algorithm"]
        self.countdown.setRange(0, self._period)
        self._set_recovery(recovery_codes or "")
        self._tick()
        self._timer.start()
        self.show()

    def clear(self) -> None:
        """Stop the timer and reset the widget to its hidden state."""
        self._timer.stop()
        self._secret = ""
        self.code_label.setText("------")
        self.countdown.setRange(0, 30)
        self.countdown.setValue(0)
        self.recovery_view.clear()
        self.recovery_view.hide()
        self.recovery_copy_btn.hide()
        self.recovery_toggle.setChecked(False)
        self.recovery_toggle.setText("\u25b6 Recovery Codes")
        self.recovery_toggle.hide()
        self.hide()

    def set_editable(self, editable: bool) -> None:
        """Enable/disable the destructive Remove button (copy stays available)."""
        self.remove_btn.setEnabled(editable)

    def current_code(self) -> str:
        """Return the displayed code without the visual grouping space."""
        return self.code_label.text().replace(" ", "")

    def _tick(self) -> None:
        if not self._secret:
            return
        now = time.time()
        try:
            code = generate_code(
                self._secret, now, self._digits, self._period, self._algorithm
            )
        except ValueError:
            self.code_label.setText("invalid")
            self._timer.stop()
            return
        self.code_label.setText(f"{code[:3]} {code[3:]}" if len(code) == 6 else code)
        self.countdown.setValue(self._period - int(now) % self._period)

    def _copy_code(self) -> None:
        code = self.current_code()
        if code and code != "------":
            self.copy_requested.emit(code, "2FA code")

    def _set_recovery(self, codes: str) -> None:
        has_codes = bool(codes.strip())
        self.recovery_view.setPlainText(codes)
        self.recovery_toggle.setVisible(has_codes)
        self.recovery_toggle.setChecked(False)
        self.recovery_toggle.setText("\u25b6 Recovery Codes")
        self.recovery_view.hide()
        self.recovery_copy_btn.hide()

    def _toggle_recovery(self) -> None:
        expanded = self.recovery_toggle.isChecked()
        self.recovery_toggle.setText(
            "\u25bc Recovery Codes" if expanded else "\u25b6 Recovery Codes"
        )
        self.recovery_view.setVisible(expanded)
        self.recovery_copy_btn.setVisible(expanded)

    def hideEvent(self, event):
        """Stop the update timer while hidden."""
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        """Resume updates when shown with a secret set."""
        if self._secret:
            self._timer.start()
        super().showEvent(event)
