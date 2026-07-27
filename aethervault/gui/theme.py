# Created: 2026-07-24
# Last Edited: 2026-07-27 16:51 CT (America/Chicago)
# Path: aethervault/gui/theme.py
# Purpose: Unified theme system for AetherVault — dark/light palettes and QSS.

"""Unified theme system with dark/light color palettes and QSS stylesheets."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeColors:
    """Light theme color constants for the application palette."""

    BG_PRIMARY = "#f8f9fa"
    BG_SECONDARY = "#ffffff"
    BG_TERTIARY = "#f1f2f6"
    BG_ALTERNATE = "#f5f5f5"

    TEXT_PRIMARY = "#2f3542"
    TEXT_SECONDARY = "#636e72"
    TEXT_INVERSE = "#ffffff"

    ACCENT_BLUE = "#54a0ff"
    ACCENT_GREEN = "#00d2d3"
    ACCENT_ORANGE = "#ff9f43"
    ACCENT_RED = "#ff6b6b"

    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#ff5555"

    BORDER_LIGHT = "#ced6e0"
    BORDER_MEDIUM = "#a4b0be"
    BORDER_DARK = "#747d8c"


class DarkThemeColors:
    """Dark theme color constants for the application palette."""

    BG_PRIMARY = "#1a1a2e"
    BG_SECONDARY = "#2d2d44"
    BG_TERTIARY = "#3d3d5c"
    BG_ALTERNATE = "#35354a"

    TEXT_PRIMARY = "#e8e8e8"
    TEXT_SECONDARY = "#b0b0c0"
    TEXT_INVERSE = "#ffffff"

    ACCENT_BLUE = "#54a0ff"
    ACCENT_GREEN = "#00d2d3"
    ACCENT_ORANGE = "#ff9f43"
    ACCENT_RED = "#ff6b6b"

    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#ff5555"

    BORDER_LIGHT = "#555577"
    BORDER_MEDIUM = "#666688"
    BORDER_DARK = "#777799"


LIGHT_STYLE = """
QWidget {
    background-color: #f8f9fa;
    color: #2f3542;
    font-family: "Segoe UI";
    font-size: 11pt;
}
QMainWindow, QDialog {
    background-color: #f8f9fa;
}
QFrame {
    background-color: #ffffff;
    border: 1px solid #ced6e0;
    border-radius: 5px;
    padding: 8px;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #ced6e0;
    border-radius: 3px;
    padding: 4px 12px;
    font-size: 11pt;
}
QPushButton:hover {
    background-color: #f5f5f5;
    border-color: #a4b0be;
}
QPushButton:pressed {
    background-color: #ced6e0;
}
QPushButton:disabled {
    color: #a4b0be;
}
QLineEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #ced6e0;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #54a0ff;
    selection-color: #ffffff;
}
QLineEdit {
    min-height: 30px;
    max-height: 30px;
}
QComboBox {
    min-height: 30px;
    max-height: 30px;
    padding: 2px 4px;
    border: 1px solid #ced6e0;
    border-radius: 3px;
    background-color: #ffffff;
}
QComboBox:focus {
    border-color: #54a0ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QTextEdit {
    min-height: 60px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #54a0ff;
}
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f5f5f5;
    border: 1px solid #ced6e0;
    border-radius: 3px;
    gridline-color: #ced6e0;
}
QTableWidget::item {
    padding: 2px 4px;
}
QTableWidget::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QProgressBar {
    background-color: #e0e0e0;
    border: 1px solid #ced6e0;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #f1f2f6;
    padding: 4px 6px;
    border: none;
    border-right: 1px solid #ced6e0;
    border-bottom: 1px solid #ced6e0;
    font-weight: 600;
    font-size: 11pt;
}
QLabel {
    color: #2f3542;
}
QStatusBar {
    background-color: #f1f2f6;
    color: #636e72;
    padding: 4px;
    font-size: 10pt;
}
QMenuBar {
    background-color: #ffffff;
    color: #2f3542;
    padding: 4px;
}
QMenuBar::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #ced6e0;
}
QMenu::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QSplitter::handle {
    background-color: #ced6e0;
}
"""

DARK_STYLE = """
QWidget {
    background-color: #1a1a2e;
    color: #e8e8e8;
    font-family: "Segoe UI";
    font-size: 11pt;
}
QMainWindow, QDialog {
    background-color: #1a1a2e;
}
QFrame {
    background-color: #2d2d44;
    border: 1px solid #555577;
    border-radius: 5px;
    padding: 8px;
}
QPushButton {
    background-color: #2d2d44;
    border: 1px solid #555577;
    border-radius: 3px;
    padding: 4px 12px;
    font-size: 11pt;
    color: #e8e8e8;
}
QPushButton:hover {
    background-color: #35354a;
    border-color: #666688;
}
QPushButton:pressed {
    background-color: #555577;
}
QPushButton:disabled {
    color: #666688;
}
QLineEdit, QTextEdit {
    background-color: #2d2d44;
    border: 1px solid #555577;
    border-radius: 3px;
    padding: 2px 4px;
    color: #e8e8e8;
    selection-background-color: #54a0ff;
    selection-color: #ffffff;
}
QLineEdit {
    min-height: 30px;
    max-height: 30px;
}
QComboBox {
    min-height: 30px;
    max-height: 30px;
    padding: 2px 4px;
    border: 1px solid #555577;
    border-radius: 3px;
    background-color: #2d2d44;
    color: #e8e8e8;
}
QComboBox:focus {
    border-color: #54a0ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d44;
    color: #e8e8e8;
    selection-background-color: #54a0ff;
}
QTextEdit {
    min-height: 60px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #54a0ff;
}
QTableWidget {
    background-color: #2d2d44;
    alternate-background-color: #35354a;
    border: 1px solid #555577;
    border-radius: 3px;
    gridline-color: #555577;
    color: #e8e8e8;
}
QTableWidget::item {
    padding: 2px 4px;
    color: #e8e8e8;
}
QTableWidget::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QProgressBar {
    background-color: #3d3d5c;
    border: 1px solid #555577;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #3d3d5c;
    padding: 4px 6px;
    border: none;
    border-right: 1px solid #555577;
    border-bottom: 1px solid #555577;
    font-weight: 600;
    color: #e8e8e8;
    font-size: 11pt;
}
QLabel {
    color: #e8e8e8;
}
QStatusBar {
    background-color: #3d3d5c;
    color: #b0b0c0;
    padding: 4px;
    font-size: 10pt;
}
QMenuBar {
    background-color: #2d2d44;
    color: #e8e8e8;
    padding: 4px;
}
QMenuBar::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QMenu {
    background-color: #2d2d44;
    border: 1px solid #555577;
}
QMenu::item:selected {
    background-color: #54a0ff;
    color: #ffffff;
}
QSplitter::handle {
    background-color: #555577;
}
"""


def apply_theme(app: QApplication, theme_name: str = "light") -> None:
    """Apply the named theme (light or dark) stylesheet and palette to the application."""
    if theme_name == "dark":
        app.setStyleSheet(DARK_STYLE)
        _apply_dark_palette(app)
    else:
        app.setStyleSheet(LIGHT_STYLE)
        _apply_light_palette(app)


def _apply_light_palette(app: QApplication) -> None:
    """Set the application palette to light-mode colors."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(ThemeColors.BG_PRIMARY))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(ThemeColors.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ThemeColors.BG_ALTERNATE))
    palette.setColor(QPalette.ColorRole.Text, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(ThemeColors.BG_TERTIARY))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.ACCENT_BLUE))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_INVERSE))
    app.setPalette(palette)


def _apply_dark_palette(app: QApplication) -> None:
    """Set the application palette to dark-mode colors."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(DarkThemeColors.BG_PRIMARY))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(DarkThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(DarkThemeColors.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(DarkThemeColors.BG_ALTERNATE))
    palette.setColor(QPalette.ColorRole.Text, QColor(DarkThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(DarkThemeColors.BG_TERTIARY))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(DarkThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.ACCENT_BLUE))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_INVERSE))
    app.setPalette(palette)
