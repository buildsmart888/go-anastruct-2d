from __future__ import annotations
import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from .load_cases import (
    CASE_TYPES, COMBINATION_METHODS, apply_load_case_configuration,
    combination_metadata, guess_case_type, metadata_for_cases,
)


class LoadCaseCombinationDialog(QDialog):
    """Excel-like load-case and load-combination editor."""

    def __init__(self, model: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Cases / Load Combinations")
        self.resize(920, 650)
        self.original = copy.deepcopy(model)
        self.data = copy.deepcopy(model)
        self._combo_cache = copy.deepcopy(model.get("combinations", {}) or {})
        self._combo_meta_cache = combination_metadata(model)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Load Case = กรณีแรงแต่ละชนิด · Load Combination = ตัวคูณรวมกรณีแรง\n"
            "กรอก factor ลงในคอลัมน์ DL / LL / WL ได้โดยตรง เช่น ULS: 1.2DL + 1.6LL"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        root.addWidget(QLabel("Load Cases"))
        self.case_table = QTableWidget(0, 3)
        self.case_table.setHorizontalHeaderLabels(["Case ID", "Type", "Description"])
        self.case_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.case_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.case_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.case_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        root.addWidget(self.case_table, 1)

        case_buttons = QHBoxLayout()
        add_case = QPushButton("+ Add Load Case")
        remove_case = QPushButton("Remove selected")
        copy_cases = QPushButton("Copy table")
        preset = QPushButton("Preset DL + LL")
        case_buttons.addWidget(add_case); case_buttons.addWidget(remove_case); case_buttons.addWidget(copy_cases); case_buttons.addWidget(preset); case_buttons.addStretch()
        root.addLayout(case_buttons)

        sw = QHBoxLayout()
        self.self_weight = QCheckBox("Include Self-weight")
        self.self_weight_case = QComboBox()
        sw.addWidget(self.self_weight)
        sw.addWidget(QLabel("Apply self-weight to:"))
        sw.addWidget(self.self_weight_case, 1)
        root.addLayout(sw)

        root.addWidget(QLabel("Load Combinations — factors"))
        self.combo_table = QTableWidget(0, 2)
        self.combo_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        root.addWidget(self.combo_table, 1)

        combo_buttons = QHBoxLayout()
        add_combo = QPushButton("+ Add Combination")
        remove_combo = QPushButton("Remove selected")
        copy_combos = QPushButton("Copy table")
        add_uls = QPushButton("Preset 1.2DL + 1.6LL")
        combo_buttons.addWidget(add_combo); combo_buttons.addWidget(remove_combo); combo_buttons.addWidget(copy_combos); combo_buttons.addWidget(add_uls); combo_buttons.addStretch()
        root.addLayout(combo_buttons)

        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color: #b00020;")
        root.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_data)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        add_case.clicked.connect(lambda: self.add_case_row("", "Other", ""))
        remove_case.clicked.connect(self.remove_cases)
        copy_cases.clicked.connect(lambda: self.copy_table(self.case_table))
        preset.clicked.connect(self.add_dl_ll)
        add_combo.clicked.connect(lambda: self.add_combo_row("", "Custom", {}))
        remove_combo.clicked.connect(self.remove_combinations)
        copy_combos.clicked.connect(lambda: self.copy_table(self.combo_table))
        add_uls.clicked.connect(self.add_uls_preset)
        self.case_table.itemChanged.connect(self._case_table_changed)
        self.self_weight.toggled.connect(self.self_weight_case.setEnabled)

        meta = metadata_for_cases(model)
        self.case_table.blockSignals(True)
        for case in model.get("cases", []):
            row = meta.get(case, {})
            self.add_case_row(case, row.get("type", guess_case_type(case)), row.get("description", ""))
        self.case_table.blockSignals(False)
        self.self_weight.setChecked(bool(model.get("self_weight", False)))
        self._refresh_case_dependent_controls()
        if model.get("self_weight_case") in model.get("cases", []):
            self.self_weight_case.setCurrentText(model["self_weight_case"])
        self.self_weight_case.setEnabled(self.self_weight.isChecked())
        self._rebuild_combo_table()

    @staticmethod
    def table_tsv(table):
        headers = []
        for c in range(table.columnCount()):
            item = table.horizontalHeaderItem(c)
            headers.append(item.text() if item else "")
        rows = [headers]
        for r in range(table.rowCount()):
            values = []
            for c in range(table.columnCount()):
                widget = table.cellWidget(r, c)
                if widget is not None and hasattr(widget, "currentText"):
                    values.append(widget.currentText())
                else:
                    item = table.item(r, c)
                    values.append(item.text() if item else "")
            rows.append(values)
        return "\n".join("\t".join(str(value) for value in row) for row in rows)

    def copy_table(self, table):
        QGuiApplication.clipboard().setText(self.table_tsv(table))

    def _case_ids(self):
        out = []
        for i in range(self.case_table.rowCount()):
            item = self.case_table.item(i, 0)
            case = item.text().strip() if item else ""
            if case:
                out.append(case)
        return out

    def add_case_row(self, case_id, case_type="Other", description=""):
        was_blocked = self.case_table.signalsBlocked()
        self.case_table.blockSignals(True)
        row = self.case_table.rowCount()
        self.case_table.insertRow(row)
        self.case_table.setItem(row, 0, QTableWidgetItem(case_id))
        combo = QComboBox()
        combo.addItems(CASE_TYPES)
        combo.setCurrentText(case_type if case_type in CASE_TYPES else "Other")
        self.case_table.setCellWidget(row, 1, combo)
        self.case_table.setItem(row, 2, QTableWidgetItem(description))
        combo.currentTextChanged.connect(lambda _=None: self._case_table_changed())
        self.case_table.blockSignals(was_blocked)
        if not was_blocked:
            self._case_table_changed()

    def _snapshot_combo_table(self):
        if self.combo_table.columnCount() < 2:
            return
        cases = [self.combo_table.horizontalHeaderItem(i).text() for i in range(2, self.combo_table.columnCount())]
        combos = {}
        meta = {}
        for r in range(self.combo_table.rowCount()):
            name_item = self.combo_table.item(r, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            method_widget = self.combo_table.cellWidget(r, 1)
            method = method_widget.currentText() if method_widget else "Custom"
            factors = {}
            for c, case in enumerate(cases, start=2):
                item = self.combo_table.item(r, c)
                text = item.text().strip() if item else ""
                if text:
                    try:
                        factors[case] = float(text)
                    except ValueError:
                        pass
            combos[name] = factors
            meta[name] = {"method": method}
        self._combo_cache = combos
        self._combo_meta_cache = meta

    def _case_table_changed(self, *_):
        old_cases = [
            self.combo_table.horizontalHeaderItem(i).text()
            for i in range(2, self.combo_table.columnCount())
            if self.combo_table.horizontalHeaderItem(i) is not None
        ]
        previous_sw = self.self_weight_case.currentText()
        self._snapshot_combo_table()
        new_cases = self._case_ids()
        if len(old_cases) == len(new_cases):
            for old, new in zip(old_cases, new_cases):
                if old == new:
                    continue
                for factors in self._combo_cache.values():
                    if old in factors and new not in factors:
                        factors[new] = factors.pop(old)
                if previous_sw == old:
                    previous_sw = new
        self._refresh_case_dependent_controls()
        if previous_sw in new_cases:
            self.self_weight_case.setCurrentText(previous_sw)
        self._rebuild_combo_table()

    def _refresh_case_dependent_controls(self):
        cases = self._case_ids()
        current = self.self_weight_case.currentText()
        self.self_weight_case.blockSignals(True)
        self.self_weight_case.clear()
        self.self_weight_case.addItems(cases)
        if current in cases:
            self.self_weight_case.setCurrentText(current)
        elif "DL" in cases:
            self.self_weight_case.setCurrentText("DL")
        self.self_weight_case.blockSignals(False)

    def _rebuild_combo_table(self):
        cases = self._case_ids()
        self.combo_table.blockSignals(True)
        self.combo_table.setColumnCount(2 + len(cases))
        self.combo_table.setHorizontalHeaderLabels(["Combination", "Method"] + cases)
        self.combo_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.combo_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(2, 2 + len(cases)):
            self.combo_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.combo_table.setRowCount(0)
        for name, factors in self._combo_cache.items():
            self.add_combo_row(name, (self._combo_meta_cache.get(name, {}) or {}).get("method", "Custom"), factors)
        self.combo_table.blockSignals(False)

    def add_combo_row(self, name, method="Custom", factors=None):
        factors = factors or {}
        row = self.combo_table.rowCount()
        self.combo_table.insertRow(row)
        self.combo_table.setItem(row, 0, QTableWidgetItem(name))
        method_box = QComboBox()
        method_box.addItems(COMBINATION_METHODS)
        method_box.setCurrentText(method if method in COMBINATION_METHODS else "Custom")
        self.combo_table.setCellWidget(row, 1, method_box)
        cases = self._case_ids()
        for index, case in enumerate(cases, start=2):
            value = factors.get(case, "")
            self.combo_table.setItem(row, index, QTableWidgetItem("" if value == "" else f"{float(value):g}"))

    def remove_cases(self):
        self._snapshot_combo_table()
        rows = sorted({idx.row() for idx in self.case_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.case_table.removeRow(row)
        self._refresh_case_dependent_controls()
        self._rebuild_combo_table()

    def remove_combinations(self):
        rows = sorted({idx.row() for idx in self.combo_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.combo_table.removeRow(row)
        self._snapshot_combo_table()

    def add_dl_ll(self):
        self._snapshot_combo_table()
        existing = set(self._case_ids())
        self.case_table.blockSignals(True)
        if "DL" not in existing:
            self.add_case_row("DL", "Dead", "Dead load / self-weight")
        if "LL" not in existing:
            self.add_case_row("LL", "Live", "Live load")
        self.case_table.blockSignals(False)
        self._refresh_case_dependent_controls()
        self._rebuild_combo_table()
        if "DL" in self._case_ids():
            self.self_weight.setChecked(True)
            self.self_weight_case.setCurrentText("DL")

    def add_uls_preset(self):
        if "DL" not in self._case_ids() or "LL" not in self._case_ids():
            self.add_dl_ll()
        self._snapshot_combo_table()
        self._combo_cache["ULS"] = {"DL": 1.2, "LL": 1.6}
        self._combo_meta_cache["ULS"] = {"method": "LRFD"}
        self._rebuild_combo_table()

    def _collect_cases(self):
        cases = []
        meta = {}
        for r in range(self.case_table.rowCount()):
            item = self.case_table.item(r, 0)
            case = item.text().strip() if item else ""
            if not case:
                raise ValueError(f"Load Cases row {r + 1}: enter Case ID")
            if case in cases:
                raise ValueError(f"Duplicate Load Case ID: {case}")
            type_box = self.case_table.cellWidget(r, 1)
            desc_item = self.case_table.item(r, 2)
            cases.append(case)
            meta[case] = {
                "type": type_box.currentText() if type_box else guess_case_type(case),
                "description": desc_item.text().strip() if desc_item else "",
            }
        return cases, meta

    def _collect_combinations(self, cases):
        combinations = {}
        meta = {}
        for r in range(self.combo_table.rowCount()):
            item = self.combo_table.item(r, 0)
            name = item.text().strip() if item else ""
            if not name:
                continue
            if name in combinations:
                raise ValueError(f"Duplicate Load Combination: {name}")
            method = self.combo_table.cellWidget(r, 1).currentText()
            factors = {}
            for c, case in enumerate(cases, start=2):
                factor_item = self.combo_table.item(r, c)
                text = factor_item.text().strip() if factor_item else ""
                if not text:
                    continue
                value = float(text)
                if value:
                    factors[case] = value
            combinations[name] = factors
            meta[name] = {"method": method}
        return combinations, meta

    def accept_data(self):
        try:
            cases, case_meta = self._collect_cases()
            combinations, combo_meta = self._collect_combinations(cases)
            self.data = apply_load_case_configuration(
                self.original,
                cases=cases,
                case_metadata=case_meta,
                combinations=combinations,
                combination_meta=combo_meta,
                self_weight=self.self_weight.isChecked(),
                self_weight_case=self.self_weight_case.currentText() or None,
            )
        except Exception as exc:
            self.error.setText(str(exc))
            return
        self.accept()
