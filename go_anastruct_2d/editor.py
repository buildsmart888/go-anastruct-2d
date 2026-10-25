from __future__ import annotations
import copy
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from .model import validate
from .load_manager import LoadCaseCombinationDialog
from .sections import starter_sections

FIELDS = {
    "nodes": ["id", "x", "z", "support", "springs"],
    "members": ["id", "i", "j", "type", "material", "section", "release_i", "release_j"],
    "materials": ["id", "E", "rho"],
    "sections": ["id", "A", "Iz", "kind"],
    "point_loads": ["node", "member", "direction", "value", "x", "case"],
    "distributed_loads": ["member", "direction", "w1", "w2", "x1", "x2", "case"],
}
NUMERIC = {"x", "z", "E", "rho", "A", "Iz", "value", "w1", "w2", "x1", "x2"}
BOOLS = {"release_i", "release_j"}
JSON_FIELDS = {"springs"}


class ModelEditor(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GO 2D Structural model — m, kN")
        self.resize(980, 680)
        self.data = copy.deepcopy(model)
        self.tables = {}
        root = QVBoxLayout(self)
        note = QLabel("XZ plane · +Z up · E [kN/m²] · A [m²] · Iz [m⁴] · rho [kN/m³] · springs JSON e.g. {\"UZ\":10000}")
        note.setWordWrap(True)
        root.addWidget(note)
        tabs = QTabWidget()
        self.tabs = tabs
        root.addWidget(tabs, 1)
        for key, fields in FIELDS.items():
            page = QWidget()
            box = QVBoxLayout(page)
            table = QTableWidget(0, len(fields))
            table.setHorizontalHeaderLabels(fields)
            self.tables[key] = table
            box.addWidget(table, 1)
            controls = QHBoxLayout()
            add = QPushButton("Add")
            duplicate = QPushButton("Duplicate")
            copy_btn = QPushButton("Copy")
            paste_btn = QPushButton("Paste")
            remove = QPushButton("Delete")
            for button in (add, duplicate, copy_btn, paste_btn, remove):
                controls.addWidget(button)
            controls.addStretch()
            box.addLayout(controls)
            add.clicked.connect(lambda _=False, k=key: self.add_row(k, {}))
            duplicate.clicked.connect(lambda _=False, k=key, t=table: self.duplicate_selected(k, t))
            copy_btn.clicked.connect(lambda _=False, t=table: self.copy_selected(t))
            paste_btn.clicked.connect(lambda _=False, k=key, t=table: self.paste_rows(k, t))
            remove.clicked.connect(lambda _=False, t=table: self.remove_selected(t))
            table.setToolTip("Double-click a cell to edit. Copy/Paste uses tab-separated rows compatible with Excel / Google Sheets.")
            for row in self.data.get(key, []):
                self.add_row(key, row)
            tabs.addTab(page, key.replace("_", " ").title())
        section_tools = QHBoxLayout()
        add_sections = QPushButton("Add starter RC / RHS sections")
        add_sections.clicked.connect(self.add_starter_sections)
        section_tools.addWidget(add_sections)
        section_tools.addStretch()
        root.addLayout(section_tools)
        load_case_tools = QHBoxLayout()
        self.load_case_button = QPushButton("Load Cases / Combinations…")
        self.load_case_summary = QLabel()
        self.load_case_summary.setWordWrap(True)
        load_case_tools.addWidget(self.load_case_button)
        load_case_tools.addWidget(self.load_case_summary, 1)
        root.addLayout(load_case_tools)
        self.load_case_button.clicked.connect(self.edit_load_cases)
        self._update_load_case_summary()
        self.error = QLabel()
        self.error.setWordWrap(True)
        root.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_model)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def add_row(self, key, row):
        table = self.tables[key]
        i = table.rowCount()
        table.insertRow(i)
        for j, field in enumerate(FIELDS[key]):
            value = row.get(field, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, separators=(",", ":"))
            table.setItem(i, j, QTableWidgetItem(str(value) if value != "" else ""))

    def _selected_rows(self, table):
        rows = sorted({index.row() for index in table.selectedIndexes()})
        if not rows and table.currentRow() >= 0:
            rows = [table.currentRow()]
        return rows

    def copy_selected(self, table):
        rows = self._selected_rows(table)
        if not rows:
            return
        lines = []
        for r in rows:
            values = []
            for c in range(table.columnCount()):
                item = table.item(r, c)
                values.append(item.text() if item else "")
            lines.append("\t".join(values))
        QApplication.clipboard().setText("\n".join(lines))

    def duplicate_selected(self, key, table):
        rows = self._selected_rows(table)
        existing_ids = {
            (table.item(i, 0).text().strip() if table.item(i, 0) else "")
            for i in range(table.rowCount())
        } if FIELDS[key] and FIELDS[key][0] == "id" else set()
        for r in rows:
            row = {}
            for c, field in enumerate(FIELDS[key]):
                item = table.item(r, c)
                text = item.text().strip() if item else ""
                if text:
                    row[field] = text
            if "id" in row:
                base = row["id"] + "_copy"
                candidate = base
                n = 2
                while candidate in existing_ids:
                    candidate = f"{base}{n}"; n += 1
                row["id"] = candidate
                existing_ids.add(candidate)
            self.add_row(key, row)

    def paste_rows(self, key, table):
        text = QApplication.clipboard().text().strip("\r\n")
        if not text:
            return
        start = table.currentRow()
        if start < 0:
            start = table.rowCount()
        rows = [line.split("\t") for line in text.replace("\r\n", "\n").split("\n") if line.strip()]
        for offset, values in enumerate(rows):
            target = start + offset
            if target >= table.rowCount():
                table.insertRow(target)
            for c in range(min(len(values), len(FIELDS[key]))):
                table.setItem(target, c, QTableWidgetItem(values[c]))

    def remove_selected(self, table):
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)

    def add_starter_sections(self):
        existing = {self.tables["sections"].item(i, 0).text().strip() for i in range(self.tables["sections"].rowCount()) if self.tables["sections"].item(i, 0)}
        for row in starter_sections():
            if row["id"] not in existing:
                self.add_row("sections", row)

    def _update_load_case_summary(self):
        cases = ", ".join(self.data.get("cases", [])) or "—"
        combinations = ", ".join((self.data.get("combinations", {}) or {}).keys()) or "—"
        sw = "OFF"
        if self.data.get("self_weight"):
            sw = "ON → " + str(self.data.get("self_weight_case") or "—")
        self.load_case_summary.setText(f"Cases: {cases}  ·  Combinations: {combinations}  ·  Self-weight: {sw}")

    def edit_load_cases(self):
        try:
            base = self._collect_tables_only()
        except Exception as exc:
            self.error.setText(str(exc))
            return
        dialog = LoadCaseCombinationDialog(base, self)
        if dialog.exec():
            self.data = dialog.data
            self._update_load_case_summary()

    def _collect_tables_only(self):
        out = copy.deepcopy(self.data)
        for key, fields in FIELDS.items():
            rows = []
            table = self.tables[key]
            for i in range(table.rowCount()):
                row = {}
                for j, field in enumerate(fields):
                    item = table.item(i, j)
                    text = item.text().strip() if item else ""
                    if not text:
                        continue
                    if field in NUMERIC:
                        row[field] = float(text)
                    elif field in BOOLS:
                        row[field] = text.lower() in ("1", "true", "yes", "y")
                    elif field in JSON_FIELDS:
                        row[field] = json.loads(text)
                    else:
                        row[field] = text
                if row:
                    rows.append(row)
            out[key] = rows
        return out

    def _collect(self):
        out = copy.deepcopy(self.data)
        for key, fields in FIELDS.items():
            rows = []
            table = self.tables[key]
            for i in range(table.rowCount()):
                row = {}
                for j, field in enumerate(fields):
                    item = table.item(i, j)
                    text = item.text().strip() if item else ""
                    if not text:
                        continue
                    if field in NUMERIC:
                        row[field] = float(text)
                    elif field in BOOLS:
                        row[field] = text.lower() in ("1", "true", "yes", "y")
                    elif field in JSON_FIELDS:
                        row[field] = json.loads(text)
                    else:
                        row[field] = text
                if row:
                    rows.append(row)
            out[key] = rows
        out["cases"] = copy.deepcopy(self.data.get("cases", []))
        out["case_metadata"] = copy.deepcopy(self.data.get("case_metadata", {}))
        out["combinations"] = copy.deepcopy(self.data.get("combinations", {}))
        out["combination_metadata"] = copy.deepcopy(self.data.get("combination_metadata", {}))
        out["self_weight"] = bool(self.data.get("self_weight", False))
        out["self_weight_case"] = self.data.get("self_weight_case")
        out.setdefault("schema", 1)
        out.setdefault("version", 4)
        return validate(out)

    def accept_model(self):
        try:
            self.data = self._collect()
        except Exception as exc:
            self.error.setText(str(exc))
            return
        self.accept()


class ResultTableDialog(QDialog):
    def __init__(self, model, result, case, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GO 2D Structural results — " + case)
        self.resize(920, 600)
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs, 1)
        nodes = QTableWidget(0, 7)
        nodes.setHorizontalHeaderLabels(["Node", "UX", "UZ", "Rot", "RX", "RZ", "MY"])
        for nid, row in result["cases"][case]["nodes"].items():
            i = nodes.rowCount(); nodes.insertRow(i)
            values = [nid, row["ux"], row["uz"], row["rotation"], row["Rx"], row["Rz"], row["My"]]
            for j, value in enumerate(values): nodes.setItem(i, j, QTableWidgetItem(f"{value:.8g}" if isinstance(value, float) else str(value)))
        tabs.addTab(nodes, "Nodes / Reactions")
        members = QTableWidget(0, 8)
        members.setHorizontalHeaderLabels(["Member", "Quantity", "Type", "Value", "x", "Side", "Unit", "L"])
        units = {"N": "kN", "V": "kN", "M": "kN.m", "d": "m"}
        for mid, member in result["cases"][case]["members"].items():
            for quantity, extrema in member["extrema"].items():
                for kind, row in extrema.items():
                    i = members.rowCount(); members.insertRow(i)
                    values = [mid, quantity, kind, row["value"], row["x"], row["side"], units[quantity], member["L"]]
                    for j, value in enumerate(values): members.setItem(i, j, QTableWidgetItem(f"{value:.8g}" if isinstance(value, float) else str(value)))
        tabs.addTab(members, "Member extrema")
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject); close.accepted.connect(self.accept)
        root.addWidget(close)
