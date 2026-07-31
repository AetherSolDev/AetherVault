# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
# Path: aethervault/gui/conflict_dialog.py
# Purpose: Import conflict review dialog for per-entry resolution.

"""Import conflict review dialog for per-entry resolution."""

from typing import Dict, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ImportConflictDialog(QDialog):
    """Dialog for reviewing and resolving import conflicts per entry."""

    def __init__(self, conflicts: List[Dict], parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.decisions: Dict[Tuple[str, str], str] = {}
        self._groups: List[QButtonGroup] = []
        self.setWindowTitle("Resolve Import Conflicts")
        self.resize(800, 500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        warning = QLabel(
            "<b>⚠️  Passwords will be displayed below.</b> "
            "This dialog is in a secure context — only visible to you."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("padding: 8px; background: #fff3cd; border: 1px solid #ffc107;")
        layout.addWidget(warning)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Title", "Username", "Vault Password", "Import Password", "Action"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setRowCount(len(self.conflicts))

        self._groups = []
        for ri, conflict in enumerate(self.conflicts):
            vault = conflict["vault"]
            imp = conflict["import"]

            table.setItem(ri, 0, QTableWidgetItem(vault.get("title", "")))
            table.setItem(ri, 1, QTableWidgetItem(vault.get("username", "")))
            table.setItem(ri, 2, QTableWidgetItem(vault.get("password", "")))
            table.setItem(ri, 3, QTableWidgetItem(imp.get("password", "")))

            group = QButtonGroup(self)
            keep_rb = QRadioButton("Keep Vault")
            replace_rb = QRadioButton("Use Import")
            group.addButton(keep_rb)
            group.addButton(replace_rb)
            keep_rb.setChecked(True)

            key = (vault.get("title", "").lower().strip(), vault.get("username", "").lower().strip())
            self.decisions[key] = "keep_vault"
            group.buttonClicked.connect(lambda checked, k=key, g=group: self._on_decision_changed(k, g))

            hb = QHBoxLayout()
            hb.addWidget(keep_rb)
            hb.addWidget(replace_rb)
            hb.addStretch()
            cell_widget = QWidget()
            cell_widget.setLayout(hb)
            table.setCellWidget(ri, 4, cell_widget)
            self._groups.append(group)

        layout.addWidget(table)

        bulk = QHBoxLayout()
        keep_all = QPushButton("Keep All Vault")
        keep_all.clicked.connect(lambda: self._bulk_set("keep_vault"))
        bulk.addWidget(keep_all)
        replace_all = QPushButton("Replace All")
        replace_all.clicked.connect(lambda: self._bulk_set("replace"))
        bulk.addWidget(replace_all)
        bulk.addStretch()
        layout.addLayout(bulk)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel Import")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        confirm_btn = QPushButton("Confirm Import")
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _on_decision_changed(self, key: Tuple[str, str], group: QButtonGroup):
        checked = group.checkedButton()
        if checked:
            idx = group.buttons().index(checked)
            self.decisions[key] = "keep_vault" if idx == 0 else "replace"

    def _bulk_set(self, decision: str):
        for ri, group in enumerate(self._groups):
            buttons = group.buttons()
            if decision == "keep_vault":
                buttons[0].setChecked(True)
            else:
                buttons[1].setChecked(True)
            vault = self.conflicts[ri]["vault"]
            key = (vault.get("title", "").lower().strip(), vault.get("username", "").lower().strip())
            self.decisions[key] = decision

    def get_decisions(self) -> Dict[Tuple[str, str], str]:
        """Return the final conflict decisions map."""
        return self.decisions
