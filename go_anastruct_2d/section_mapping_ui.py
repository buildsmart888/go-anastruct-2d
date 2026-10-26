"""Single review dialog for all factory steel sections (IngeTrazo / PySide6).

One action chooses all section/axis mappings and one consent confirms nominal
unverified data. Cancelling preserves the user's existing FEM and scene.
"""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .engineering_core import CatalogError
from .section_mapping_policy import choices_for_section, preview_values


class FactorySectionMappingDialog(QDialog):
    """No per-section popups. One grouped table + one explicit consent gate."""

    def __init__(self, section_ids, previous=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GO Factory — Review steel sections / axis (PREVIEW)")
        self.resize(1030, max(420, min(650, 250 + 50 * len(section_ids))))
        self._ids = sorted(set(section_ids))
        self._previous = previous or {}
        self._boxes = []
        self._labels = []
        root = QVBoxLayout(self)

        notice = QLabel(
            "All entries are factory steel members. Choose a section and "
            "in-plane bending axis for EACH profile.\n"
            "GO Core nominal A/Iz are geometric approximations (no fillets, "
            "fabrication tolerances or manufacturer verification). "
            "Manual steel alternatives are NOT equivalent physical sections. "
            "These values are for PREVIEW only, not structural design."
        )
        notice.setWordWrap(True)
        root.addWidget(notice)

        table = QTableWidget(len(self._ids), 5, self)
        self.table = table
        table.setHorizontalHeaderLabels(
            ["GO Factory section", "Analysis mapping / bending axis",
             "A [m²]", "Iz in-plane [m⁴]", "Property status"]
        )
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        for idx, section in enumerate(self._ids):
            cell = QTableWidgetItem(section)
            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(idx, 0, cell)
            choices = choices_for_section(section)
            select = QComboBox(table)
            for title, payload in choices:
                select.addItem(title, payload)
            prior = self._previous.get(section)
            if isinstance(prior, str):
                prior = {"mode": "manual_starter", "section": prior,
                         "acknowledged": True}
            if isinstance(prior, dict):
                for option in range(select.count()):
                    entry = select.itemData(option)
                    if entry.get("mode") == prior.get("mode") and (
                        entry.get("axis", entry.get("section")) ==
                        prior.get("axis", prior.get("section"))
                    ):
                        select.setCurrentIndex(option)
                        break
            table.setCellWidget(idx, 1, select)
            info = []
            for col in (2, 3, 4):
                item = QTableWidgetItem("")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(idx, col, item)
                info.append(item)
            self._labels.append(info)
            self._boxes.append(select)
            select.currentIndexChanged.connect(
                lambda _index, row=idx: self._update_row(row)
            )
            self._update_row(idx)

        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(0, 235)
        header.resizeSection(1, 365)
        header.resizeSection(2, 100)
        header.resizeSection(3, 125)
        root.addWidget(table, 1)
        self.consent = QCheckBox(
            "I understand these nominal properties / alternative sections are "
            "UNVERIFIED demonstration inputs and must be checked before design."
        )
        # QCheckBox does not implement QLabel.setWordWrap in Qt 6.
        root.addWidget(self.consent)
        bottom = QHBoxLayout()
        note = QLabel("No model, geometry, loads or releases change until Apply is confirmed.")
        note.setWordWrap(True)
        bottom.addWidget(note, 1)
        root.addLayout(bottom)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel, parent=self
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Apply Sections & Continue"
        )
        buttons.accepted.connect(self._accept_review)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _update_row(self, row):
        data = self._boxes[row].currentData()
        if data is None:
            for item in self._labels[row]:
                item.setText("Unavailable")
            return
        try:
            values = preview_values(self._ids[row], data)
        except (CatalogError, ValueError, KeyError) as exc:
            values = ("—", "—", f"ERROR: {exc}")
        for cell, value in zip(self._labels[row], values):
            cell.setText(value)

    def selection(self):
        mapping = {}
        for section, combo in zip(self._ids, self._boxes):
            choice = combo.currentData()
            if not isinstance(choice, dict):
                raise CatalogError(f"{section}: no valid analysis mapping")
            # Preview only. The bridge will validate each selected mode.
            preview_values(section, choice)
            mapping[section] = copy.deepcopy(choice)
        return mapping

    def _accept_review(self):
        if not self.consent.isChecked():
            QMessageBox.warning(
                self, "Explicit engineering acknowledgement required",
                "Please acknowledge that nominal properties and manual "
                "substitutions have not been verified for structural design."
            )
            return
        try:
            self.selection()
        except (CatalogError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Invalid section mapping", str(exc))
            return
        self.accept()
