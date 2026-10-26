from __future__ import annotations
import copy
import threading
from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QMessageBox, QPushButton, QSpinBox, QToolTip, QVBoxLayout, QWidget,
)
from .client import analyze, SolverCancelled
from .runtime import diagnostic_text, repair_runtime, runtime_status
from .constants import DIAGRAMS, PLUGIN_NAME, VERSION
from .editor import ModelEditor, ResultTableDialog
from .load_manager import LoadCaseCombinationDialog
from .examples import example_names, get_example
from .factory_bridge import (FACTORY_KEY, FactoryImportError, build_analysis_from_factory,
                             members_from_scene, project_stations, required_section_mappings)
from .exporters import export_csv, export_pdf
from .model import fingerprint, validate
from .sections import starter_sections
from .engineering_core import (
    CatalogError, STATUS_NOMINAL, nominal_section_properties,
    section_record, catalog_info,
)
from .factory_reimport import preserve_analysis_edits, ReimportNeedsConfirmation
from .overlay import OverlayRenderer
from .picking import hover_member_data, internal_force_hover, pick_item


class FactorySelectionCancelled(Exception):
    """User cancelled profile choice; not an engineering error."""


class SolverTask(QObject):
    done = Signal(object)
    progress = Signal(str)

    def __init__(self, model, timeout):
        super().__init__()
        self.model = copy.deepcopy(model)
        self.timeout = timeout
        self.cancel_event = threading.Event()

    @Slot()
    def run(self):
        try:
            self.progress.emit("Analyzing with anaStruct 1.7.0…")
            result = analyze(self.model, timeout=self.timeout, cancel=self.cancel_event)
            payload = {"ok": True, "result": result}
        except SolverCancelled as exc:
            payload = {"ok": False, "cancelled": True, "error": str(exc)}
        except Exception as exc:
            payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        self.done.emit(payload)

    def cancel(self):
        self.cancel_event.set()


class RuntimeRepairTask(QObject):
    done = Signal(object)
    progress = Signal(str)

    @Slot()
    def run(self):
        try:
            self.progress.emit("Installing / repairing anaStruct solver runtime…")
            status, output = repair_runtime()
            self.done.emit({"ok": True, "status": status, "output": output})
        except Exception as exc:
            self.done.emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


class Panel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.data = {}
        self.model = None
        self.result = None
        self.revision = 0
        self.result_revision = 0
        self.selected_item = None
        self.thread = None
        self.task = None
        self.repair_thread = None
        self.repair_task = None
        self.running_hash = None
        self.frame_y = 0.0
        self.factory_placement = {}
        self._factory_source_members = []
        self.overlay = OverlayRenderer(self)
        self._build_ui()
        self.refresh()
        self._install_hover_filter()

    def _install_hover_filter(self):
        viewport = getattr(self.app, "viewport", None)
        if viewport is not None:
            viewport.setMouseTracking(True)
            viewport.installEventFilter(self)

    def eventFilter(self, obj, event):
        viewport = getattr(self.app, "viewport", None)
        if obj is viewport and event.type() == QEvent.Type.MouseMove:
            if event.buttons() != Qt.MouseButton.NoButton or not self.result_current() or not self.show_analytical_overlay.isChecked():
                QToolTip.hideText()
                return False
            pos = event.position()
            info = hover_member_data(self.app, self.model, self.result, self.case.currentText(), float(pos.x()), float(pos.y()), frame_y=self.frame_y)
            if info is None:
                QToolTip.hideText()
            else:
                QToolTip.showText(viewport.mapToGlobal(pos.toPoint()), info["label"], viewport)
            return False
        if obj is viewport and event.type() == QEvent.Type.Leave:
            QToolTip.hideText()
        return super().eventFilter(obj, event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        title = QLabel(f"{PLUGIN_NAME}\nv{VERSION}")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")
        root.addWidget(title)

        demo_box = QGroupBox("Model")
        demo_layout = QVBoxLayout(demo_box)
        row = QHBoxLayout()
        self.example_combo = QComboBox()
        self.example_combo.addItems(example_names())
        self.example_button = QPushButton("Load example")
        row.addWidget(self.example_combo, 1); row.addWidget(self.example_button)
        demo_layout.addLayout(row)
        self.edit_button = QPushButton("Edit nodes / members / loads / sections…")
        demo_layout.addWidget(self.edit_button)
        self.load_case_button = QPushButton("Load Cases / Combinations…")
        demo_layout.addWidget(self.load_case_button)
        self.self_weight = QCheckBox("Self-weight")
        self.self_weight_case = QComboBox()
        sw = QHBoxLayout(); sw.addWidget(self.self_weight); sw.addWidget(self.self_weight_case, 1)
        demo_layout.addLayout(sw)
        root.addWidget(demo_box)

        factory_box = QGroupBox("GO Factory 3D integration")
        factory_layout = QVBoxLayout(factory_box)
        self.factory_import_button = QPushButton("Create Analysis from GO Factory")
        self.factory_import_button.setToolTip("Read Column/Rafter metadata from existing 3D factory; never changes 3D solids.")
        factory_layout.addWidget(self.factory_import_button)
        edit_row = QHBoxLayout()
        self.factory_edit_sections = QPushButton("Sections / Materials...")
        self.factory_edit_loads = QPushButton("Point / Line Loads...")
        edit_row.addWidget(self.factory_edit_sections)
        edit_row.addWidget(self.factory_edit_loads)
        factory_layout.addLayout(edit_row)
        edit_row2 = QHBoxLayout()
        self.factory_edit_releases = QPushButton("Member Releases...")
        self.factory_edit_combos = QPushButton("Load Combinations...")
        edit_row2.addWidget(self.factory_edit_releases)
        edit_row2.addWidget(self.factory_edit_combos)
        factory_layout.addLayout(edit_row2)
        project_row = QHBoxLayout()
        project_row.addWidget(QLabel("Project:"))
        self.factory_project_combo = QComboBox()
        self.factory_project_combo.setMinimumWidth(90)
        project_row.addWidget(self.factory_project_combo, 1)
        factory_layout.addLayout(project_row)
        station_row = QHBoxLayout()
        station_row.addWidget(QLabel("Frame station:"))
        self.factory_station_combo = QComboBox()
        station_row.addWidget(self.factory_station_combo, 1)
        factory_layout.addLayout(station_row)
        base_row = QHBoxLayout()
        base_row.addWidget(QLabel("Base restraint (explicit):"))
        self.factory_base_combo = QComboBox()
        self.factory_base_combo.addItems(("Fixed", "Pin"))
        base_row.addWidget(self.factory_base_combo, 1)
        factory_layout.addLayout(base_row)
        visibility_row = QHBoxLayout()
        self.show_analytical_overlay = QCheckBox("Show analytical overlay")
        self.show_analytical_overlay.setChecked(True)
        self.show_alignment_markers = QCheckBox("GO Factory alignment markers")
        visibility_row.addWidget(self.show_analytical_overlay)
        visibility_row.addWidget(self.show_alignment_markers)
        factory_layout.addLayout(visibility_row)
        self.factory_alignment_status = QLabel("Standalone model (Y = 0 m)")
        self.factory_alignment_status.setWordWrap(True)
        factory_layout.addWidget(self.factory_alignment_status)
        root.addWidget(factory_box)

        results = QGroupBox("Analysis / Results")
        rb = QVBoxLayout(results)
        solver_row = QHBoxLayout()
        self.check_solver_button = QPushButton("Check Solver")
        self.repair_solver_button = QPushButton("Install / Repair Solver")
        solver_row.addWidget(self.check_solver_button)
        solver_row.addWidget(self.repair_solver_button, 1)
        rb.addLayout(solver_row)
        self.solver_status = QLabel("Solver: not checked")
        self.solver_status.setWordWrap(True)
        rb.addWidget(self.solver_status)
        self.analysis_state = QLabel("anaStruct: Not analyzed")
        self.analysis_state.setObjectName("go_anastruct_2d_analysis_state")
        self.analysis_state.setToolTip(
            "This status belongs to the GO 2D anaStruct extension. "
            "The GO Structural Workspace may use a different solver and status."
        )
        self.analysis_state.setStyleSheet("font-weight: 600;")
        rb.addWidget(self.analysis_state)
        run_row = QHBoxLayout()
        self.run_button = QPushButton("Run Analysis")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        run_row.addWidget(self.run_button, 1); run_row.addWidget(self.cancel_button)
        rb.addLayout(run_row)
        self.timeout = QDoubleSpinBox(); self.timeout.setRange(30, 3600); self.timeout.setDecimals(0); self.timeout.setValue(180); self.timeout.setPrefix("Time limit: "); self.timeout.setSuffix(" s")
        rb.addWidget(self.timeout)
        rb.addWidget(QLabel("Load case / combination"))
        self.case = QComboBox(); rb.addWidget(self.case)
        rb.addWidget(QLabel("Viewport diagram"))
        self.diagram = QComboBox(); self.diagram.addItems(DIAGRAMS); rb.addWidget(self.diagram)
        self.diagram_scale = QDoubleSpinBox(); self.diagram_scale.setRange(0.05, 20.0); self.diagram_scale.setSingleStep(0.1); self.diagram_scale.setValue(1.0); self.diagram_scale.setPrefix("Diagram scale: ")
        rb.addWidget(self.diagram_scale)
        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Labels / member:"))
        self.label_count = QSpinBox(); self.label_count.setRange(0, 20); self.label_count.setValue(3); self.label_count.setToolTip("Maximum sampled diagram labels per member; collision avoidance may hide crowded labels. Hover preserves every numerical result.")
        label_row.addWidget(self.label_count)
        self.auto_label_layout = QCheckBox("Auto layout")
        self.auto_label_layout.setChecked(True)
        self.auto_label_layout.setToolTip(
            "Avoid overlapping load/diagram/ID labels in screen space; "
            "does not change calculations, values, or results."
        )
        label_row.addWidget(self.auto_label_layout)
        legend = QLabel("+ blue / − red")
        legend.setToolTip("Signed N/V/M diagram area fill")
        label_row.addWidget(legend); label_row.addStretch()
        rb.addLayout(label_row)
        hover_hint = QLabel("Hover a member after analysis to read N / V / M / deflection at that position.")
        hover_hint.setWordWrap(True); rb.addWidget(hover_hint)
        toggles = QHBoxLayout()
        self.show_ids = QCheckBox("IDs"); self.show_ids.setChecked(True)
        self.show_values = QCheckBox("Min / Max"); self.show_values.setChecked(True)
        self.show_diagram_labels = QCheckBox("Diagram labels"); self.show_diagram_labels.setChecked(True)
        toggles.addWidget(self.show_ids); toggles.addWidget(self.show_values); toggles.addWidget(self.show_diagram_labels); toggles.addStretch()
        rb.addLayout(toggles)

        load_box = QGroupBox("Load display")
        load_layout = QVBoxLayout(load_box)
        load_row1 = QHBoxLayout()
        self.show_point_loads = QCheckBox("Point / Moment"); self.show_point_loads.setChecked(True)
        self.show_distributed_loads = QCheckBox("Distributed"); self.show_distributed_loads.setChecked(True)
        load_row1.addWidget(self.show_point_loads); load_row1.addWidget(self.show_distributed_loads); load_row1.addStretch()
        load_layout.addLayout(load_row1)
        load_row2 = QHBoxLayout()
        self.show_self_weight_overlay = QCheckBox("Self-weight"); self.show_self_weight_overlay.setChecked(True)
        self.show_load_labels = QCheckBox("Labels"); self.show_load_labels.setChecked(True)
        self.show_active_load_only = QCheckBox("Active case only"); self.show_active_load_only.setChecked(True)
        load_row2.addWidget(self.show_self_weight_overlay); load_row2.addWidget(self.show_load_labels); load_row2.addWidget(self.show_active_load_only); load_row2.addStretch()
        load_layout.addLayout(load_row2)
        self.load_legend = QLabel("Load legend: —")
        self.load_legend.setWordWrap(True)
        load_layout.addWidget(self.load_legend)
        rb.addWidget(load_box)

        self.selected_label = QLabel("Selection: —")
        self.selected_label.setWordWrap(True)
        rb.addWidget(self.selected_label)
        root.addWidget(results)

        exports = QGroupBox("Tables / Export")
        eb = QVBoxLayout(exports)
        self.table_button = QPushButton("Result tables…")
        self.csv_button = QPushButton("Export CSV…")
        self.pdf_button = QPushButton("Export PDF report — selected case…")
        self.full_pdf_button = QPushButton("Export full PDF — all cases / combinations…")
        eb.addWidget(self.table_button); eb.addWidget(self.csv_button); eb.addWidget(self.pdf_button); eb.addWidget(self.full_pdf_button)
        root.addWidget(exports)

        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addStretch()

        self.example_button.clicked.connect(self.load_selected_example)
        self.factory_import_button.clicked.connect(self.import_factory_frame)
        self.factory_edit_sections.clicked.connect(lambda: self.edit_model_tab("Sections"))
        self.factory_edit_loads.clicked.connect(lambda: self.edit_model_tab("Distributed Loads"))
        self.factory_edit_releases.clicked.connect(lambda: self.edit_model_tab("Members"))
        self.factory_edit_combos.clicked.connect(self.edit_load_cases)
        self.factory_project_combo.currentTextChanged.connect(self.factory_project_changed)
        self.factory_station_combo.currentIndexChanged.connect(self.factory_station_changed)
        self.factory_base_combo.currentTextChanged.connect(self.factory_base_changed)
        self.show_analytical_overlay.toggled.connect(self.update_factory_visibility)
        self.show_alignment_markers.toggled.connect(self.update_factory_visibility)
        self.edit_button.clicked.connect(self.edit_model)
        self.load_case_button.clicked.connect(self.edit_load_cases)
        self.self_weight.toggled.connect(self.update_self_weight)
        self.self_weight_case.currentTextChanged.connect(self.update_self_weight)
        self.check_solver_button.clicked.connect(self.check_solver)
        self.repair_solver_button.clicked.connect(self.repair_solver)
        self.run_button.clicked.connect(self.run_analysis)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.case.currentTextChanged.connect(self.redraw)
        self.case.currentTextChanged.connect(self._refresh_load_legend)
        self.diagram.currentTextChanged.connect(self.redraw)
        self.diagram_scale.valueChanged.connect(self.redraw)
        self.label_count.valueChanged.connect(self.redraw)
        self.auto_label_layout.toggled.connect(self.redraw)
        self.show_ids.toggled.connect(self.redraw)
        self.show_values.toggled.connect(self.redraw)
        self.show_diagram_labels.toggled.connect(self.redraw)
        self.show_point_loads.toggled.connect(self.redraw)
        self.show_distributed_loads.toggled.connect(self.redraw)
        self.show_self_weight_overlay.toggled.connect(self.redraw)
        self.show_load_labels.toggled.connect(self.redraw)
        self.show_active_load_only.toggled.connect(self.redraw)
        self.show_active_load_only.toggled.connect(self._refresh_load_legend)
        self.table_button.clicked.connect(self.show_tables)
        self.csv_button.clicked.connect(self.export_csv_clicked)
        self.pdf_button.clicked.connect(self.export_pdf_clicked)
        self.full_pdf_button.clicked.connect(self.export_full_pdf_clicked)
        initial = runtime_status(probe=False)
        self.solver_status.setText("Solver detected: " + str(initial.get("worker_exe") or initial.get("python")) if initial.get("ready") else "Solver not configured — click Check Solver or Install / Repair Solver")

    def load_selected_example(self):
        name = self.example_combo.currentText()
        if not name:
            return
        self.load_example(name)

    def load_example(self, name):
        """Open standalone example without requiring GO Factory to be installed."""
        self.set_model(get_example(name))
        if name == "11 — Gable Frame from GO Factory":
            placement = {
                "enabled": True, "source": "demo", "project": "Factory 01",
                "frame_y": 0.0, "frame_stations": [float(y) for y in range(0, 37, 6)],
                "markers": [], "alignment_error_m": None, "section_mapping": {},
                "show_overlay": True, "show_markers": False,
            }
        else:
            placement = {}
        self.set_factory_placement(placement)
        self.status.setText(f"Loaded example: {name} — Run Analysis")

    def set_factory_placement(self, placement):
        payload = self.document_payload()
        payload["factory_overlay"] = copy.deepcopy(placement)
        self.app.set_document_data(payload)
        # Host callbacks may be async; always synchronize the view immediately.
        self.refresh()

    def _sync_factory_controls(self):
        placement = self.factory_placement
        # UI must always represent the restraints actually saved in the FEM.
        if self.model:
            bases = {
                row.get("support", "Free")
                for row in self.model.get("nodes", [])
                if row.get("id") in ("N1", "N5")
            }
            if len(bases) == 1 and next(iter(bases)) in ("Fixed", "Pin"):
                self.factory_base_combo.blockSignals(True)
                self.factory_base_combo.setCurrentText(next(iter(bases)))
                self.factory_base_combo.blockSignals(False)

        self.factory_project_combo.blockSignals(True)
        self.factory_project_combo.clear()
        live_projects = project_stations(self._factory_source_members)
        names = list(live_projects) if live_projects else (
            [str(placement["project"])] if placement.get("project") else []
        )
        self.factory_project_combo.addItems(names)
        if placement.get("project") in names:
            self.factory_project_combo.setCurrentText(str(placement["project"]))
        self.factory_project_combo.blockSignals(False)

        self.factory_station_combo.blockSignals(True)
        self.factory_station_combo.clear()
        stations = placement.get("frame_stations", [])
        if not stations and placement:
            stations = [placement.get("frame_y", 0.0)]
        for y in stations:
            self.factory_station_combo.addItem(f"Y = {float(y):g} m", float(y))
        target = float(placement.get("frame_y", 0.0))
        for index in range(self.factory_station_combo.count()):
            if abs(float(self.factory_station_combo.itemData(index)) - target) < 1e-6:
                self.factory_station_combo.setCurrentIndex(index)
                break
        self.factory_station_combo.blockSignals(False)

        self.show_analytical_overlay.blockSignals(True)
        self.show_alignment_markers.blockSignals(True)
        self.show_analytical_overlay.setChecked(bool(placement.get("show_overlay", True)))
        self.show_alignment_markers.setChecked(bool(placement.get("show_markers", False)))
        self.show_analytical_overlay.blockSignals(False)
        self.show_alignment_markers.blockSignals(False)

        if placement.get("source") == FACTORY_KEY:
            error = placement.get("alignment_error_m")
            quality = "centerline metadata aligned" if error is not None and error <= 1e-5 else "centerline mapping needs inspection"
            catalog = ("GO Core catalog checksum matched" if
                       placement.get("factory_metadata_catalog_pinned") else
                       "legacy/unpinned factory metadata — verify profile source")
            text = (f"GO Factory: {placement.get('project')} / Y={target:g} m — "
                    f"{quality}; {catalog}; NOMINAL properties are not design-verified")
        elif placement.get("source") == "demo":
            text = f"Demo Gable Frame / Y={target:g} m (no 3D factory link)"
        else:
            text = "Standalone analysis at Y = 0 m"
        self.factory_alignment_status.setText(text)

    def update_factory_visibility(self, *_):
        placement = dict(self.factory_placement)
        placement["show_overlay"] = self.show_analytical_overlay.isChecked()
        placement["show_markers"] = self.show_alignment_markers.isChecked()
        self.set_factory_placement(placement)

    def _live_factory_rows(self):
        viewport = getattr(self.app, "viewport", None)
        scene = getattr(viewport, "scene", None)
        return members_from_scene(scene)

    def _factory_frame(self, rows, project, y):
        """One review per new mapping set; silent cancel; reuse saved approvals."""
        mapping = copy.deepcopy(self.factory_placement.get("section_mapping", {}))
        # Remember a preview acknowledgement only for the exact same catalog.
        # A new source snapshot requires a fresh section/axis review.
        if self.factory_placement.get("catalog_sha256") != catalog_info()["sha256"]:
            mapping = {}
        needed = required_section_mappings(rows, project, y)
        steel_starters = [
            row["id"] for row in starter_sections() if row.get("kind") == "Steel"
        ]
        pending = []
        for steel_name in needed:
            saved = mapping.get(steel_name)
            if isinstance(saved, dict) and saved.get("acknowledged") is True:
                continue
            try:
                record = section_record(steel_name)
                has_nominal = record["analysis_status"] == STATUS_NOMINAL
            except CatalogError:
                has_nominal = False
            choices = []
            if has_nominal:
                choices.extend((
                    "GO Core nominal / STRONG axis — approximate, unverified",
                    "GO Core nominal / WEAK axis — approximate, unverified",
                ))
            choices.extend(
                f"Manual steel starter: {section_id} — not factory geometry"
                for section_id in steel_starters
            )
            choice, accepted = QInputDialog.getItem(
                self, "GO Steel — Choose analysis section (Preview)",
                f"Factory member: {steel_name}\n"
                "Choose the in-plane bending axis or an explicit steel test section.\n"
                "Nominal dimensions are NOT manufacturer-verified.",
                choices, 0, False,
            )
            if not accepted:
                raise FactorySelectionCancelled()
            if choice.startswith("GO Core nominal"):
                axis = "strong" if "STRONG" in choice else "weak"
                props = nominal_section_properties(
                    steel_name, axis=axis, acknowledge_unverified=True
                )
                mapping[steel_name] = {
                    "mode": "go_core_nominal", "axis": axis,
                    "acknowledged": True,
                }
                pending.append(
                    f"• {steel_name} ({axis} axis): "
                    f"A={props['A_m2']:.7g} m², "
                    f"I={props['Iz_m4']:.8g} m⁴, "
                    f"mass≈{props['nominal_mass_kg_m']:.3f} kg/m"
                )
            else:
                sid = choice.split(" — ", 1)[0].removeprefix("Manual steel starter: ")
                mapping[steel_name] = {
                    "mode": "manual_starter", "section": sid,
                    "acknowledged": True,
                }
                pending.append(f"• {steel_name}: manual substitute {sid} (NOT equivalent)")
        if pending:
            summary = (
                "Confirm ALL new section mappings for this project:\n\n"
                + "\n".join(pending) + "\n\n"
                "Nominal/mapped properties have NOT been verified with a "
                "manufacturer. Connections, E, density and load definitions "
                "still require engineering review.\n\n"
                "Accept these mappings for PREVIEW testing only?\n"
                "Your choices will be remembered in this model; selecting "
                "the same sections/axes will not show this confirmation again."
            )
            confirmation = QMessageBox.question(
                self, "GO Steel — Preview section review",
                summary,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                raise FactorySelectionCancelled()

        model, placement = build_analysis_from_factory(
            rows, project, y, section_mapping=mapping,
            support=self.factory_base_combo.currentText(),
        )
        placement["show_overlay"] = self.show_analytical_overlay.isChecked()
        placement["show_markers"] = self.show_alignment_markers.isChecked()
        return model, placement

    def factory_base_changed(self, support):
        """Fixed/Pin change must invalidate the current FEM; no UI-only change."""
        if (not self.model or self.thread is not None or
                self.factory_placement.get("source") != FACTORY_KEY or
                support not in ("Fixed", "Pin")):
            return
        changed = copy.deepcopy(self.model)
        for node in changed["nodes"]:
            if node["id"] in ("N1", "N5"):
                node["support"] = support
        if fingerprint(changed) != fingerprint(self.model):
            self.set_model(changed)
            self.status.setText(
                f"Base restraints changed to {support} — results stale. Run Analysis again."
            )

    def _keep_factory_analysis_edits(self, imported, placement):
        """Never silently discard manually edited loads/combos/releases on re-import."""
        if (self.model is None or
                self.factory_placement.get("source") != FACTORY_KEY or
                self.factory_placement.get("project") != placement.get("project")):
            return imported
        unchanged_mapping = (
            self.factory_placement.get("section_mapping", {}) ==
            placement.get("section_mapping", {})
        )
        try:
            return preserve_analysis_edits(
                self.model, imported, retain_sections=unchanged_mapping
            )
        except ReimportNeedsConfirmation as exc:
            result = QMessageBox.question(
                self, "GO Factory geometry changed",
                f"{exc}\n\n"
                "The existing analytical loads, combinations and releases "
                "cannot safely be remapped to the changed geometry.\n\n"
                "Discard them and import the NEW demonstration model? "
                "Choose No to keep your edited analysis unchanged.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                raise FactoryImportError("Re-import cancelled; existing analysis preserved")
            return imported

    def import_factory_frame(self):
        """Read existing scene metadata; never edit GO Factory 3D objects."""
        try:
            rows = self._live_factory_rows()
            projects = project_stations(rows)
            if not projects:
                raise FactoryImportError(
                    "No GO Factory Column/Rafter metadata in this scene. "
                    "Create a Gable Portal Frame with GO Factory Generator first; "
                    "or load Example 11 for a standalone demonstration."
                )
            names = list(projects)
            project = self.factory_project_combo.currentText()
            if project not in projects:
                project = names[0]
            if len(names) > 1 and not self.factory_project_combo.currentText():
                chosen, accepted = QInputDialog.getItem(
                    self, "Select GO Factory project", "Factory project:",
                    names, names.index(project), False,
                )
                if not accepted:
                    return
                project = chosen
            stations = projects[project]
            selected_y = self.factory_station_combo.currentData()
            previous_station = selected_y if selected_y is not None else self.factory_placement.get("frame_y")
            y = float(previous_station) if previous_station is not None and any(
                abs(float(previous_station) - station) < 1e-6 for station in stations
            ) else float(stations[0])
            model, placement = self._factory_frame(rows, project, y)
            model = self._keep_factory_analysis_edits(model, placement)
            self._factory_source_members = rows
            self.set_model(model)
            self.set_factory_placement(placement)
            self.status.setText(
                f"GO Factory '{project}', Y={y:g} m imported; "
                "review demo loads and mapped sections, then Run Analysis."
            )
        except FactorySelectionCancelled:
            self.status.setText("Factory section selection cancelled; model unchanged")
            return
        except (FactoryImportError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "GO Factory — Analysis import", str(exc))
            self.status.setText(str(exc))

    def factory_project_changed(self, project):
        """Update station choices; never silently overwrite the current FEM."""
        projects = project_stations(self._factory_source_members)
        if project not in projects:
            return
        self.factory_station_combo.blockSignals(True)
        self.factory_station_combo.clear()
        for station in projects[project]:
            self.factory_station_combo.addItem(f"Y = {station:g} m", station)
        self.factory_station_combo.blockSignals(False)
        self.factory_alignment_status.setText(
            f"Selected '{project}' — choose frame Y and click Create Analysis from GO Factory."
        )

    def factory_station_changed(self, index):
        if index < 0 or not self.factory_placement:
            return
        y = self.factory_station_combo.itemData(index)
        if y is None or abs(float(y) - self.frame_y) < 1e-6:
            return
        placement = dict(self.factory_placement)
        if placement.get("source") == FACTORY_KEY:
            try:
                rows = self._live_factory_rows()
                model, updated = self._factory_frame(
                    rows, placement.get("project", ""), float(y)
                )
                model = self._keep_factory_analysis_edits(model, updated)
                if self.model is None or fingerprint(model) != fingerprint(self.model):
                    self.set_model(model)  # Only real FEM changes invalidate results.
                updated["show_overlay"] = placement.get("show_overlay", True)
                updated["show_markers"] = placement.get("show_markers", False)
                placement = updated
            except FactorySelectionCancelled:
                self._sync_factory_controls()
                return
            except (FactoryImportError, ValueError) as exc:
                QMessageBox.warning(self, "GO Factory frame station", str(exc))
                self._sync_factory_controls()
                return
        else:
            # Same standalone FEM geometry, only move the viewport overlay.
            placement["frame_y"] = float(y)
        self.set_factory_placement(placement)

    def check_solver(self):
        status = runtime_status(probe=True)
        self.solver_status.setText(diagnostic_text(status))
        if status.get("ready"):
            self.status.setText("anaStruct solver runtime is ready")
        else:
            self.status.setText("Solver not ready — use Install / Repair Solver")
        return status

    def repair_solver(self):
        if self.repair_thread is not None or self.thread is not None:
            return
        self.repair_solver_button.setEnabled(False)
        self.check_solver_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.solver_status.setText("Installing anaStruct 1.7.0 and NumPy in isolated runtime…")
        self.repair_thread = QThread(self)
        self.repair_task = RuntimeRepairTask()
        self.repair_task.moveToThread(self.repair_thread)
        self.repair_thread.started.connect(self.repair_task.run)
        self.repair_task.progress.connect(self.status.setText, Qt.ConnectionType.QueuedConnection)
        self.repair_task.done.connect(self.repair_done, Qt.ConnectionType.QueuedConnection)
        self.repair_task.done.connect(self.repair_thread.quit)
        self.repair_thread.finished.connect(self.repair_thread_finished)
        self.repair_thread.start()

    @Slot(object)
    def repair_done(self, payload):
        if payload.get("ok"):
            status = payload.get("status") or runtime_status(probe=True)
            self.solver_status.setText(diagnostic_text(status))
            self.status.setText("Solver installation / repair complete")
        else:
            error = payload.get("error", "Solver repair failed")
            self.solver_status.setText(error)
            self.status.setText(error)

    @Slot()
    def repair_thread_finished(self):
        if self.repair_task is not None:
            self.repair_task.deleteLater()
        if self.repair_thread is not None:
            self.repair_thread.deleteLater()
        self.repair_task = None
        self.repair_thread = None
        self.repair_solver_button.setEnabled(True)
        self.check_solver_button.setEnabled(True)
        self._sync_controls()

    def document_payload(self):
        return copy.deepcopy(self.app.document_data(default={}) or {})

    def result_current(self):
        if not self.model or not self.result:
            return False
        try:
            return self.result.get("model_hash") == fingerprint(self.model)
        except Exception:
            return False

    def refresh(self):
        payload = self.document_payload()
        old_model = self.model
        old_result = self.result
        self.data = payload
        self.model = payload.get("model")
        self.result = payload.get("result")
        if self.model != old_model:
            self.revision += 1
        if self.result != old_result:
            self.result_revision += 1
        self.factory_placement = payload.get('factory_overlay') or {}
        self.frame_y = float(self.factory_placement.get('frame_y', 0.0))
        self.overlay.invalidate()
        self._sync_controls()
        self._sync_factory_controls()
        self._refresh_load_legend()
        self.redraw()

    def _sync_controls(self):
        cases = []
        if self.model:
            cases = list(self.model.get("cases", [])) + list(self.model.get("combinations", {}))
        if self.result_current():
            cases = list(self.result.get("cases", {}))
        current = self.case.currentText()
        self.case.blockSignals(True); self.case.clear(); self.case.addItems(cases)
        if current in cases: self.case.setCurrentText(current)
        self.case.blockSignals(False)
        self.self_weight.blockSignals(True)
        self.self_weight.setChecked(bool((self.model or {}).get("self_weight", False)))
        self.self_weight.blockSignals(False)
        self.self_weight_case.blockSignals(True); self.self_weight_case.clear(); self.self_weight_case.addItems((self.model or {}).get("cases", []))
        if self.model and self.model.get("self_weight_case") in self.model.get("cases", []): self.self_weight_case.setCurrentText(self.model["self_weight_case"])
        self.self_weight_case.blockSignals(False)
        has_model = bool(self.model)
        current_result = self.result_current()
        idle = self.thread is None and self.repair_thread is None
        self.run_button.setEnabled(has_model and idle)
        self.edit_button.setEnabled(has_model and idle)
        self.load_case_button.setEnabled(has_model and idle)
        self.repair_solver_button.setEnabled(idle)
        self.check_solver_button.setEnabled(idle)
        self.table_button.setEnabled(current_result)
        self.csv_button.setEnabled(current_result)
        self.pdf_button.setEnabled(current_result)
        self.full_pdf_button.setEnabled(current_result)
        if self.thread is not None:
            self.analysis_state.setText("anaStruct: Analyzing…")
        elif not has_model:
            self.analysis_state.setText("anaStruct: No model")
        elif current_result:
            self.analysis_state.setText("anaStruct: Analyzed (current)")
        elif self.result:
            self.analysis_state.setText("anaStruct: Results stale")
        else:
            self.analysis_state.setText("anaStruct: Not analyzed")
        if not has_model:
            self.status.setText("Load Beam demo / Portal demo, or create a model.")
        elif current_result:
            self.status.setText(f"Current results — {self.result.get('solver')} {self.result.get('solver_version')}")
        elif self.result:
            self.status.setText("Results are stale — Run Analysis again.")

    def _load_legend_html(self):
        if not self.model:
            return "Load legend: —"
        entries = self.overlay.case_legend_entries(
            self.model,
            selected_case=self.case.currentText(),
            active_only=self.show_active_load_only.isChecked(),
        )
        if not entries:
            return "Load legend: —"
        selected = self.case.currentText()
        parts = []
        for entry in entries:
            dot = f'<span style="color:{entry["color"]}; font-size:14px;">&#9679;</span>'
            label = f'{entry["name"]} — {entry["label"]}'
            factor = float(entry.get("factor", 1.0))
            if abs(factor - 1.0) > 1e-12:
                label += f' × {factor:.3g}'
            if entry.get("description"):
                label += f' ({entry["description"]})'
            if selected and selected == entry["name"]:
                label = f'<b>{label}</b>'
            parts.append(f'{dot} {label}')
        mode = "showing only active case / combination" if self.show_active_load_only.isChecked() else "showing all base load cases"
        return "Load legend:<br>" + "<br>".join(parts) + f'<br><i>{mode}</i>'

    def _refresh_load_legend(self, *_):
        if hasattr(self, "load_legend"):
            self.load_legend.setText(self._load_legend_html())

    def set_model(self, model):
        checked = validate(model)
        payload = self.document_payload()
        payload.update(version=VERSION, model=checked)
        self.app.set_document_data(payload)

    def edit_model(self):
        if not self.model:
            self.set_model(beam_demo()); return
        dialog = ModelEditor(self.model, self)
        if dialog.exec():
            self.set_model(dialog.data)


    def edit_model_tab(self, title):
        """Open the existing authoritative model editor on the requested tab."""
        if not self.model:
            QMessageBox.information(
                self, "No analysis model",
                "Load a Gable example or import GO Factory first."
            )
            return
        dialog = ModelEditor(self.model, self)
        for idx in range(dialog.tabs.count()):
            if dialog.tabs.tabText(idx).lower() == title.lower():
                dialog.tabs.setCurrentIndex(idx)
                break
        if dialog.exec():
            self.set_model(dialog.data)
            self.status.setText(
                f"{title} updated — analytical results are stale. Re-run Analysis."
            )

    def edit_load_cases(self):
        if not self.model:
            self.set_model(beam_demo())
            return
        dialog = LoadCaseCombinationDialog(self.model, self)
        if dialog.exec():
            self.set_model(dialog.data)
            self.status.setText("Load Cases / Combinations updated — Run Analysis again")

    def update_self_weight(self, *_):
        if not self.model or self.thread is not None:
            return
        model = copy.deepcopy(self.model)
        model["self_weight"] = self.self_weight.isChecked()
        if self.self_weight_case.currentText():
            model["self_weight_case"] = self.self_weight_case.currentText()
        try:
            self.set_model(model)
        except Exception as exc:
            self.status.setText(str(exc))

    def run_analysis(self):
        if self.thread is not None or self.repair_thread is not None or not self.model:
            return
        solver = runtime_status(probe=True)
        self.solver_status.setText(diagnostic_text(solver))
        if not solver.get("ready"):
            self.status.setText("anaStruct solver is not ready — click Install / Repair Solver")
            return
        try:
            model = validate(self.model)
            self.running_hash = fingerprint(model)
        except Exception as exc:
            self.status.setText(str(exc)); return
        self.run_button.setEnabled(False); self.cancel_button.setEnabled(True); self.edit_button.setEnabled(False)
        self.analysis_state.setText("anaStruct: Analyzing…")
        self.thread = QThread(self)
        self.task = SolverTask(model, float(self.timeout.value()))
        self.task.moveToThread(self.thread)
        self.thread.started.connect(self.task.run)
        self.task.progress.connect(self.status.setText, Qt.ConnectionType.QueuedConnection)
        self.task.done.connect(self.analysis_done, Qt.ConnectionType.QueuedConnection)
        self.task.done.connect(self.thread.quit)
        self.thread.finished.connect(self.thread_finished)
        self.thread.start()

    def cancel_analysis(self):
        if self.task:
            self.task.cancel(); self.cancel_button.setEnabled(False); self.status.setText("Cancelling…")

    @Slot(object)
    def analysis_done(self, payload):
        if payload.get("cancelled"):
            self.status.setText("Analysis cancelled")
            self.analysis_state.setText("anaStruct: Cancelled")
            return
        if not payload.get("ok"):
            self.status.setText(payload.get("error", "Analysis failed"))
            self.analysis_state.setText("anaStruct: Failed (see status)")
            return
        try:
            if not self.model or fingerprint(self.model) != self.running_hash:
                self.status.setText("Model changed; solver result discarded")
                return
        except Exception:
            self.status.setText("Model changed; solver result discarded")
            return
        result = payload["result"]
        result["model_hash"] = self.running_hash
        data = self.document_payload(); data["result"] = result; data["version"] = VERSION
        self.app.set_document_data(data)
        solved = list(result.get("cases", {}))
        self.analysis_state.setText("anaStruct: Analyzed (current)")
        self.status.setText("Analysis complete — " + ", ".join(solved) if solved else "Analysis complete")

    @Slot()
    def thread_finished(self):
        if self.task is not None: self.task.deleteLater()
        if self.thread is not None: self.thread.deleteLater()
        self.task = None; self.thread = None; self.running_hash = None
        self.cancel_button.setEnabled(False)
        self._sync_controls()

    def redraw(self, *_):
        self.overlay.invalidate()
        if getattr(self.app, "viewport", None) is not None:
            self.app.viewport.update()

    def pick(self, viewport, px, py):
        if not self.show_analytical_overlay.isChecked():
            return None
        return pick_item(self.app, self.model, px, py, frame_y=self.frame_y)

    def snap_internal(self, viewport, snap, px, py):
        if not self.result_current() or not self.show_analytical_overlay.isChecked():
            return None
        return internal_force_hover(self.app, self.model, self.result, self.case.currentText(), px, py, frame_y=self.frame_y)

    def selected(self, item):
        self.selected_item = item
        if not item:
            self.selected_label.setText("Selection: —")
        elif item.startswith("member:") and self.model:
            mid = item.split(":", 1)[1]
            row = next((m for m in self.model["members"] if m["id"] == mid), None)
            if row:
                text = f"Member {mid} · {row['i']} → {row['j']} · {row['type']} · {row['section']}"
                if self.result_current() and self.case.currentText() in self.result["cases"]:
                    mr = self.result["cases"][self.case.currentText()]["members"].get(mid)
                    if mr:
                        text += f"\nL={mr['L']:.4g} m · Mmax={mr['extrema']['M']['max']['value']:.4g} kN.m"
                self.selected_label.setText(text)
        else:
            self.selected_label.setText("Selection: " + item)
        self.redraw()

    def delete_item(self, item):
        if not self.model or not item:
            return
        model = copy.deepcopy(self.model)
        kind, ident = item.split(":", 1)
        if kind == "member":
            model["members"] = [m for m in model["members"] if m["id"] != ident]
            model["point_loads"] = [p for p in model.get("point_loads", []) if p.get("member") != ident]
            model["distributed_loads"] = [p for p in model.get("distributed_loads", []) if p.get("member") != ident]
        elif kind == "node":
            if any(ident in (m["i"], m["j"]) for m in model["members"]):
                self.status.setText("Cannot delete a node while members are connected to it")
                return
            model["nodes"] = [n for n in model["nodes"] if n["id"] != ident]
            model["point_loads"] = [p for p in model.get("point_loads", []) if p.get("node") != ident]
        try:
            self.set_model(model)
            self.selected_item = None
            self.app.release_pick()
        except Exception as exc:
            self.status.setText(str(exc))

    def _current_case(self):
        case = self.case.currentText()
        if not self.result_current() or case not in self.result.get("cases", {}):
            raise ValueError("Run Analysis and select a current result case first")
        return case

    def show_tables(self):
        try:
            case = self._current_case()
        except Exception as exc:
            self.status.setText(str(exc)); return
        ResultTableDialog(self.model, self.result, case, self).exec()

    def export_csv_clicked(self):
        try:
            case = self._current_case()
        except Exception as exc:
            self.status.setText(str(exc)); return
        directory = QFileDialog.getExistingDirectory(self, "Export result CSV files")
        if not directory: return
        try:
            files = export_csv(directory, self.model, self.result, case)
            self.status.setText(f"Exported {len(files)} CSV files")
        except Exception as exc:
            QMessageBox.critical(self, "CSV export failed", str(exc))

    def _capture_viewport_image(self):
        viewport = getattr(self.app, "viewport", None)
        if viewport is None:
            return None
        try:
            if hasattr(viewport, "grabFramebuffer"):
                image = viewport.grabFramebuffer()
                if image is not None and not image.isNull():
                    return image
        except Exception:
            pass
        try:
            pixmap = viewport.grab()
            image = pixmap.toImage()
            if image is not None and not image.isNull():
                return image
        except Exception:
            pass
        return None

    def _pdf_viewport_options(self):
        return {
            "case": self.case.currentText(),
            "diagram": self.diagram.currentText(),
            "active_only": self.show_active_load_only.isChecked(),
            "show_point_loads": self.show_point_loads.isChecked(),
            "show_distributed_loads": self.show_distributed_loads.isChecked(),
            "show_self_weight": self.show_self_weight_overlay.isChecked(),
            "show_load_labels": self.show_load_labels.isChecked(),
            "show_diagram_labels": self.show_diagram_labels.isChecked(),
        }

    def export_pdf_clicked(self):
        try:
            case = self._current_case()
        except Exception as exc:
            self.status.setText(str(exc)); return
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF report", f"GO_2D_{case}.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            export_pdf(
                path, self.model, self.result, case,
                viewport_image=self._capture_viewport_image(),
                viewport_options=self._pdf_viewport_options(),
            )
            self.status.setText("PDF report exported")
        except Exception as exc:
            QMessageBox.critical(self, "PDF export failed", str(exc))

    def export_full_pdf_clicked(self):
        if not self.result_current():
            self.status.setText("Run Analysis before exporting the full report")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export full PDF report", "GO_2D_All_Cases.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            export_pdf(
                path, self.model, self.result, None,
                viewport_image=self._capture_viewport_image(),
                viewport_options=self._pdf_viewport_options(),
            )
            self.status.setText("Full PDF report exported — all cases / combinations")
        except Exception as exc:
            QMessageBox.critical(self, "PDF export failed", str(exc))

