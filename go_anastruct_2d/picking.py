from __future__ import annotations
import math
import numpy as np

from .diagram_utils import interpolate_plot


def _closest_parameter(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return 0.0, math.hypot(px - a[0], py - a[1])
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / denom))
    qx, qy = a[0] + t * dx, a[1] + t * dy
    return t, math.hypot(px - qx, py - qy)


def _distance_to_segment(px, py, a, b):
    return _closest_parameter(px, py, a, b)[1]


def pick_item(app, model, px, py, tolerance=9.0):
    if not model:
        return None
    nodes = {row["id"]: row for row in model["nodes"]}
    node_ids = list(nodes)
    pts = np.array([[nodes[n]["x"], 0.0, nodes[n]["z"]] for n in node_ids], dtype=float)
    sx, sy, front = app.world_to_pixels(pts)
    best = None
    for i, nid in enumerate(node_ids):
        if not front[i]:
            continue
        distance = math.hypot(px - float(sx[i]), py - float(sy[i]))
        if distance <= tolerance and (best is None or distance < best[0]):
            best = (distance, "node:" + nid)
    if best is not None:
        return best[1]

    hits = []
    for member in model["members"]:
        a, b = nodes[member["i"]], nodes[member["j"]]
        points = np.array([[a["x"], 0.0, a["z"]], [b["x"], 0.0, b["z"]]], dtype=float)
        mx, my, mf = app.world_to_pixels(points)
        if not bool(mf[0]) and not bool(mf[1]):
            continue
        distance = _distance_to_segment(px, py, (float(mx[0]), float(my[0])), (float(mx[1]), float(my[1])))
        if distance <= tolerance:
            hits.append((distance, "member:" + member["id"]))
    return min(hits, key=lambda row: row[0])[1] if hits else None


def hover_member_data(app, model, result, case, px, py, tolerance=13.0):
    """Return cached member-result data nearest a viewport pixel, or None."""
    if not model or not result or case not in result.get("cases", {}):
        return None
    nodes = {row["id"]: row for row in model["nodes"]}
    case_data = result["cases"][case]
    best = None
    for member in model.get("members", []):
        mr = case_data.get("members", {}).get(member["id"])
        if not mr:
            continue
        a, b = nodes[member["i"]], nodes[member["j"]]
        world = np.array([[a["x"], 0.0, a["z"]], [b["x"], 0.0, b["z"]]], dtype=float)
        sx, sy, front = app.world_to_pixels(world)
        if not bool(front[0]) and not bool(front[1]):
            continue
        t, distance = _closest_parameter(px, py, (float(sx[0]), float(sy[0])), (float(sx[1]), float(sy[1])))
        if distance > tolerance or (best is not None and distance >= best[0]):
            continue
        length = float(mr.get("L", math.hypot(b["x"] - a["x"], b["z"] - a["z"])))
        x = t * length
        values = interpolate_plot(mr.get("plot", []), x)
        wx = a["x"] + t * (b["x"] - a["x"])
        wz = a["z"] + t * (b["z"] - a["z"])
        label = (
            f"{member['id']} @ {x:.3f} m | "
            f"N = {values['N']:.4g} kN | V = {values['V']:.4g} kN | "
            f"M = {values['M']:.4g} kN·m | d = {values['d'] * 1000.0:.4g} mm [{case}]"
        )
        best = {"distance": distance, "member": member["id"], "x": x, "values": values, "world": (wx, 0.0, wz), "label": label}
    return best


def internal_force_hover(app, model, result, case, px, py, tolerance=13.0):
    """Return a native SnapResult for tools that use the IngeTrazo snap pipeline."""
    best = hover_member_data(app, model, result, case, px, py, tolerance=tolerance)
    if best is None:
        return None
    from PySide6.QtGui import QVector3D
    from core.snap import SnapResult
    wx, wy, wz = best["world"]
    return SnapResult(QVector3D(float(wx), float(wy), float(wz)), "reference", (0.15, 0.55, 0.95), label=best["label"])
