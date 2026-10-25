from __future__ import annotations
import math
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen, QBrush, QPainterPath, QPolygonF
from .diagram_utils import sample_plot, signed_interval_parts


class OverlayRenderer:
    """Native IngeTrazo 2D overlay.

    Engineering/result geometry is cached in world coordinates. Camera motion only
    projects cached points and paints them; it never runs anaStruct or rebuilds meshes.
    """

    def __init__(self, panel):
        self.panel = panel
        self._key = None
        self._cache = None

    def invalidate(self):
        self._key = None
        self._cache = None

    def _span(self, model):
        xs = [n["x"] for n in model["nodes"]]
        zs = [n["z"] for n in model["nodes"]]
        return max(max(xs) - min(xs), max(zs) - min(zs), 1.0)

    def _world_point(self, member, nodes, x):
        a, b = nodes[member["i"]], nodes[member["j"]]
        length = math.hypot(b["x"] - a["x"], b["z"] - a["z"])
        t = 0.0 if length == 0 else x / length
        return np.array([a["x"] + (b["x"] - a["x"]) * t, 0.0, a["z"] + (b["z"] - a["z"]) * t], dtype=float)

    def _normal(self, member, nodes):
        a, b = nodes[member["i"]], nodes[member["j"]]
        dx, dz = b["x"] - a["x"], b["z"] - a["z"]
        length = math.hypot(dx, dz)
        return np.array([-dz / length, 0.0, dx / length], dtype=float)

    def _case_factor(self, model, selected_case, load_case):
        if not selected_case:
            return 1.0
        if selected_case in model.get("cases", []):
            return 1.0 if selected_case == load_case else 0.0
        return float((model.get("combinations", {}).get(selected_case, {}) or {}).get(load_case, 0.0))

    @staticmethod
    def _factor_tag(factor, case):
        if abs(factor - 1.0) < 1e-12:
            return f"[{case}]"
        return f"[{factor:.3g}×{case}]"

    def _case_color(self, model, case_name, *, self_weight=False):
        metadata = (model.get("case_metadata", {}) or {}).get(case_name, {})
        load_type = str(metadata.get("type", "")).strip().lower()
        name = str(case_name or "").strip().upper()
        if self_weight:
            return "#6b7280"
        if load_type == "dead" or name.startswith("DL") or name in ("SW", "G"):
            return "#6b7280"
        if load_type == "live" or name.startswith("LL") or name.startswith("L"):
            return "#2563eb"
        if load_type == "wind" or name.startswith("WL") or name.startswith("W"):
            return "#16a34a"
        if load_type in ("seismic", "earthquake") or name.startswith("EQ"):
            return "#dc2626"
        if load_type in ("thermal", "temperature") or name.startswith("TEMP") or name.startswith("T"):
            return "#9333ea"
        palette = ["#0f766e", "#b45309", "#7c3aed", "#be123c", "#0369a1", "#15803d"]
        return palette[sum(ord(ch) for ch in name) % len(palette)]

    def _show_point_loads(self):
        return bool(getattr(getattr(self.panel, "show_point_loads", None), "isChecked", lambda: True)())

    def _show_distributed_loads(self):
        return bool(getattr(getattr(self.panel, "show_distributed_loads", None), "isChecked", lambda: True)())

    def _show_self_weight(self):
        return bool(getattr(getattr(self.panel, "show_self_weight_overlay", None), "isChecked", lambda: True)())

    def _show_load_labels(self):
        return bool(getattr(getattr(self.panel, "show_load_labels", None), "isChecked", lambda: True)())

    def _show_active_load_only(self):
        return bool(getattr(getattr(self.panel, "show_active_load_only", None), "isChecked", lambda: True)())

    def _show_diagram_labels(self):
        return bool(getattr(getattr(self.panel, "show_diagram_labels", None), "isChecked", lambda: True)())

    def _display_factor(self, model, selected_case, load_case):
        if self._show_active_load_only():
            return self._case_factor(model, selected_case, load_case)
        return 1.0

    def case_legend_entries(self, model, selected_case=None, active_only=None):
        if not model:
            return []
        if active_only is None:
            active_only = self._show_active_load_only()
        if selected_case is None:
            selected_case = self.panel.case.currentText() if hasattr(self.panel, "case") else ""

        if active_only:
            if selected_case in model.get("cases", []):
                visible = {selected_case: 1.0}
            else:
                visible = {
                    name: float(factor)
                    for name, factor in (model.get("combinations", {}).get(selected_case, {}) or {}).items()
                    if abs(float(factor)) > 1e-14
                }
        else:
            visible = {name: 1.0 for name in model.get("cases", [])}

        visible_load_cases = set()
        if self._show_point_loads():
            visible_load_cases.update(row.get("case") for row in model.get("point_loads", []) if row.get("case"))
        if self._show_distributed_loads():
            visible_load_cases.update(row.get("case") for row in model.get("distributed_loads", []) if row.get("case"))
        sw_case = model.get("self_weight_case") or "SW"
        if model.get("self_weight") and self._show_self_weight():
            visible_load_cases.add(sw_case)

        entries = []
        for case_name in model.get("cases", []):
            if case_name not in visible or case_name not in visible_load_cases:
                continue
            meta = (model.get("case_metadata", {}) or {}).get(case_name, {})
            label = str(meta.get("type") or case_name)
            factor = float(visible.get(case_name, 1.0))
            entries.append({
                "name": case_name,
                "label": label,
                "description": str(meta.get("description", "")).strip(),
                "factor": factor,
                "color": self._case_color(model, case_name),
            })

        if model.get("self_weight") and self._show_self_weight():
            sw_case = model.get("self_weight_case") or "SW"
            if sw_case in visible:
                entries.append({
                    "name": sw_case,
                    "label": "Self-weight",
                    "description": "Automatic gravity load",
                    "factor": float(visible.get(sw_case, 1.0)),
                    "color": self._case_color(model, sw_case, self_weight=True),
                    "self_weight": True,
                })
        return entries

    def _build(self):
        panel = self.panel
        model = panel.model
        result = panel.result if panel.result_current() else None
        case = panel.case.currentText() if hasattr(panel, "case") else ""
        diagram = panel.diagram.currentText() if hasattr(panel, "diagram") else "Model"
        scale = float(panel.diagram_scale.value()) if hasattr(panel, "diagram_scale") else 1.0
        label_count = int(panel.label_count.value()) if hasattr(panel, "label_count") else 0
        key = (
            panel.revision, panel.result_revision, case, diagram, round(scale, 6), label_count,
            self._show_point_loads(), self._show_distributed_loads(), self._show_self_weight(), self._show_load_labels(), self._show_active_load_only(), self._show_diagram_labels(),
        )
        if key == self._key and self._cache is not None:
            return self._cache
        self._key = key
        empty = {"members": [], "nodes": [], "diagram": [], "diagram_labels": [], "reactions": [], "loads": []}
        if not model:
            self._cache = empty
            return self._cache

        nodes = {row["id"]: row for row in model["nodes"]}
        by_member = {row["id"]: row for row in model["members"]}
        members = []
        for member in model["members"]:
            a, b = nodes[member["i"]], nodes[member["j"]]
            members.append((member["id"], np.array([[a["x"], 0.0, a["z"]], [b["x"], 0.0, b["z"]]], dtype=float)))
        node_points = [
            (nid, np.array([row["x"], 0.0, row["z"]], dtype=float), row)
            for nid, row in nodes.items()
        ]

        diagram_lines = []
        diagram_labels = []
        reactions = []
        loads = []
        span = self._span(model)

        # Applied forces/moments: only the selected base case or the factored selected combination.
        if self._show_point_loads():
            for load in model.get("point_loads", []):
                factor = self._display_factor(model, case, load["case"])
                if abs(factor) < 1e-14:
                    continue
                value = float(load["value"]) * factor
                if "node" in load:
                    base = np.array([nodes[load["node"]]["x"], 0.0, nodes[load["node"]]["z"]], dtype=float)
                else:
                    base = self._world_point(by_member[load["member"]], nodes, float(load["x"]))
                tag = self._factor_tag(factor, load["case"])
                color = self._case_color(model, load["case"])
                label = f"{load['direction']} = {value:.4g} kN {tag}" if self._show_load_labels() else ""
                if load["direction"] in ("FX", "FZ"):
                    sign = 1.0 if value >= 0 else -1.0
                    direction = np.array([sign, 0.0, 0.0]) if load["direction"] == "FX" else np.array([0.0, 0.0, sign])
                    tail = base - direction * (0.13 * span)
                    loads.append({
                        "kind": "force", "points": np.array([tail, base]),
                        "label": label, "color": color,
                    })
                else:
                    loads.append({
                        "kind": "moment", "point": base, "sign": 1.0 if value >= 0 else -1.0,
                        "label": f"MY = {value:.4g} kN·m {tag}" if self._show_load_labels() else "", "color": color,
                    })

        if self._show_distributed_loads():
            for load in model.get("distributed_loads", []):
                factor = self._display_factor(model, case, load["case"])
                if abs(factor) < 1e-14:
                    continue
                member = by_member[load["member"]]
                length = math.hypot(
                    nodes[member["j"]]["x"] - nodes[member["i"]]["x"],
                    nodes[member["j"]]["z"] - nodes[member["i"]]["z"],
                )
                x1, x2 = float(load.get("x1", 0.0)), float(load.get("x2", length))
                arrows = []
                tails = []
                for x in np.linspace(x1, x2, 7):
                    base = self._world_point(member, nodes, float(x))
                    t = 0.0 if x2 == x1 else (x - x1) / (x2 - x1)
                    value = (load["w1"] + (load["w2"] - load["w1"]) * t) * factor
                    sign = 1.0 if value >= 0 else -1.0
                    direction = np.array([sign, 0.0, 0.0]) if load["direction"] == "FX" else np.array([0.0, 0.0, sign])
                    # Preserve visible arrow length while keeping direction/sign engineering-correct.
                    tail = base - direction * (0.095 * span)
                    arrows.append(np.array([tail, base]))
                    tails.append(tail)
                w1, w2 = float(load["w1"]) * factor, float(load["w2"]) * factor
                tag = self._factor_tag(factor, load["case"])
                value_text = f"{w1:.4g}" if abs(w1 - w2) < 1e-12 else f"{w1:.4g} → {w2:.4g}"
                loads.append({
                    "kind": "udl", "arrows": arrows, "baseline": np.array(tails),
                    "label": f"{load['direction']} w = {value_text} kN/m {tag}" if self._show_load_labels() else "",
                    "label_point": tails[len(tails) // 2], "color": self._case_color(model, load["case"]),
                })

        # Self-weight is a real engineering load. Show it for its base case and
        # any selected combination that contains the self-weight case.
        if model.get("self_weight", False) and self._show_self_weight():
            sw_case = model.get("self_weight_case")
            if self._show_active_load_only():
                if sw_case:
                    sw_factor = self._case_factor(model, case, sw_case)
                elif case in model.get("cases", []):
                    sw_factor = 1.0
                else:
                    sw_factor = float(sum((model.get("combinations", {}).get(case, {}) or {}).values()))
            else:
                sw_factor = 1.0
            if abs(sw_factor) > 1e-14:
                materials = {row["id"]: row for row in model.get("materials", [])}
                sections = {row["id"]: row for row in model.get("sections", [])}
                for member in model.get("members", []):
                    rho = float(materials[member["material"]].get("rho", 0.0))
                    area = float(sections[member["section"]]["A"])
                    q = -rho * area * sw_factor
                    if abs(q) <= 1e-14:
                        continue
                    length = math.hypot(
                        nodes[member["j"]]["x"] - nodes[member["i"]]["x"],
                        nodes[member["j"]]["z"] - nodes[member["i"]]["z"],
                    )
                    arrows = []
                    tails = []
                    for x in np.linspace(0.0, length, 5):
                        base = self._world_point(member, nodes, float(x))
                        direction = np.array([0.0, 0.0, -1.0])
                        tail = base - direction * (0.06 * span)
                        arrows.append(np.array([tail, base]))
                        tails.append(tail)
                    tag = self._factor_tag(sw_factor, sw_case or "SW")
                    loads.append({
                        "kind": "udl", "arrows": arrows, "baseline": np.array(tails),
                        "label": f"Self-weight FZ w = {q:.4g} kN/m {tag}" if self._show_load_labels() else "",
                        "label_point": tails[1 if len(tails) > 1 else 0],
                        "color": self._case_color(model, sw_case or "SW", self_weight=True),
                    })

        if result and case in result.get("cases", {}):
            case_data = result["cases"][case]
            if diagram in ("N", "V", "M"):
                quantity = diagram
                peak = max((abs(p[quantity]) for mr in case_data["members"].values() for p in mr["plot"]), default=0.0)
                factor = (0.16 * span * scale / peak) if peak > 1e-14 else 0.0
                for mid, mr in case_data["members"].items():
                    member = by_member[mid]
                    normal = self._normal(member, nodes)
                    bases = [self._world_point(member, nodes, p["x"]) for p in mr["plot"]]
                    values = [float(p[quantity]) for p in mr["plot"]]
                    pts = [base + normal * (value * factor) for base, value in zip(bases, values)]
                    diagram_lines.append({
                        "member": mid, "curve": np.array(pts, dtype=float),
                        "baseline": np.array(bases, dtype=float), "values": values, "quantity": quantity,
                    })
                    unit = {"N": "kN", "V": "kN", "M": "kN·m"}[quantity]
                    if self._show_diagram_labels():
                        for row in sample_plot(mr["plot"], mr["L"], label_count):
                            base = self._world_point(member, nodes, row["x"])
                            point = base + normal * (row[quantity] * factor)
                            diagram_labels.append({"point": point, "text": f"{row[quantity]:.4g} {unit}"})
            elif diagram == "Deflection":
                peak = max((abs(p["d"]) for mr in case_data["members"].values() for p in mr["plot"]), default=0.0)
                factor = (0.15 * span * scale / peak) if peak > 1e-14 else 0.0
                for mid, mr in case_data["members"].items():
                    member = by_member[mid]
                    normal = self._normal(member, nodes)
                    pts = []
                    # anaStruct transverse deflection `d` is displayed opposite the
                    # member's positive local normal so a gravity-loaded horizontal
                    # beam visibly sags downward in the engineering viewport.
                    for p in mr["plot"]:
                        base = self._world_point(member, nodes, p["x"])
                        pts.append(base - normal * (p["d"] * factor))
                    diagram_lines.append({"member": mid, "curve": np.array(pts, dtype=float), "quantity": "D"})
                    if self._show_diagram_labels():
                        for row in sample_plot(mr["plot"], mr["L"], label_count):
                            base = self._world_point(member, nodes, row["x"])
                            point = base - normal * (row["d"] * factor)
                            value_mm = row["d"] * 1000.0
                            if abs(value_mm) < 5e-7:
                                value_mm = 0.0
                            diagram_labels.append({"point": point, "text": f"{value_mm:.4g} mm"})
            elif diagram == "Deformed":
                peak = max((math.hypot(p["ux"], p["uz"]) for mr in case_data["members"].values() for p in mr["plot"]), default=0.0)
                factor = (0.15 * span * scale / peak) if peak > 1e-14 else 0.0
                for mid, mr in case_data["members"].items():
                    member = by_member[mid]
                    pts = []
                    for p in mr["plot"]:
                        base = self._world_point(member, nodes, p["x"])
                        pts.append(base + np.array([p["ux"] * factor, 0.0, p["uz"] * factor]))
                    diagram_lines.append({"member": mid, "curve": np.array(pts, dtype=float), "quantity": "D"})
                    if self._show_diagram_labels():
                        for row in sample_plot(mr["plot"], mr["L"], label_count):
                            base = self._world_point(member, nodes, row["x"])
                            point = base + np.array([row["ux"] * factor, 0.0, row["uz"] * factor])
                            value_mm = row["d"] * 1000.0
                            if abs(value_mm) < 5e-7:
                                value_mm = 0.0
                            diagram_labels.append({"point": point, "text": f"{value_mm:.4g} mm"})
            elif diagram == "Reaction":
                peak = max((max(abs(r["Rx"]), abs(r["Rz"])) for r in case_data["nodes"].values()), default=0.0)
                factor = (0.13 * span * scale / peak) if peak > 1e-14 else 0.0
                for nid, reaction in case_data["nodes"].items():
                    base = np.array([nodes[nid]["x"], 0.0, nodes[nid]["z"]], dtype=float)
                    if abs(reaction["Rx"]) > 1e-12:
                        tail = base - np.array([reaction["Rx"] * factor, 0.0, 0.0])
                        reactions.append({"kind": "force", "points": np.array([tail, base]), "label": f"Rx = {reaction['Rx']:.4g} kN"})
                    if abs(reaction["Rz"]) > 1e-12:
                        tail = base - np.array([0.0, 0.0, reaction["Rz"] * factor])
                        reactions.append({"kind": "force", "points": np.array([tail, base]), "label": f"Rz = {reaction['Rz']:.4g} kN"})
                    if abs(reaction["My"]) > 1e-12:
                        reactions.append({"kind": "moment", "point": base, "sign": 1.0 if reaction["My"] >= 0 else -1.0, "label": f"My = {reaction['My']:.4g} kN·m"})

        self._cache = {"members": members, "nodes": node_points, "diagram": diagram_lines, "diagram_labels": diagram_labels, "reactions": reactions, "loads": loads}
        return self._cache

    def _project_one(self, point):
        px, py, front = self.panel.app.world_to_pixels(np.array([point], dtype=float))
        if not front[0]:
            return None
        return QPointF(float(px[0]), float(py[0]))

    def _draw_polyline(self, painter, points, color, width=2):
        if len(points) < 2:
            return
        px, py, front = self.panel.app.world_to_pixels(points)
        painter.setPen(QPen(QColor(color), width))
        for i in range(len(points) - 1):
            if front[i] or front[i + 1]:
                painter.drawLine(QPointF(float(px[i]), float(py[i])), QPointF(float(px[i + 1]), float(py[i + 1])))


    def _draw_signed_fill(self, painter, item):
        baseline = item.get("baseline")
        curve = item.get("curve")
        values = item.get("values") or []
        if baseline is None or curve is None or len(curve) < 2 or len(values) < 2:
            return
        positive = QColor("#3b82f6"); positive.setAlpha(72)
        negative = QColor("#ef4444"); negative.setAlpha(72)
        painter.setPen(QPen(Qt.NoPen))
        for i in range(len(curve) - 1):
            b0, b1 = baseline[i], baseline[i + 1]
            c0, c1 = curve[i], curve[i + 1]
            for t0, t1, sign in signed_interval_parts(values[i], values[i + 1]):
                bb0 = b0 + (b1 - b0) * t0
                bb1 = b0 + (b1 - b0) * t1
                cc0 = c0 + (c1 - c0) * t0
                cc1 = c0 + (c1 - c0) * t1
                world = np.array([bb0, cc0, cc1, bb1], dtype=float)
                px, py, front = self.panel.app.world_to_pixels(world)
                if not any(bool(v) for v in front):
                    continue
                painter.setBrush(QBrush(positive if sign >= 0 else negative))
                painter.drawPolygon(QPolygonF([QPointF(float(px[j]), float(py[j])) for j in range(4)]))

    def _draw_arrow(self, painter, points, color, label="", label_offset=(6.0, -6.0), width=2):
        px, py, front = self.panel.app.world_to_pixels(points)
        if not (front[0] or front[-1]):
            return
        a = QPointF(float(px[0]), float(py[0])); b = QPointF(float(px[-1]), float(py[-1]))
        painter.setPen(QPen(QColor(color), width)); painter.setBrush(QBrush(QColor(color)))
        painter.drawLine(a, b)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy)
        if length > 1e-6:
            ux, uy = dx / length, dy / length
            nx, ny = -uy, ux
            size = 8.0
            p1 = QPointF(b.x() - ux * size + nx * size * 0.48, b.y() - uy * size + ny * size * 0.48)
            p2 = QPointF(b.x() - ux * size - nx * size * 0.48, b.y() - uy * size - ny * size * 0.48)
            painter.drawPolygon(QPolygonF([b, p1, p2]))
        if label:
            painter.drawText(QPointF(a.x() + label_offset[0], a.y() + label_offset[1]), label)

    def _draw_moment(self, painter, world, sign, color, label):
        p = self._project_one(world)
        if p is None:
            return
        radius = 17.0
        rect = QRectF(p.x() - radius, p.y() - radius, radius * 2, radius * 2)
        painter.setPen(QPen(QColor(color), 2)); painter.setBrush(QBrush(QColor(color)))
        start = 35 * 16 if sign >= 0 else 145 * 16
        span = 285 * 16 if sign >= 0 else -285 * 16
        painter.drawArc(rect, start, span)
        # Arrow head near the arc end; visual sign follows the arc direction.
        angle = math.radians(320 if sign >= 0 else 220)
        tip = QPointF(p.x() + radius * math.cos(angle), p.y() - radius * math.sin(angle))
        tangent = angle - (math.pi / 2 if sign >= 0 else -math.pi / 2)
        ux, uy = math.cos(tangent), -math.sin(tangent)
        nx, ny = -uy, ux
        size = 7.0
        p1 = QPointF(tip.x() - ux * size + nx * size * 0.45, tip.y() - uy * size + ny * size * 0.45)
        p2 = QPointF(tip.x() - ux * size - nx * size * 0.45, tip.y() - uy * size - ny * size * 0.45)
        painter.drawPolygon(QPolygonF([tip, p1, p2]))
        painter.drawText(QPointF(p.x() + 22, p.y() - 18), label)

    def _draw_support(self, painter, point, node, selected=False):
        p = self._project_one(point)
        if p is None:
            return
        support = node.get("support", "Free")
        color = QColor("#d88920" if selected else "#34495e")
        painter.setPen(QPen(color, 2)); painter.setBrush(QBrush())
        painter.drawEllipse(p, 4.5, 4.5)
        if support == "Free":
            return
        x, y = p.x(), p.y()
        if support == "Fixed":
            painter.drawLine(QPointF(x - 10, y + 6), QPointF(x + 10, y + 6))
            for dx in (-8, -4, 0, 4, 8):
                painter.drawLine(QPointF(x + dx, y + 6), QPointF(x + dx - 5, y + 13))
        elif support in ("Pin", "Roller"):
            triangle = QPolygonF([QPointF(x, y + 5), QPointF(x - 10, y + 18), QPointF(x + 10, y + 18)])
            painter.drawPolygon(triangle)
            if support == "Roller":
                painter.drawEllipse(QPointF(x - 5, y + 22), 3.0, 3.0)
                painter.drawEllipse(QPointF(x + 5, y + 22), 3.0, 3.0)
                painter.drawLine(QPointF(x - 12, y + 27), QPointF(x + 12, y + 27))
        elif support == "RollerX":
            triangle = QPolygonF([QPointF(x + 5, y), QPointF(x + 18, y - 10), QPointF(x + 18, y + 10)])
            painter.drawPolygon(triangle)
            painter.drawEllipse(QPointF(x + 22, y - 5), 3.0, 3.0)
            painter.drawEllipse(QPointF(x + 22, y + 5), 3.0, 3.0)
            painter.drawLine(QPointF(x + 27, y - 12), QPointF(x + 27, y + 12))
        elif support == "Spring":
            path = QPainterPath(QPointF(x, y + 5))
            path.lineTo(x, y + 9)
            for i, dx in enumerate((-5, 5, -5, 5, -5, 5)):
                path.lineTo(x + dx, y + 12 + i * 4)
            path.lineTo(x, y + 38)
            painter.drawPath(path)
            painter.drawLine(QPointF(x - 11, y + 38), QPointF(x + 11, y + 38))
            springs = node.get("springs", {}) or {}
            labels = []
            for dof, unit in (("UX", "kN/m"), ("UZ", "kN/m"), ("RY", "kN·m/rad")):
                if dof in springs:
                    labels.append(f"k{dof[1:].lower()}={springs[dof]:.4g} {unit}")
            if labels:
                painter.drawText(QPointF(x + 10, y + 36), ", ".join(labels))

    def paint(self, viewport, painter):
        cache = self._build()
        selected = self.panel.selected_item

        for mid, points in cache["members"]:
            color = "#d88920" if selected == "member:" + mid else "#5c6873"
            self._draw_polyline(painter, points, color, 3 if selected == "member:" + mid else 2)

        for nid, point, node in cache["nodes"]:
            self._draw_support(painter, point, node, selected == "node:" + nid)

        # Applied actions are blue and always carry engineering values/units.
        for item in cache.get("loads", []):
            color = item.get("color", "#2b7dbd")
            if item["kind"] == "force":
                self._draw_arrow(painter, item["points"], color, item["label"], width=2)
            elif item["kind"] == "moment":
                self._draw_moment(painter, item["point"], item["sign"], color, item["label"])
            elif item["kind"] == "udl":
                self._draw_polyline(painter, item["baseline"], color, 1)
                for arrow in item["arrows"]:
                    self._draw_arrow(painter, arrow, color, width=1)
                label_point = self._project_one(item["label_point"])
                if label_point is not None and item.get("label"):
                    painter.setPen(QPen(QColor(color), 1))
                    painter.drawText(QPointF(label_point.x() + 6, label_point.y() - 8), item["label"])

        for item in cache["diagram"]:
            quantity = item.get("quantity", "D")
            if quantity in ("N", "V", "M"):
                self._draw_signed_fill(painter, item)
            color = {"N": "#244a7c", "V": "#236b48", "M": "#8f3030", "D": "#8b5cb8"}.get(quantity, "#8b5cb8")
            self._draw_polyline(painter, item["curve"], color, 2)

        for label in cache.get("diagram_labels", []):
            p = self._project_one(label["point"])
            if p is not None:
                painter.setPen(QPen(QColor("#1f2933"), 1))
                painter.drawText(QPointF(p.x() + 5, p.y() - 6), label["text"])

        for item in cache["reactions"]:
            if item["kind"] == "force":
                self._draw_arrow(painter, item["points"], "#cf7f20", item["label"], width=2)
            else:
                self._draw_moment(painter, item["point"], item["sign"], "#cf7f20", item["label"])

        if not self.panel.show_ids.isChecked() and not self.panel.show_values.isChecked():
            return
        model = self.panel.model
        if not model:
            return
        nodes = {row["id"]: row for row in model["nodes"]}
        painter.setPen(QPen(QColor("#1f2933"), 1))

        if self.panel.show_ids.isChecked():
            pts = np.array([[row["x"], 0.0, row["z"]] for row in model["nodes"]], dtype=float)
            px, py, front = self.panel.app.world_to_pixels(pts)
            for i, row in enumerate(model["nodes"]):
                if front[i]:
                    painter.drawText(QPointF(float(px[i] + 6), float(py[i] - 8)), row["id"])
            for member in model["members"]:
                a, b = nodes[member["i"]], nodes[member["j"]]
                pt = np.array([[(a["x"] + b["x"]) / 2.0, 0.0, (a["z"] + b["z"]) / 2.0]], dtype=float)
                mx, my, mf = self.panel.app.world_to_pixels(pt)
                if mf[0]:
                    painter.drawText(QPointF(float(mx[0] + 5), float(my[0] - 6)), member["id"])

        if self.panel.show_values.isChecked() and self.panel.result_current():
            case = self.panel.case.currentText()
            diagram = self.panel.diagram.currentText()
            if case in self.panel.result.get("cases", {}) and diagram in ("N", "V", "M", "Deflection"):
                quantity = {"Deflection": "d"}.get(diagram, diagram)
                unit = {"N": "kN", "V": "kN", "M": "kN·m", "d": "mm"}[quantity]
                by_id = {m["id"]: m for m in model["members"]}
                for mid, mr in self.panel.result["cases"][case]["members"].items():
                    member = by_id[mid]
                    extrema = mr["extrema"][quantity]
                    for kind in ("min", "max"):
                        row = extrema[kind]
                        pt = np.array([self._world_point(member, nodes, row["x"])], dtype=float)
                        x, y, front = self.panel.app.world_to_pixels(pt)
                        if front[0]:
                            value = row["value"] * 1000.0 if quantity == "d" else row["value"]
                            if abs(value) < 5e-7:
                                value = 0.0
                            painter.drawText(
                                QPointF(float(x[0] + 5), float(y[0] + (14 if kind == "max" else -8))),
                                f"{value:.4g} {unit}",
                            )
