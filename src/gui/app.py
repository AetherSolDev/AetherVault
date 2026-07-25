# Created: 2025-12-04
# Last Edited: 2026-07-25 18:12 CT (America/Chicago)
# Path: src/gui/app.py
# Purpose: Main application window and UI logic for AetherVault.

"""Main application window and UI logic for AetherVault."""

import json
import os
import re
import shutil
from typing import List, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence,
    QPainter, QPixmap, QShortcut,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src import (
    PORTABLE_MARKER,
    VERSION,
    disable_portable_mode,
    enable_portable_mode,
    is_portable,
)
from src.core_logic import (
    DB_BACKUP_PATH,
    DB_PATH,
    DEFAULT_LOCKOUT_MINUTES,
    MASTER_KEY_FILE,
    CredentialEntry,
    generate_strong_password,
    get_timestamped_backup_path,
    load_master_password,
    load_settings,
    save_settings,
    store_master_password,
    verify_password,
)
from src.gui.theme import DarkThemeColors, ThemeColors
from src.db_manager import DatabaseManager
from src.gui.dialogs import DocumentationDialog, PasswordGeneratorDialog, resource_path
from src.gui.theme import apply_theme as apply_app_theme

LOCKOUT_OPTIONS = [1, 3, 5, 10, 30]
LOCKOUT_NEVER = 0
AUTO_CLEAR_DELAY = 30000


class ClickToCopyFilter(QObject):
    """Event filter that copies widget text to clipboard on left-click."""

    def __init__(self, parent, field_name: str, callback):
        """Initialize the filter with a field name and copy callback."""
        super().__init__(parent)
        self._field_name = field_name
        self._callback = callback

    def eventFilter(self, obj, event):
        """Intercept left-clicks and copy the widget's text to clipboard."""
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            text = obj.text() if hasattr(obj, "text") else ""
            if text:
                self._callback(text, self._field_name)
        return super().eventFilter(obj, event)


class PasswordStrengthBar(QProgressBar):
    """Progress bar that evaluates and displays password strength."""

    def __init__(self, parent=None):
        """Initialize the strength bar with range 0-100 and hide by default."""
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(True)
        self.setFixedHeight(15)
        self.hide()

    def evaluate(self, password: str):
        """Score a password and update the bar with a color-coded strength level."""
        if not password:
            self.hide()
            return
        self.show()
        score = 0
        if len(password) >= 8:
            score += 15
        if len(password) >= 12:
            score += 15
        if len(password) >= 16:
            score += 10
        if re.search(r"[a-z]", password):
            score += 10
        if re.search(r"[A-Z]", password):
            score += 15
        if re.search(r"\d", password):
            score += 15
        if re.search(r"[^a-zA-Z0-9]", password):
            score += 20
        score = min(score, 100)
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


class PySidePWManager(QMainWindow):
    """Main application window handling authentication, credential management, and UI."""

    def __init__(self):
        """Initialize the main window, load settings, and build the UI."""
        super().__init__()
        self.setWindowTitle("AetherVault")
        self.resize(1100, 700)
        self.setMinimumSize(750, 500)

        icon_path = resource_path(os.path.join("assets", "aethervault.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.is_authenticated = False
        self.is_editing = False
        self.master_password_hash = load_master_password(MASTER_KEY_FILE)
        self.current_entry_id: Optional[int] = None
        self.previous_entry_id: Optional[int] = None
        self.is_form_modified = False
        self.credentials: List[CredentialEntry] = []
        self.settings = load_settings()
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder
        self._favicon_cache: dict = {}
        self._network_manager = QNetworkAccessManager()

        self._apply_theme()

        self.clipboard_clear_time = 15000
        self.clipboard_clear_timer = QTimer(self)
        self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)

        self.form_clear_timer = QTimer(self)
        self.form_clear_timer.setSingleShot(True)
        self.form_clear_timer.timeout.connect(self.clear_form)

        self.last_copied_field: Optional[str] = None

        error_handler = lambda title, msg: QMessageBox.critical(self, title, msg)
        self.db_manager = DatabaseManager(DB_PATH, error_handler)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_auth_ui()
        self.create_main_content()
        self.setup_menu_bar()
        self.setup_shortcuts()

        self.installEventFilter(self)

        sb = QStatusBar(self)
        sb.setFixedHeight(22)
        self.setStatusBar(sb)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Awaiting input...")

        self._setup_system_tray()

    # --- Clipboard ---

    def clear_clipboard(self):
        """Clear the system clipboard and stop the clear timer."""
        QApplication.clipboard().setText("")
        self.clipboard_clear_timer.stop()
        self.status_bar.showMessage("Clipboard cleared.", 3000)

    def copy_to_clipboard(self, text: str, field_name: str = ""):
        """Copy text to clipboard and start the auto-clear timer."""
        if not self.is_authenticated:
            self.status_bar.showMessage("Authentication required to copy.", 3000)
            return
        QApplication.clipboard().setText(text)
        self.clipboard_clear_timer.stop()
        self.clipboard_clear_timer.start(self.clipboard_clear_time)
        self.last_copied_field = field_name
        label = field_name.capitalize() if field_name else "Value"
        self.status_bar.showMessage(
            f"{label} copied. Will clear in 15s.", 3000
        )
        QTimer.singleShot(30000, self._auto_clear_form_check)

    def _auto_clear_form_check(self):
        """Auto-clear the form if a password was copied and no edit is in progress."""
        if self.last_copied_field == "password" and not self.is_editing:
            self.clear_form()
            self.status_bar.showMessage("Password copied — form auto-cleared.", 3000)

    # --- Password Generator ---

    def show_password_generator(self):
        """Open the password generator dialog and insert the result."""
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec() == QDialog.Accepted:
            pw = dlg.get_password()
            if pw:
                self.password_entry_ref.setText(pw)
                self.form_modified()
                self.status_bar.showMessage("Password generated and inserted.", 3000)

    # --- Auth ---

    def check_setup_state(self):
        """Show setup or login screen depending on whether a master password exists."""
        if not self.master_password_hash:
            self.show_auth_screen(setup_mode=True)
            self.status_bar.showMessage(
                "Welcome! Please set a strong Master Password.", 5000
            )
        else:
            self.show_auth_screen(setup_mode=False)

    def create_auth_ui(self):
        """Build the authentication screen with password entry and action button."""
        self.auth_frame = QFrame()
        auth_layout = QVBoxLayout(self.auth_frame)
        self.auth_title = QLabel("Password Vault")
        self.auth_title.setFont(QFont("Arial", 24))
        self.auth_title.setAlignment(Qt.AlignCenter)
        auth_layout.addWidget(self.auth_title)
        auth_layout.addStretch(1)
        block = QWidget()
        block.setFixedWidth(350)
        bl = QVBoxLayout(block)
        bl.setContentsMargins(0, 0, 0, 0)
        self.master_pass_entry = QLineEdit()
        self.master_pass_entry.setEchoMode(QLineEdit.Password)
        self.master_pass_entry.returnPressed.connect(self.action_btn_clicked)
        bl.addWidget(self.master_pass_entry)
        self.action_btn = QPushButton("Login")
        self.action_btn.clicked.connect(self.action_btn_clicked)
        bl.addWidget(self.action_btn)
        auth_layout.addWidget(block, alignment=Qt.AlignCenter)
        auth_layout.addStretch(1)
        self.auth_index = self.stacked_widget.addWidget(self.auth_frame)

    def action_btn_clicked(self):
        """Route the auth button click to set password or login."""
        if self.action_btn.text() == "Set Master Password":
            self.set_master_password()
        else:
            self.attempt_login()

    def show_auth_screen(self, setup_mode=False):
        """Switch to the authentication screen in setup or login mode."""
        self.stacked_widget.setCurrentIndex(self.auth_index)
        if setup_mode:
            self.auth_title.setText("Setup Master Password")
            self.action_btn.setText("Set Master Password")
            self.master_pass_entry.setPlaceholderText("Enter new master password")
        else:
            self.auth_title.setText("Master Password")
            self.action_btn.setText("Login")
            self.master_pass_entry.setPlaceholderText("Enter Master Password")
        self.master_pass_entry.clear()
        self.master_pass_entry.setFocus()
        self.is_authenticated = False
        self.credentials = []
        self._update_tray_lock_action()

    def set_master_password(self):
        """Validate and store a new master password."""
        pw = self.master_pass_entry.text()
        if len(pw) < 8:
            QMessageBox.warning(
                self, "Password Too Short",
                "Master password must be at least 8 characters.",
            )
            return
        if store_master_password(pw):
            self.master_password_hash = load_master_password(MASTER_KEY_FILE)
            QMessageBox.information(
                self, "Success", "Master password set successfully. Please log in."
            )
            self.show_auth_screen(setup_mode=False)
        else:
            QMessageBox.critical(self, "Error", "Failed to save master password file.")

    def attempt_login(self):
        """Verify master password and unlock the vault."""
        pw = self.master_pass_entry.text()
        if not pw:
            self.status_bar.showMessage("Please enter a password.", 3000)
            return
        stored = self.master_password_hash
        if verify_password(pw, stored):
            self.is_authenticated = True
            self._update_tray_lock_action()
            self.db_manager.set_encryption_key(stored)
            self.status_bar.showMessage("Authentication successful.", 5000)
            self.show_main_app()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid master password.")
            self.status_bar.showMessage("Login failed.", 3000)

    def show_main_app(self):
        """Switch to the main credential management view after successful login."""
        self.stacked_widget.setCurrentIndex(self.main_index)
        self.credentials = self.db_manager.load_all_credentials()
        self.update_list_view()
        mode = " [Portable]" if is_portable() else ""
        self.status_bar.showMessage(f"Vault unlocked.{mode}", 5000)
        self.search_entry.setFocus()
        self.reset_activity_timer()

    # --- Password Visibility ---

    def _toggle_password_visibility_button(self, checked):
        """Toggle the password field between masked and visible text."""
        if checked:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pass_btn.setText("\U0001f441")
        else:
            self.password_entry_ref.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setText("\U0001f441")

    # --- Theme ---

    def show_documentation(self):
        """Open the user guide documentation in the system browser."""
        path = resource_path(os.path.join("docs", "USER_GUIDE.html"))
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Help Not Found",
                                "Documentation file not found at:\n" + path)

    def _apply_theme(self):
        """Apply the current theme (light/dark) to the application instance."""
        app = QApplication.instance()
        if app:
            apply_app_theme(app, self.settings.get("theme", "light"))

    def toggle_theme(self):
        """Switch between light and dark themes and persist the choice."""
        current = self.settings.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        self._apply_theme()
        self.theme_action.setText(
            f"Switch to {'Light' if new_theme == 'dark' else 'Dark'} Theme"
        )
        self.status_bar.showMessage(f"Switched to {new_theme} mode.", 3000)

    # --- View / Edit Mode ---

    def enter_view_mode(self):
        """Switch the form to read-only view mode."""
        self.is_editing = False
        self._set_form_readonly(True)
        self.gen_pass_btn.hide()
        self.save_btn.hide()
        self.cancel_btn.hide()
        self.edit_btn.show()
        self.add_btn.show()
        self.delete_btn.show()
        if self.current_entry_id:
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        self.strength_bar.hide()

    def enter_edit_mode(self):
        """Switch the form to editable mode for the current entry."""
        if self.current_entry_id is None:
            return
        self.is_editing = True
        self._set_form_readonly(False)
        self.gen_pass_btn.show()
        self.save_btn.show()
        self.cancel_btn.show()
        self.edit_btn.hide()
        self.add_btn.hide()
        self.delete_btn.hide()
        self.save_btn.setEnabled(False)
        self.is_form_modified = False
        self.password_entry_ref.setFocus()

    def enter_new_mode(self):
        """Clear the form and switch to new-entry creation mode."""
        self.is_editing = True
        self.previous_entry_id = self.current_entry_id
        self._clear_fields()
        self.current_entry_id = None
        self._set_form_readonly(False)
        self.gen_pass_btn.show()
        self.save_btn.show()
        self.cancel_btn.show()
        self.edit_btn.hide()
        self.add_btn.hide()
        self.delete_btn.hide()
        self.save_btn.setEnabled(False)
        self.is_form_modified = False
        self.input_fields["title"].setFocus()
        self.credential_table.clearSelection()

    def cancel_edit(self):
        """Discard changes and return to view mode, restoring the previous entry."""
        if self.current_entry_id:
            entry = next(
                (c for c in self.credentials if c.db_id == self.current_entry_id), None
            )
            if entry:
                self.fill_form(entry)
                self.enter_view_mode()
                return
        if self.previous_entry_id:
            self.current_entry_id = self.previous_entry_id
            entry = next(
                (c for c in self.credentials if c.db_id == self.previous_entry_id), None
            )
            if entry:
                self.fill_form(entry)
                self.credential_table.selectionModel().clear()
                self._select_entry_in_table(self.previous_entry_id)
        self.enter_view_mode()

    def _add_custom_field_row(self):
        """Add a blank row to the custom fields table."""
        r = self.custom_fields_table.rowCount()
        self.custom_fields_table.insertRow(r)
        self.custom_fields_table.setItem(r, 0, QTableWidgetItem(""))
        self.custom_fields_table.setItem(r, 1, QTableWidgetItem(""))
        self.form_modified()

    def _remove_custom_field_row(self):
        """Remove the selected row from the custom fields table."""
        r = self.custom_fields_table.currentRow()
        if r >= 0:
            self.custom_fields_table.removeRow(r)
            self.form_modified()

    def _set_form_readonly(self, ro: bool):
        """Set all form input fields to read-only or editable."""
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

    def _clear_fields(self):
        """Clear all form fields and reset the custom fields table."""
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

    def _select_entry_in_table(self, db_id: int):
        """Select the table row corresponding to the given database ID."""
        for row in range(self.credential_table.rowCount()):
            item = self.credential_table.item(row, 4)
            if item and item.text() == str(db_id):
                self.credential_table.selectRow(row)
                break

    # --- Main Content ---

    def create_main_content(self):
        """Build the main splitter layout with credential list and detail form."""
        self.main_content_splitter = QSplitter(Qt.Horizontal)
        self.main_content_splitter.setHandleWidth(6)

        # --- Left: List ---
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)

        sl = QHBoxLayout()
        sl.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Filter by title, username, or URL...")
        self.search_entry.textChanged.connect(self.update_list_view)
        sl.addWidget(self.search_entry)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentIndexChanged.connect(self.update_list_view)
        sl.addWidget(self.category_filter)
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All Tags")
        self.tag_filter.currentIndexChanged.connect(self.update_list_view)
        sl.addWidget(self.tag_filter)
        list_layout.addLayout(sl)

        self.credential_table = QTableWidget()
        self.credential_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.credential_table.setSelectionMode(QTableWidget.SingleSelection)
        self.credential_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.credential_table.itemSelectionChanged.connect(self.display_selected_entry)
        self.credential_table.cellDoubleClicked.connect(self._table_cell_double_clicked)
        self.credential_table.cellClicked.connect(self._table_cell_clicked)
        self.credential_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.credential_table.customContextMenuRequested.connect(self._table_context_menu)
        self.credential_table.horizontalHeader().sectionClicked.connect(self._handle_sort)
        list_layout.addWidget(self.credential_table)

        lbl = QHBoxLayout()
        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self.enter_new_mode)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.enter_edit_mode)
        self.edit_btn.setEnabled(False)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_credential)
        self.delete_btn.setEnabled(False)
        lbl.addWidget(self.add_btn)
        lbl.addWidget(self.edit_btn)
        lbl.addWidget(self.delete_btn)
        list_layout.addLayout(lbl)
        self.main_content_splitter.addWidget(list_panel)

        # --- Right: Form ---
        form_panel = QWidget()
        form_layout = QVBoxLayout(form_panel)
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
                ClickToCopyFilter(self, key, self.copy_to_clipboard)
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
                self.toggle_pass_btn.clicked.connect(
                    self._toggle_password_visibility_button
                )
                pl.addWidget(self.toggle_pass_btn)
                form_grid.addWidget(pc, row, 1)

                self.strength_bar = PasswordStrengthBar()
                form_grid.addWidget(self.strength_bar, row + 1, 1, 1, 2)
                line_edit.textChanged.connect(self._on_password_text_changed)
                self.strength_bar.hide()

                al = QHBoxLayout()
                al.setContentsMargins(0, 0, 0, 0)
                self.gen_pass_btn = QPushButton("Generate")
                self.gen_pass_btn.setToolTip("Open secure password generator")
                self.gen_pass_btn.clicked.connect(self.show_password_generator)
                al.addWidget(self.gen_pass_btn)
                copy_pass_btn = QPushButton("Copy")
                copy_pass_btn.setToolTip("Copy password to clipboard")
                copy_pass_btn.clicked.connect(
                    lambda checked, le=line_edit: self.copy_to_clipboard(
                        le.text(), "password"
                    )
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
                            self.copy_to_clipboard(le.text(), n)
                    )
                    form_grid.addWidget(copy_btn, row, 2)
            if key != "password":
                line_edit.textChanged.connect(self.form_modified)
            row += 1

        tags_row = row
        form_grid.addWidget(QLabel("Tags:"), tags_row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        self.tags_entry = QLineEdit()
        self.tags_entry.setPlaceholderText("tag1, tag2, tag3")
        self.tags_entry.textChanged.connect(self.form_modified)
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
        self.notes_entry.textChanged.connect(self.form_modified)
        self.notes_entry.installEventFilter(
            ClickToCopyFilter(self, "notes", self.copy_to_clipboard)
        )
        notes_container_layout.addWidget(self.notes_entry)
        form_grid.addWidget(notes_container, notes_row, 1, 1, 2)

        form_grid.setColumnMinimumWidth(0, 90)
        form_grid.setColumnStretch(1, 1)
        form_grid.setVerticalSpacing(4)

        form_layout.addLayout(form_grid, stretch=2)

        # --- Custom Fields ---
        cf_label = QLabel("Custom Fields:")
        form_layout.addWidget(cf_label)
        self.custom_fields_table = QTableWidget()
        self.custom_fields_table.setColumnCount(2)
        self.custom_fields_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.custom_fields_table.horizontalHeader().setStretchLastSection(True)
        self.custom_fields_table.horizontalHeader().setFixedHeight(50)
        self.custom_fields_table.verticalHeader().hide()
        self.custom_fields_table.setMinimumHeight(80)
        form_layout.addWidget(self.custom_fields_table, stretch=1)
        cf_buttons = QHBoxLayout()
        self.cf_add_btn = QPushButton("+ Add Field")
        self.cf_add_btn.clicked.connect(self._add_custom_field_row)
        self.cf_remove_btn = QPushButton("- Remove Selected")
        self.cf_remove_btn.clicked.connect(self._remove_custom_field_row)
        cf_buttons.addWidget(self.cf_add_btn)
        cf_buttons.addWidget(self.cf_remove_btn)
        cf_buttons.addStretch()
        form_layout.addLayout(cf_buttons)

        fbl = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_credential)
        self.save_btn.hide()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        self.cancel_btn.hide()
        fbl.addWidget(self.save_btn)
        fbl.addWidget(self.cancel_btn)
        fbl.addStretch()
        form_layout.addLayout(fbl)

        form_panel.setLayout(form_layout)
        list_panel.setMinimumWidth(300)
        form_panel.setMinimumWidth(400)
        form_panel.setMaximumWidth(700)
        self.main_content_splitter.addWidget(list_panel)
        self.main_content_splitter.addWidget(form_panel)
        self.main_content_splitter.setSizes([500, 500])
        self.main_content_splitter.setStretchFactor(0, 1)
        self.main_content_splitter.setStretchFactor(1, 1)
        self.main_index = self.stacked_widget.addWidget(self.main_content_splitter)

        self.gen_pass_btn.hide()
        self._set_form_readonly(True)

    def _on_password_text_changed(self, text):
        """Evaluate password strength and mark the form as modified."""
        if self.is_editing:
            self.strength_bar.evaluate(text)
            self.form_modified()

    # --- Table & Selection ---

    def _populate_category_filter(self):
        """Refresh the category filter dropdown from current credentials."""
        current = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        categories = sorted(
            {c.category for c in self.credentials if c.category}
        )
        self.category_filter.addItems(categories)
        idx = self.category_filter.findText(current)
        if idx >= 0:
            self.category_filter.setCurrentIndex(idx)
        self.category_filter.blockSignals(False)

    def _populate_tag_filter(self):
        """Refresh the tag filter dropdown from current credentials."""
        current = self.tag_filter.currentText()
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem("All Tags")
        tags = sorted({
            t.strip()
            for c in self.credentials
            if c.tags
            for t in c.tags.split(",")
            if t.strip()
        })
        self.tag_filter.addItems(tags)
        idx = self.tag_filter.findText(current)
        if idx >= 0:
            self.tag_filter.setCurrentIndex(idx)
        self.tag_filter.blockSignals(False)

    def update_list_view(self):
        """Filter credentials by search, category, and tag, then refresh the table."""
        if not self.is_authenticated:
            return
        search = self.search_entry.text().lower()
        selected_cat = self.category_filter.currentText()
        selected_tag = self.tag_filter.currentText()
        filtered = [
            c for c in self.credentials
            if (selected_cat == "All Categories" or c.category == selected_cat)
            and (selected_tag == "All Tags" or (c.tags and selected_tag in [t.strip() for t in c.tags.split(",")]))
            and (
                not search
                or search in c.title.lower()
                or search in c.username.lower()
                or search in c.url.lower()
                or search in (c.notes or "").lower()
                or search in (c.category or "").lower()
                or search in (c.tags or "").lower()
            )
        ]
        headers = ["Title", "Username", "URL", "Category", "ID"]
        self.credential_table.setColumnCount(len(headers))
        self.credential_table.setHorizontalHeaderLabels(headers)
        self.credential_table.setColumnHidden(4, True)
        self.credential_table.setRowCount(len(filtered))

        theme_colors = DarkThemeColors if self.settings.get("theme", "light") == "dark" else ThemeColors
        highlight = QColor(theme_colors.BG_TERTIARY)

        for ri, entry in enumerate(filtered):
            for ci, val in [
                (0, entry.title), (1, entry.username),
                (2, entry.url), (3, entry.category),
                (4, str(entry.db_id)),
            ]:
                item = QTableWidgetItem(val)
                if search and search in val.lower():
                    item.setBackground(highlight)
                if ci == 0 and entry.url:
                    try:
                        domain = QUrl(entry.url).host()
                        if domain and domain in self._favicon_cache:
                            item.setIcon(self._favicon_cache[domain])
                    except Exception:
                        pass
                self.credential_table.setItem(ri, ci, item)

        h = self.credential_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Interactive)
        h.setSectionResizeMode(1, QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Interactive)
        h.resizeSection(0, 220)
        h.resizeSection(1, 160)
        h.resizeSection(3, 140)
        h.setMinimumSectionSize(100)
        self.credential_table.verticalHeader().setDefaultSectionSize(32)
        self.credential_table.verticalHeader().hide()
        self.credential_table.horizontalHeader().setFixedHeight(50)
        self._populate_category_filter()
        self._populate_tag_filter()

    def _handle_sort(self, column: int):
        """Sort the credential table by the clicked column, toggling order on re-click."""
        if column == 4:
            return
        if self.sort_column == column:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.AscendingOrder
        self.credential_table.sortItems(column, self.sort_order)

    def _table_cell_double_clicked(self, row: int, col: int):
        """Copy the double-clicked cell's text to clipboard."""
        if not self.is_authenticated:
            return
        if col == 4:
            return
        item = self.credential_table.item(row, col)
        if not item or not item.text():
            return
        labels = {0: "title", 1: "username", 2: "url", 3: "category"}
        label = labels.get(col, "value")
        self.copy_to_clipboard(item.text(), label)

    def _table_cell_clicked(self, row: int, col: int):
        """Filter by category when a category cell is clicked."""
        if not self.is_authenticated:
            return
        if col != 3:
            return
        item = self.credential_table.item(row, col)
        if not item or not item.text():
            return
        idx = self.category_filter.findText(item.text())
        if idx >= 0:
            self.category_filter.setCurrentIndex(idx)

    def _table_context_menu(self, pos):
        """Show a right-click context menu for the credential table."""
        if not self.is_authenticated:
            return
        item = self.credential_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        entry_id_item = self.credential_table.item(row, 4)
        if not entry_id_item:
            return
        title_item = self.credential_table.item(row, 0)
        username_item = self.credential_table.item(row, 1)
        menu = QMenu(self)
        if username_item and username_item.text():
            a = menu.addAction("Copy Username")
            a.triggered.connect(lambda: self.copy_to_clipboard(username_item.text(), "username"))
        a = menu.addAction("Copy Password")
        a.triggered.connect(self._context_copy_password)
        menu.addSeparator()
        a = menu.addAction("Edit Entry")
        a.triggered.connect(self._context_edit)
        a = menu.addAction("Delete Entry")
        a.triggered.connect(self._context_delete)
        menu.exec(self.credential_table.viewport().mapToGlobal(pos))

    def _context_copy_password(self):
        """Copy the password of the currently right-clicked row."""
        entry_id_item = self.credential_table.item(self.credential_table.currentRow(), 4)
        if not entry_id_item:
            return
        try:
            db_id = int(entry_id_item.text())
        except ValueError:
            return
        entry = next((c for c in self.credentials if c.db_id == db_id), None)
        if entry and entry.password:
            self.copy_to_clipboard(entry.password, "password")

    def _context_edit(self):
        """Enter edit mode from the context menu."""
        if self.current_entry_id:
            self.enter_edit_mode()

    def _context_delete(self):
        """Delete the current entry from the context menu."""
        self.delete_credential()

    def _fetch_favicons(self):
        """Fetch favicons for all credential URLs via Google's favicon service."""
        if not self.is_authenticated:
            return QMessageBox.warning(self, "Denied", "Login first.")
        if not self.credentials:
            return
        domains = set()
        for c in self.credentials:
            if c.url:
                try:
                    domain = QUrl(c.url).host()
                    if domain:
                        domains.add(domain)
                except Exception:
                    pass
        if not domains:
            self.status_bar.showMessage("No URLs with domains to fetch.", 3000)
            return
        self.status_bar.showMessage(f"Fetching favicons for {len(domains)} domains...", 5000)
        for domain in domains:
            if domain in self._favicon_cache:
                continue
            url = QUrl(f"https://www.google.com/s2/favicons?domain={domain}&sz=16")
            req = QNetworkRequest(url)
            reply = self._network_manager.get(req)
            reply.finished.connect(lambda r=reply, d=domain: self._on_favicon_fetched(r, d))

    def _on_favicon_fetched(self, reply, domain: str):
        """Cache the downloaded favicon and refresh the table."""
        data = reply.readAll()
        reply.deleteLater()
        if data and len(data) > 0:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self._favicon_cache[domain] = QIcon(pixmap)
                self.update_list_view()

    def display_selected_entry(self):
        """Populate the form with the credential selected in the table."""
        if self.is_editing:
            return
        rows = self.credential_table.selectionModel().selectedRows()
        if not rows:
            self.delete_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.current_entry_id = None
            self._clear_fields()
            return
        item = self.credential_table.item(rows[0].row(), 4)
        if item is None:
            return
        try:
            db_id = int(item.text())
        except ValueError:
            return
        entry = next((c for c in self.credentials if c.db_id == db_id), None)
        if entry:
            self.current_entry_id = db_id
            self.delete_btn.setEnabled(True)
            self.edit_btn.setEnabled(True)
            self.fill_form(entry)

    def _custom_fields_from_entry(self, raw: str):
        """Parse JSON custom fields and populate the custom fields table."""
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
        """Serialize the custom fields table contents to a JSON string."""
        pairs = []
        for r in range(self.custom_fields_table.rowCount()):
            f = self.custom_fields_table.item(r, 0)
            v = self.custom_fields_table.item(r, 1)
            pairs.append({
                "field": f.text() if f else "",
                "value": v.text() if v else "",
            })
        return json.dumps(pairs)

    def fill_form(self, entry: CredentialEntry):
        """Populate all form fields with data from a CredentialEntry."""
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
        self.enter_view_mode()

    def clear_form(self):
        """Clear the form fields and deselect the current entry."""
        self._clear_fields()
        self.current_entry_id = None
        self.is_form_modified = False
        self.credential_table.clearSelection()
        self.enter_view_mode()

    def form_modified(self):
        """Mark the form as modified and enable the Save button."""
        if self.is_editing:
            self.is_form_modified = True
            self.save_btn.setEnabled(True)

    # --- Save / Delete ---

    def save_credential(self):
        """Validate and save the current credential entry to the database."""
        title = self.input_fields["title"].text().strip()
        password = self.input_fields["password"].text().strip()
        if not title or not password:
            QMessageBox.warning(
                self, "Missing Data",
                "Both 'Title' and 'Password' fields are required.",
            )
            return
        data = {k: e.text() for k, e in self.input_fields.items()}
        data["notes"] = self.notes_entry.toHtml()
        data["custom_fields"] = self._custom_fields_to_json()
        data["db_id"] = self.current_entry_id
        entry = CredentialEntry(**data)
        if self.current_entry_id:
            self.db_manager.update_credential(entry)
            msg = f"Entry '{title}' updated."
        else:
            new_id = self.db_manager.save_credential(entry)
            if new_id is None:
                return
            entry.db_id = new_id
            msg = f"New entry '{title}' saved."
        self._auto_backup_db(reason="Credential Save")
        self.credentials = self.db_manager.load_all_credentials()
        self.update_list_view()
        self.fill_form(entry)
        self.enter_view_mode()
        self._select_entry_in_table(entry.db_id)
        self.status_bar.showMessage(msg, 5000)

    def delete_credential(self):
        """Prompt for confirmation and delete the current credential entry."""
        if self.current_entry_id is None:
            return
        title = self.input_fields["title"].text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Permanently delete '{title}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db_manager.delete_credential(self.current_entry_id)
            self.credentials = [
                c for c in self.credentials if c.db_id != self.current_entry_id
            ]
            self._clear_fields()
            self.update_list_view()
            self.enter_view_mode()
            self.status_bar.showMessage(f"Entry '{title}' deleted.", 5000)

    # --- Import / Export / Backup ---

    def handle_export(self):
        """Export all credentials to a CSV file selected by the user."""
        if not self.credentials:
            QMessageBox.warning(self, "Export Failed", "No credentials to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Credentials", os.path.expanduser("~") + "/vault_export.csv",
            "CSV Files (*.csv)",
        )
        if path:
            try:
                n = self.db_manager.export_to_csv(path, self.credentials)
                QMessageBox.information(
                    self, "Exported", f"Exported {n} credentials to:\n{path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))

    def handle_import(self):
        """Import credentials from a CSV file selected by the user."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Credentials", os.path.expanduser("~"), "CSV Files (*.csv)"
        )
        if path:
            reply = QMessageBox.question(
                self, "Confirm Import",
                "Add or update entries from CSV?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    n = self.db_manager.import_from_csv(path)
                    self.credentials = self.db_manager.load_all_credentials()
                    self.update_list_view()
                    self._clear_fields()
                    self.enter_view_mode()
                    self.status_bar.showMessage(f"Imported/updated {n} entries.", 5000)
                except Exception as e:
                    QMessageBox.critical(self, "Import Failed", str(e))

    def handle_backup(self):
        """Create a timestamped backup copy of the database file."""
        if not os.path.exists(DB_PATH):
            QMessageBox.warning(self, "No Vault", "Nothing to back up.")
            return
        backup_path = get_timestamped_backup_path()
        try:
            self.db_manager.conn.close()
            shutil.copyfile(DB_PATH, backup_path)
            self.status_bar.showMessage(
                f"Vault backed up → {os.path.basename(backup_path)}", 5000
            )
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))
        finally:
            self.db_manager._connect()

    def handle_restore(self):
        """Restore the database from a user-selected backup file."""
        reply = QMessageBox.question(
            self, "CRITICAL WARNING",
            "Overwrite current vault with a backup?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Backup", os.path.expanduser("~"), "Database files (*.db)"
            )
            if path:
                self.db_manager.conn.close()
                try:
                    shutil.copyfile(path, DB_PATH)
                    err = lambda t, m: QMessageBox.critical(self, t, m)
                    self.db_manager = DatabaseManager(DB_PATH, err)
                    self.db_manager.set_encryption_key(self.master_password_hash)
                    self.credentials = self.db_manager.load_all_credentials()
                    self.update_list_view()
                    self._clear_fields()
                    self.enter_view_mode()
                    self.status_bar.showMessage("Database restored.", 5000)
                except Exception as e:
                    QMessageBox.critical(self, "Restore Failed", str(e))
                finally:
                    self.db_manager._connect()

    # --- About ---

    def show_about_dialog(self):
        """Display the About dialog with application version and license info."""
        QMessageBox.about(
            self, "About AetherVault",
            "<h2>AetherVault</h2>"
            f"<p>Version {VERSION}</p>"
            "<p>PySide6 + SQLite + AES-256</p>"
            "<p>Local, portable, secure credential storage.</p>"
            "<hr>"
            "<p><b>License: GPL v3</b></p>"
            "<p>This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.</p>"
            "<p>This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.</p>",
        )

    # --- Menu Bar ---

    def setup_menu_bar(self):
        """Create the application menu bar with File, Tools, Settings, and Help menus."""
        mb = QMenuBar()

        fm = mb.addMenu("&File")
        a = QAction("&Export Vault (CSV)", self)
        a.triggered.connect(self.handle_export)
        fm.addAction(a)
        a = QAction("&Import Vault (CSV)", self)
        a.triggered.connect(self.handle_import)
        fm.addAction(a)
        fm.addSeparator()
        a = QAction("&Backup Vault", self)
        a.triggered.connect(self.handle_backup)
        fm.addAction(a)
        a = QAction("&Restore Vault", self)
        a.triggered.connect(self.handle_restore)
        fm.addAction(a)
        fm.addSeparator()
        a = QAction("&Quit", self)
        a.triggered.connect(self._quit_application)
        fm.addAction(a)

        tm = mb.addMenu("&Tools")
        a = QAction("Find &Duplicates", self)
        a.triggered.connect(self.find_and_remove_duplicates_ui)
        tm.addAction(a)
        a = QAction("Password &Health", self)
        a.triggered.connect(self.show_password_health)
        tm.addAction(a)
        a = QAction("Fetch &Favicons", self)
        a.triggered.connect(self._fetch_favicons)
        tm.addAction(a)

        sm = mb.addMenu("&Settings")
        self.lockout_actions = []
        lm = sm.addMenu("&Auto-Lock")
        for m in LOCKOUT_OPTIONS:
            a = QAction(f"After {m} Minutes", self, checkable=True)
            a.triggered.connect(lambda checked, x=m: self.set_lockout_time(x))
            lm.addAction(a)
            self.lockout_actions.append(a)
        a = QAction("Never", self, checkable=True)
        a.triggered.connect(lambda checked: self.set_lockout_time(LOCKOUT_NEVER))
        lm.addAction(a)
        self.lockout_actions.append(a)
        self.update_lockout_menu_state()
        sm.addSeparator()
        cur = self.settings.get("theme", "light")
        self.theme_action = QAction(
            f"Switch to {'Light' if cur == 'dark' else 'Dark'} Theme", self,
        )
        self.theme_action.triggered.connect(self.toggle_theme)
        sm.addAction(self.theme_action)

        sm.addSeparator()
        self.portable_action = QAction("&Portable Mode", self, checkable=True)
        self.portable_action.setChecked(is_portable())
        self.portable_action.triggered.connect(self.toggle_portable_mode)
        sm.addAction(self.portable_action)

        hm = mb.addMenu("&Help")
        a = QAction("&Documentation", self)
        a.triggered.connect(self.show_documentation)
        hm.addAction(a)
        a = QAction("&About", self)
        a.triggered.connect(self.show_about_dialog)
        hm.addAction(a)

        self.setMenuBar(mb)

    def update_lockout_menu_state(self):
        """Update the check marks on the auto-lock menu to match current settings."""
        cur = self.settings.get("lockout_minutes", DEFAULT_LOCKOUT_MINUTES)
        for a in self.lockout_actions:
            if "Minutes" in a.text():
                try:
                    m = int(a.text().split()[1])
                except ValueError:
                    m = -1
            elif a.text() == "Never":
                m = LOCKOUT_NEVER
            else:
                continue
            a.setChecked(m == cur)

    def set_lockout_time(self, minutes: int):
        """Set the inactivity lockout duration and reset the activity timer."""
        self.settings["lockout_minutes"] = minutes
        save_settings(self.settings)
        self.update_lockout_menu_state()
        self.reset_activity_timer()
        if minutes == LOCKOUT_NEVER:
            self.status_bar.showMessage("Auto-lock disabled.", 3000)
        else:
            self.status_bar.showMessage(f"Auto-lock set to {minutes} minutes.", 3000)

    # --- Shortcuts ---

    def setup_shortcuts(self):
        """Register keyboard shortcuts for common actions."""
        QShortcut(QKeySequence("Ctrl+N"), self, self.enter_new_mode)
        QShortcut(QKeySequence("Ctrl+E"), self, self._shortcut_edit)
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Esc"), self, self._shortcut_escape)
        QShortcut(QKeySequence("/"), self, self._shortcut_search)

    def _shortcut_edit(self):
        """Enter edit mode via Ctrl+E shortcut."""
        if not self.is_editing and self.current_entry_id:
            self.enter_edit_mode()

    def _shortcut_save(self):
        """Save the current entry via Ctrl+S shortcut."""
        if self.is_editing:
            self.save_credential()

    def _shortcut_escape(self):
        """Cancel editing via Esc shortcut."""
        if self.is_editing:
            self.cancel_edit()

    def _shortcut_search(self):
        """Focus the search field via / shortcut."""
        self.search_entry.setFocus()
        self.search_entry.selectAll()

    # --- Activity Lock ---

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Reset the activity timer on mouse, keyboard, or deactivation events."""
        if self.is_authenticated:
            if event.type() in (
                QEvent.MouseMove, QEvent.KeyPress, QEvent.MouseButtonPress,
            ):
                self.reset_activity_timer()
            elif event.type() == QEvent.WindowDeactivate:
                self.reset_activity_timer()
        return super().eventFilter(source, event)

    def reset_activity_timer(self):
        """Restart the inactivity lockout timer based on current settings."""
        mins = self.settings.get("lockout_minutes", DEFAULT_LOCKOUT_MINUTES)
        if mins == LOCKOUT_NEVER:
            if hasattr(self, "activity_lock_timer"):
                self.activity_lock_timer.stop()
            return
        ms = mins * 60 * 1000
        if hasattr(self, "activity_lock_timer"):
            self.activity_lock_timer.stop()
            self.activity_lock_timer.start(ms)
        else:
            self.activity_lock_timer = QTimer(self)
            self.activity_lock_timer.timeout.connect(self.lock_application)
            self.activity_lock_timer.start(ms)

    def lock_application(self):
        """Lock the application due to inactivity and clear the clipboard."""
        if self.is_authenticated:
            QMessageBox.information(
                self, "Session Locked", "Inactivity detected. Re-login required."
            )
            self.show_auth_screen(setup_mode=False)
            self.activity_lock_timer.stop()
            self.clear_clipboard()

    # --- Password Health ---

    def show_password_health(self):
        """Analyze all credentials and display a password health report dialog."""
        if not self.is_authenticated:
            return QMessageBox.warning(self, "Denied", "Login first.")
        if not self.credentials:
            return QMessageBox.information(self, "Empty", "No entries to check.")

        total = len(self.credentials)
        weak = []
        reused = {}
        empty_short = []

        for c in self.credentials:
            pw = c.password or ""
            if len(pw) < 8:
                empty_short.append(c)
                continue
            score = 0
            if len(pw) >= 8:
                score += 15
            if len(pw) >= 12:
                score += 15
            if len(pw) >= 16:
                score += 10
            if re.search(r"[a-z]", pw):
                score += 10
            if re.search(r"[A-Z]", pw):
                score += 15
            if re.search(r"\d", pw):
                score += 15
            if re.search(r"[^a-zA-Z0-9]", pw):
                score += 20
            score = min(score, 100)
            if score < 50:
                weak.append((c, score))

            reused.setdefault(pw, []).append(c.title)

        dlg = QDialog(self)
        dlg.setWindowTitle("Password Health Report")
        dlg.resize(600, 450)
        layout = QVBoxLayout(dlg)

        reused_entries = {k: v for k, v in reused.items() if len(v) > 1}
        summary = (
            f"Total entries: {total}\n"
            f"Weak passwords (score < 50): {len(weak)}\n"
            f"Reused passwords: {len(reused_entries)}\n"
            f"Empty or short (< 8 chars): {len(empty_short)}"
        )
        layout.addWidget(QLabel(summary))

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Issue", "Title", "Detail"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setFixedHeight(50)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        rows = []
        for c, score in weak:
            rows.append(("Weak password", c.title, f"Score: {score}/100"))
        for c in empty_short:
            label = "Empty" if not c.password else "Short"
            rows.append((f"{label} password", c.title, f"{len(c.password or '')} chars"))
        for pw, titles in reused_entries.items():
            titles_str = ", ".join(titles)
            rows.append(("Reused password", titles[0], f'"{pw[:12]}..." shared by {len(titles)} entries'))

        table.setRowCount(len(rows))
        for ri, (issue, title, detail) in enumerate(rows):
            table.setItem(ri, 0, QTableWidgetItem(issue))
            table.setItem(ri, 1, QTableWidgetItem(title))
            table.setItem(ri, 2, QTableWidgetItem(detail))

        layout.addWidget(table)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()

    # --- Duplicates ---

    def find_and_remove_duplicates_ui(self):
        """Find and remove duplicate credentials (same title + username, keep oldest)."""
        if not self.is_authenticated:
            return QMessageBox.warning(self, "Denied", "Login first.")
        if not self.credentials:
            return QMessageBox.information(self, "Empty", "No entries to check.")
        reply = QMessageBox.question(
            self, "Confirm",
            "Delete duplicates (same Title+Username, keep oldest)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            n = self.db_manager.find_and_remove_duplicates()
            if n > 0:
                self.credentials = self.db_manager.load_all_credentials()
                self.update_list_view()
                self._clear_fields()
                self.enter_view_mode()
                self.status_bar.showMessage(f"Removed {n} duplicates.", 5000)
            else:
                QMessageBox.information(self, "None Found", "No duplicates found.")

    # --- Auto Backup ---

    def _auto_backup_db(self, reason: str):
        """Perform an automatic database backup to the designated backup path."""
        if not os.path.exists(DB_PATH):
            return
        try:
            self.db_manager.conn.close()
            shutil.copyfile(DB_PATH, DB_BACKUP_PATH)
            self.db_manager._connect()
        except Exception as e:
            QMessageBox.warning(self, "Auto-Backup Failed", str(e))
            self.db_manager._connect()

    # --- Portable Mode ---

    def toggle_portable_mode(self):
        """Toggle the application between portable and standard modes."""
        if is_portable():
            if disable_portable_mode():
                self.status_bar.showMessage("Portable mode disabled.", 3000)
                self.portable_action.setChecked(False)
            else:
                QMessageBox.critical(self, "Error", "Failed to disable portable mode.")
        else:
            reply = QMessageBox.question(
                self, "Enable Portable Mode",
                "Portable mode keeps all data in the app directory.\n"
                "Proceed?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                if enable_portable_mode():
                    self.status_bar.showMessage(
                        "Portable mode enabled. Data stays with the app.", 5000
                    )
                    self.portable_action.setChecked(True)
                else:
                    QMessageBox.critical(
                        self, "Error", "Failed to enable portable mode."
                    )

    # --- System Tray ---

    def _make_tray_icon(self) -> QIcon:
        """Create and return a programmatic system tray icon."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#54a0ff"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 16, 16, 3, 3)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Monospace", 8, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "K")
        painter.end()
        return QIcon(pixmap)

    def _setup_system_tray(self):
        """Initialize the system tray icon with a context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._make_tray_icon())
        self.tray_icon.setToolTip("AetherVault")

        tray_menu = QMenu(self)
        self.tray_show_action = tray_menu.addAction("Show Window")
        self.tray_show_action.triggered.connect(self._show_window)
        self.tray_lock_action = tray_menu.addAction("Lock Vault")
        self.tray_lock_action.triggered.connect(self._tray_lock)
        tray_menu.addSeparator()
        self.tray_quit_action = tray_menu.addAction("Quit")
        self.tray_quit_action.triggered.connect(self._quit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)

        self._update_tray_lock_action()
        self.tray_icon.show()

    def _update_tray_lock_action(self):
        """Enable or disable the tray lock action based on auth state."""
        if hasattr(self, "tray_lock_action"):
            self.tray_lock_action.setEnabled(self.is_authenticated)
            self.tray_lock_action.setText(
                "Lock Vault" if self.is_authenticated else "Vault Locked"
            )

    def _tray_activated(self, reason):
        """Show the window on double-click of the tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        """Bring the application window to the foreground."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_lock(self):
        """Lock the vault from the system tray menu."""
        if self.is_authenticated:
            self.lock_application()

    def _quit_application(self):
        """Clean up resources and quit the application."""
        self.tray_icon.hide()
        if self.is_authenticated and os.path.exists(DB_PATH):
            self._auto_backup_db(reason="Shutdown")
        if self.db_manager.conn:
            self.db_manager.conn.close()
        QApplication.quit()

    # --- Close ---

    def closeEvent(self, event):
        """Minimize to tray instead of closing the application."""
        event.ignore()
        self.hide()
        self.status_bar.showMessage("Minimized to tray.", 3000)
