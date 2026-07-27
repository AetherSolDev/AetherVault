# Created: 2025-12-04
# Last Edited: 2026-07-27 16:36 CT (America/Chicago)
# Path: aethervault/gui/app.py
# Purpose: Main application window — coordinates auth, menus, CRUD, import/export.

"""Main application window — coordinates auth, menus, CRUD, import/export."""

import json
import os
import shutil
from typing import List, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence,
    QPainter, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aethervault import (
    PORTABLE_MARKER,
    VERSION,
    disable_portable_mode,
    enable_portable_mode,
    is_portable,
)
from aethervault.core_logic import (
    DB_BACKUP_PATH,
    DB_PATH,
    DEFAULT_LOCKOUT_MINUTES,
    MASTER_KEY_FILE,
    CredentialEntry,
    get_timestamped_backup_path,
    load_master_password,
    load_settings,
    save_settings,
    score_password,
    store_master_password,
    verify_password,
)
from aethervault.db_manager import DatabaseManager
from aethervault.gui.credential_form import CredentialForm
from aethervault.gui.credential_table import CredentialTable
from aethervault.gui.conflict_dialog import ImportConflictDialog
from aethervault.gui.dialogs import DocumentationDialog, PasswordGeneratorDialog, resource_path
from aethervault.gui.theme import DarkThemeColors, ThemeColors
from aethervault.gui.theme import apply_theme as apply_app_theme

LOCKOUT_OPTIONS = [1, 3, 5, 10, 30]
LOCKOUT_NEVER = 0
AUTO_CLEAR_DELAY = 30000


class PySidePWManager(QMainWindow):
    """Main application window — coordinates auth, menus, CRUD, import/export."""

    def __init__(self):
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
        self.credentials: List[CredentialEntry] = []
        self.settings = load_settings()
        self._favicon_cache: dict = {}

        self._apply_theme()

        self.clipboard_clear_time = 15000
        self.clipboard_clear_timer = QTimer(self)
        self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)
        self.form_clear_timer = QTimer(self)
        self.form_clear_timer.setSingleShot(True)
        self.form_clear_timer.timeout.connect(self._clear_form_and_deselect)
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
        QApplication.clipboard().setText("")
        self.clipboard_clear_timer.stop()
        self.status_bar.showMessage("Clipboard cleared.", 3000)

    def copy_to_clipboard(self, text: str, field_name: str = ""):
        if not self.is_authenticated:
            self.status_bar.showMessage("Authentication required to copy.", 3000)
            return
        QApplication.clipboard().setText(text)
        self.clipboard_clear_timer.stop()
        self.clipboard_clear_timer.start(self.clipboard_clear_time)
        self.last_copied_field = field_name
        label = field_name.capitalize() if field_name else "Value"
        self.status_bar.showMessage(f"{label} copied. Will clear in 15s.", 3000)
        QTimer.singleShot(AUTO_CLEAR_DELAY, self._auto_clear_form_check)

    def _auto_clear_form_check(self):
        if self.last_copied_field == "password" and not self.is_editing:
            self._clear_form_and_deselect()
            self.status_bar.showMessage("Password copied — form auto-cleared.", 3000)

    # --- Password Generator ---

    def show_password_generator(self):
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec() == QDialog.Accepted:
            pw = dlg.get_password()
            if pw:
                self.credential_form.set_password(pw)
                self.status_bar.showMessage("Password generated and inserted.", 3000)

    # --- Auth ---

    def check_setup_state(self):
        if not self.master_password_hash:
            self.show_auth_screen(setup_mode=True)
            self.status_bar.showMessage(
                "Welcome! Please set a strong Master Password.", 5000
            )
        else:
            self.show_auth_screen(setup_mode=False)

    def create_auth_ui(self):
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
        if self.action_btn.text() == "Set Master Password":
            self.set_master_password()
        else:
            self.attempt_login()

    def show_auth_screen(self, setup_mode=False):
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
        self.stacked_widget.setCurrentIndex(self.main_index)
        self.credentials = self.db_manager.load_all_credentials()
        self.credential_table.set_credentials(self.credentials)
        self.credential_table.refresh()
        mode = " [Portable]" if is_portable() else ""
        self.status_bar.showMessage(f"Vault unlocked.{mode}", 5000)
        self.credential_table.search_entry.setFocus()
        self.reset_activity_timer()

    # --- Theme ---

    def show_documentation(self):
        path = resource_path(os.path.join("docs", "USER_GUIDE.html"))
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Help Not Found",
                                "Documentation file not found at:\n" + path)

    def _apply_theme(self):
        app = QApplication.instance()
        if app:
            apply_app_theme(app, self.settings.get("theme", "light"))

    def toggle_theme(self):
        current = self.settings.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        self._apply_theme()
        self.credential_table.set_settings(self.settings)
        self.credential_table.refresh()
        self.theme_action.setText(
            f"Switch to {'Light' if new_theme == 'dark' else 'Dark'} Theme"
        )
        self.status_bar.showMessage(f"Switched to {new_theme} mode.", 3000)

    # --- Main Content ---

    def create_main_content(self):
        self.main_content_splitter = QSplitter(Qt.Horizontal)
        self.main_content_splitter.setHandleWidth(6)

        self.credential_table = CredentialTable()
        self.credential_table.set_settings(self.settings)
        self.credential_table.entry_selected.connect(self._on_entry_selected)
        self.credential_table.copy_requested.connect(self.copy_to_clipboard)
        self.credential_table.edit_requested.connect(self.enter_edit_mode)
        self.credential_table.delete_requested.connect(self.delete_credential)
        self.credential_table.add_new_requested.connect(self.enter_new_mode)

        self.credential_form = CredentialForm()
        self.credential_form.save_requested.connect(self.save_credential)
        self.credential_form.cancel_requested.connect(self.cancel_edit)
        self.credential_form.copy_requested.connect(self.copy_to_clipboard)
        self.credential_form.generate_password_requested.connect(self.show_password_generator)

        self.credential_table.setMinimumWidth(300)
        self.credential_form.setMinimumWidth(400)
        self.credential_form.setMaximumWidth(700)
        self.main_content_splitter.addWidget(self.credential_table)
        self.main_content_splitter.addWidget(self.credential_form)
        self.main_content_splitter.setSizes([500, 500])
        self.main_content_splitter.setStretchFactor(0, 1)
        self.main_content_splitter.setStretchFactor(1, 1)
        self.main_index = self.stacked_widget.addWidget(self.main_content_splitter)

    def _on_entry_selected(self, db_id: int):
        if db_id < 0:
            self.current_entry_id = None
            self.credential_form.clear_form()
            self.credential_form.enter_view_mode()
            return
        if self.credential_form.is_editing:
            return
        entry = next((c for c in self.credentials if c.db_id == db_id), None)
        if entry:
            self.current_entry_id = db_id
            self.credential_form.fill_form(entry)
            self.credential_form.enter_view_mode()

    # --- View / Edit Mode ---

    def enter_edit_mode(self):
        if self.current_entry_id is None:
            return
        self.is_editing = True
        self.credential_form.enter_edit_mode()

    def enter_new_mode(self):
        self.is_editing = True
        self.previous_entry_id = self.current_entry_id
        self.current_entry_id = None
        self.credential_form.enter_new_mode()
        self.credential_table.clear_selection()

    def cancel_edit(self):
        if self.current_entry_id:
            entry = next(
                (c for c in self.credentials if c.db_id == self.current_entry_id), None
            )
            if entry:
                self.credential_form.fill_form(entry)
                self.credential_form.enter_view_mode()
                self.is_editing = False
                return
        if self.previous_entry_id:
            self.current_entry_id = self.previous_entry_id
            entry = next(
                (c for c in self.credentials if c.db_id == self.previous_entry_id), None
            )
            if entry:
                self.credential_form.fill_form(entry)
                self.credential_form.enter_view_mode()
                self.credential_table.select_entry(self.previous_entry_id)
        else:
            self.credential_form.clear_form()
        self.credential_form.enter_view_mode()
        self.is_editing = False

    # --- Save / Delete ---

    def save_credential(self, form_data: dict):
        title = form_data.get("title", "").strip()
        password = form_data.get("password", "").strip()
        if not title or not password:
            QMessageBox.warning(
                self, "Missing Data",
                "Both 'Title' and 'Password' fields are required.",
            )
            return
        entry = CredentialEntry(**form_data)
        if entry.db_id:
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
        self.credential_table.set_credentials(self.credentials)
        self.credential_table.refresh()
        self.credential_form.fill_form(entry)
        self.credential_form.enter_view_mode()
        self.current_entry_id = entry.db_id
        self.is_editing = False
        self.credential_table.select_entry(entry.db_id)
        self.status_bar.showMessage(msg, 5000)

    def delete_credential(self):
        if self.current_entry_id is None:
            return
        title = self.credential_form.input_fields["title"].text()
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
            self.credential_form.clear_form()
            self.credential_form.enter_view_mode()
            self.credential_table.set_credentials(self.credentials)
            self.credential_table.refresh()
            self.current_entry_id = None
            self.is_editing = False
            self.status_bar.showMessage(f"Entry '{title}' deleted.", 5000)

    def _clear_form_and_deselect(self):
        self.credential_form.clear_form()
        self.credential_form.enter_view_mode()
        self.credential_table.clear_selection()

    # --- Import / Export / Backup ---

    def handle_export(self):
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
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Credentials", os.path.expanduser("~"), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            preview = self.db_manager.preview_import(path)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))
            return

        total = preview["total_rows"]
        conflicts = preview["conflicts"]
        non_conflict = preview["non_conflict_count"]

        if total == 0:
            QMessageBox.information(self, "Import", "No valid entries found in CSV.")
            return

        if not conflicts:
            # No conflicts — import directly
            try:
                n = self.db_manager.import_from_csv(path)
                self._post_import(n)
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", str(e))
            return

        # Conflicts exist — ask user what to do
        msg = (
            f"Found <b>{len(conflicts)} conflict(s)</b> out of {total} entries "
            f"(<b>{non_conflict}</b> new entries will import silently)."
        )
        reply = QMessageBox.question(
            self, "Import Conflicts",
            msg + "\n\nImport all now and review duplicates later?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Cancel:
            return
        if reply == QMessageBox.Yes:
            # Import all, review later
            try:
                n = self.db_manager.import_from_csv(path)
                self._post_import(n)
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", str(e))
            return

        # Review conflicts one by one
        dlg = ImportConflictDialog(conflicts, self)
        if dlg.exec() != QDialog.Accepted:
            return
        decisions = dlg.get_decisions()
        try:
            n = self.db_manager.execute_import(path, decisions)
            self._post_import(n)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

    def _post_import(self, n: int):
        """Reload credentials and refresh UI after an import."""
        self.credentials = self.db_manager.load_all_credentials()
        self.credential_table.set_credentials(self.credentials)
        self.credential_table.refresh()
        self.credential_form.clear_form()
        self.credential_form.enter_view_mode()
        self.current_entry_id = None
        self.is_editing = False
        self.status_bar.showMessage(f"Imported/updated {n} entries.", 5000)

    def handle_backup(self):
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
                    self.credential_table.set_credentials(self.credentials)
                    self.credential_table.refresh()
                    self.credential_form.clear_form()
                    self.credential_form.enter_view_mode()
                    self.current_entry_id = None
                    self.is_editing = False
                    self.status_bar.showMessage("Database restored.", 5000)
                except Exception as e:
                    QMessageBox.critical(self, "Restore Failed", str(e))
                finally:
                    self.db_manager._connect()

    # --- About ---

    def show_about_dialog(self):
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
        mb = QMenuBar()
        self._build_file_menu(mb)
        self._build_tools_menu(mb)
        self._build_settings_menu(mb)
        self._build_help_menu(mb)
        self.setMenuBar(mb)

    def _build_file_menu(self, mb: QMenuBar):
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

    def _build_tools_menu(self, mb: QMenuBar):
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

    def _build_settings_menu(self, mb: QMenuBar):
        sm = mb.addMenu("&Settings")
        self.lockout_actions = []
        lm = sm.addMenu("&Auto-Lock")
        for m in LOCKOUT_OPTIONS:
            a = QAction(f"After {m} Minutes", self, checkable=True)
            a.triggered.connect(lambda checked, x=m: self.set_lockout_time(x))
            lm.addAction(a)
            self.lockout_actions.append(a)
        a = QAction("Never", self, checkable=True)
        a.triggered.connect(lambda: self.set_lockout_time(LOCKOUT_NEVER))
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

    def _build_help_menu(self, mb: QMenuBar):
        hm = mb.addMenu("&Help")
        a = QAction("&Documentation", self)
        a.triggered.connect(self.show_documentation)
        hm.addAction(a)
        a = QAction("&About", self)
        a.triggered.connect(self.show_about_dialog)
        hm.addAction(a)

    def update_lockout_menu_state(self):
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
        QShortcut(QKeySequence("Ctrl+N"), self, self.enter_new_mode)
        QShortcut(QKeySequence("Ctrl+E"), self, self._shortcut_edit)
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Esc"), self, self._shortcut_escape)
        QShortcut(QKeySequence("/"), self, self._shortcut_search)

    def _shortcut_edit(self):
        if not self.is_editing and self.current_entry_id:
            self.enter_edit_mode()

    def _shortcut_save(self):
        if self.is_editing:
            self.save_credential(self.credential_form.get_form_data())

    def _shortcut_escape(self):
        if self.is_editing:
            self.cancel_edit()

    def _shortcut_search(self):
        self.credential_table.search_entry.setFocus()
        self.credential_table.search_entry.selectAll()

    # --- Activity Lock ---

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if self.is_authenticated:
            if event.type() in (
                QEvent.MouseMove, QEvent.KeyPress, QEvent.MouseButtonPress,
            ):
                self.reset_activity_timer()
            elif event.type() == QEvent.WindowDeactivate:
                self.reset_activity_timer()
        return super().eventFilter(source, event)

    def reset_activity_timer(self):
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
        if self.is_authenticated:
            QMessageBox.information(
                self, "Session Locked", "Inactivity detected. Re-login required."
            )
            self.show_auth_screen(setup_mode=False)
            self.activity_lock_timer.stop()
            self.clear_clipboard()

    # --- Password Health ---

    def show_password_health(self):
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
            score = score_password(pw)
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
                self.credential_table.set_credentials(self.credentials)
                self.credential_table.refresh()
                self.credential_form.clear_form()
                self.credential_form.enter_view_mode()
                self.current_entry_id = None
                self.is_editing = False
                self.status_bar.showMessage(f"Removed {n} duplicates.", 5000)
            else:
                QMessageBox.information(self, "None Found", "No duplicates found.")

    # --- Favicons ---

    def _fetch_favicons(self):
        if not self.is_authenticated:
            return QMessageBox.warning(self, "Denied", "Login first.")
        if not self.credentials:
            return
        domain_count = len({QUrl(c.url).host() for c in self.credentials if c.url})
        if domain_count == 0:
            self.status_bar.showMessage("No URLs with domains to fetch.", 3000)
            return
        self.status_bar.showMessage(f"Fetching favicons for {domain_count} domains...", 5000)
        self.credential_table.set_favicon_cache(self._favicon_cache)
        self.credential_table.fetch_favicons()

    # --- Auto Backup ---

    def _auto_backup_db(self, reason: str):
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
        if hasattr(self, "tray_lock_action"):
            self.tray_lock_action.setEnabled(self.is_authenticated)
            self.tray_lock_action.setText(
                "Lock Vault" if self.is_authenticated else "Vault Locked"
            )

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_lock(self):
        if self.is_authenticated:
            self.lock_application()

    def _quit_application(self):
        self.tray_icon.hide()
        if self.is_authenticated and os.path.exists(DB_PATH):
            self._auto_backup_db(reason="Shutdown")
        if self.db_manager.conn:
            self.db_manager.conn.close()
        QApplication.quit()

    # --- Close ---

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.status_bar.showMessage("Minimized to tray.", 3000)
