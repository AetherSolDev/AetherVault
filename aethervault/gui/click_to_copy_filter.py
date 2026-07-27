# Created: 2026-07-27
# Last Edited: 2026-07-27 16:51 CT (America/Chicago)
# Path: aethervault/gui/click_to_copy_filter.py
# Purpose: Event filter that copies widget text to clipboard on left-click.

"""Event filter that copies widget text to clipboard on left-click."""

from PySide6.QtCore import QEvent, QObject, Qt


class ClickToCopyFilter(QObject):
    """Event filter that copies widget text to clipboard on left-click."""

    def __init__(self, parent, field_name: str, callback):
        super().__init__(parent)
        self._field_name = field_name
        self._callback = callback

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            text = obj.text() if hasattr(obj, "text") else ""
            if text:
                self._callback(text, self._field_name)
        return super().eventFilter(obj, event)
