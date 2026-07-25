# Created: 2026-07-24
# Last Edited: 2026-07-25 18:12 CT (America/Chicago)
# Path: src/main.py
# Purpose: Application entry point — initializes QApplication and launches AetherVault main window.

"""Application entry point that initializes QApplication and launches the AetherVault main window."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.gui.app import PySidePWManager


def run():
    """Create and run the QApplication, display the main window, and exit on close."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PySidePWManager()
    window.show()
    QTimer.singleShot(500, window.check_setup_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
