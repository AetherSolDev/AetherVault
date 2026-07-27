# Created: 2026-07-27
# Last Edited: 2026-07-27 16:36 CT (America/Chicago)
# Path: aethervault/gui/credential_table.py
# Purpose: Credential list table widget with search, filter, and context menu.

"""Credential list table widget with search, filter, and context menu."""

from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aethervault.core_logic import CredentialEntry
from aethervault.gui.theme import DarkThemeColors, ThemeColors


class CredentialTable(QWidget):
    entry_selected = Signal(int)
    copy_requested = Signal(str, str)
    edit_requested = Signal()
    delete_requested = Signal()
    add_new_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.credentials: List[CredentialEntry] = []
        self.settings = {}
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder
        self._favicon_cache: dict = {}
        self._network_manager = QNetworkAccessManager()
        self._search_text = ""
        self._selected_category = "All Categories"
        self._selected_tag = "All Tags"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        sl = QHBoxLayout()
        sl.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Filter by title, username, or URL...")
        self.search_entry.textChanged.connect(self._on_search_changed)
        sl.addWidget(self.search_entry)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentIndexChanged.connect(self._on_filter_changed)
        sl.addWidget(self.category_filter)
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All Tags")
        self.tag_filter.currentIndexChanged.connect(self._on_filter_changed)
        sl.addWidget(self.tag_filter)
        layout.addLayout(sl)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.horizontalHeader().sectionClicked.connect(self._on_sort)
        layout.addWidget(self.table)

        lbl = QHBoxLayout()
        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self.add_new_requested.emit)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_requested.emit)
        self.edit_btn.setEnabled(False)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.delete_btn.setEnabled(False)
        lbl.addWidget(self.add_btn)
        lbl.addWidget(self.edit_btn)
        lbl.addWidget(self.delete_btn)
        layout.addLayout(lbl)

    def set_credentials(self, credentials: List[CredentialEntry]):
        self.credentials = credentials
        self.refresh()

    def set_settings(self, settings: dict):
        self.settings = settings

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        filtered = self._filter_credentials()
        theme = self.settings.get("theme", "light")
        theme_colors = DarkThemeColors if theme == "dark" else ThemeColors
        highlight = QColor(theme_colors.BG_TERTIARY)

        headers = ["Title", "Username", "URL", "Category", "ID", "Last Used", "Pass Changed"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setColumnHidden(4, True)
        self.table.setRowCount(len(filtered))

        for ri, entry in enumerate(filtered):
            for ci, val in [
                (0, entry.title), (1, entry.username),
                (2, entry.url), (3, entry.category),
                (4, str(entry.db_id)),
                (5, entry.time_last_used), (6, entry.time_password_changed),
            ]:
                item = QTableWidgetItem(val)
                if self._search_text and self._search_text in val.lower():
                    item.setBackground(highlight)
                if ci == 0 and entry.url:
                    try:
                        domain = QUrl(entry.url).host()
                        if domain and domain in self._favicon_cache:
                            item.setIcon(self._favicon_cache[domain])
                    except Exception:
                        pass
                self.table.setItem(ri, ci, item)

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Interactive)
        h.setSectionResizeMode(1, QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Interactive)
        h.setSectionResizeMode(5, QHeaderView.Interactive)
        h.setSectionResizeMode(6, QHeaderView.Interactive)
        h.resizeSection(0, 220)
        h.resizeSection(1, 160)
        h.resizeSection(3, 140)
        h.resizeSection(5, 100)
        h.resizeSection(6, 100)
        h.setMinimumSectionSize(100)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setFixedHeight(50)
        self._populate_category_filter()
        self._populate_tag_filter()

    def _filter_credentials(self) -> List[CredentialEntry]:
        search = self._search_text
        selected_cat = self._selected_category
        selected_tag = self._selected_tag
        return [
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

    def _on_search_changed(self, text: str):
        self._search_text = text.lower()
        self.refresh()

    def _on_filter_changed(self):
        self._selected_category = self.category_filter.currentText()
        self._selected_tag = self.tag_filter.currentText()
        self.refresh()

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.delete_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.entry_selected.emit(-1)
            return
        item = self.table.item(rows[0].row(), 4)
        if item is None:
            return
        try:
            db_id = int(item.text())
        except ValueError:
            return
        self.delete_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.entry_selected.emit(db_id)

    def _on_cell_double_clicked(self, row: int, col: int):
        if col == 4:
            return
        item = self.table.item(row, col)
        if not item or not item.text():
            return
        labels = {0: "title", 1: "username", 2: "url", 3: "category", 5: "last used", 6: "pass changed"}
        label = labels.get(col, "value")
        self.copy_requested.emit(item.text(), label)

    def _on_cell_clicked(self, row: int, col: int):
        if col != 3:
            return
        item = self.table.item(row, col)
        if not item or not item.text():
            return
        idx = self.category_filter.findText(item.text())
        if idx >= 0:
            self.category_filter.setCurrentIndex(idx)

    def _on_sort(self, column: int):
        if column == 4:
            return
        if self.sort_column == column:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.AscendingOrder
        self.table.sortItems(column, self.sort_order)

    def _context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        entry_id_item = self.table.item(row, 4)
        if not entry_id_item:
            return
        username_item = self.table.item(row, 1)
        menu = QMenu(self)
        if username_item and username_item.text():
            a = menu.addAction("Copy Username")
            a.triggered.connect(lambda: self.copy_requested.emit(username_item.text(), "username"))
        a = menu.addAction("Copy Password")
        a.triggered.connect(lambda: self._context_copy_password(entry_id_item))
        menu.addSeparator()
        a = menu.addAction("Edit Entry")
        a.triggered.connect(self.edit_requested.emit)
        a = menu.addAction("Delete Entry")
        a.triggered.connect(self.delete_requested.emit)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _context_copy_password(self, entry_id_item):
        try:
            db_id = int(entry_id_item.text())
        except ValueError:
            return
        entry = next((c for c in self.credentials if c.db_id == db_id), None)
        if entry and entry.password:
            self.copy_requested.emit(entry.password, "password")

    def select_entry(self, db_id: int):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)
            if item and item.text() == str(db_id):
                self.table.selectRow(row)
                break

    def clear_selection(self):
        self.table.clearSelection()

    def _populate_category_filter(self):
        current = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        categories = sorted({c.category for c in self.credentials if c.category})
        self.category_filter.addItems(categories)
        idx = self.category_filter.findText(current)
        if idx >= 0:
            self.category_filter.setCurrentIndex(idx)
        self.category_filter.blockSignals(False)

    def _populate_tag_filter(self):
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

    def set_favicon_cache(self, cache: dict):
        self._favicon_cache = cache

    def fetch_favicons(self):
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
            return
        for domain in domains:
            if domain in self._favicon_cache:
                continue
            url = QUrl(f"https://www.google.com/s2/favicons?domain={domain}&sz=16")
            req = QNetworkRequest(url)
            reply = self._network_manager.get(req)
            reply.finished.connect(lambda r=reply, d=domain: self._on_favicon_fetched(r, d))

    def _on_favicon_fetched(self, reply, domain: str):
        data = reply.readAll()
        reply.deleteLater()
        if data and len(data) > 0:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self._favicon_cache[domain] = QIcon(pixmap)
                self.refresh()
