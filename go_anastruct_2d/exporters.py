from __future__ import annotations
import csv
import math
from pathlib import Path



def _case_color(model, case_name, *, self_weight=False):
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


def _case_factor(model, selected_case, load_case):
    if selected_case in model.get("cases", []):
        return 1.0 if selected_case == load_case else 0.0
    return float((model.get("combinations", {}).get(selected_case, {}) or {}).get(load_case, 0.0))


def _visible_legend_entries(model, selected_case, active_only=True, options=None):
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
    options = options or {}
    show_point = bool(options.get("show_point_loads", True))
    show_dist = bool(options.get("show_distributed_loads", True))
    show_sw = bool(options.get("show_self_weight", True))
    visible_load_cases = set()
    if show_point:
        visible_load_cases.update(row.get("case") for row in model.get("point_loads", []) if row.get("case"))
    if show_dist:
        visible_load_cases.update(row.get("case") for row in model.get("distributed_loads", []) if row.get("case"))
    sw_case = model.get("self_weight_case") or "SW"
    if model.get("self_weight") and show_sw:
        visible_load_cases.add(sw_case)

    entries = []
    for case_name in model.get("cases", []):
        if case_name not in visible or case_name not in visible_load_cases:
            continue
        meta = (model.get("case_metadata", {}) or {}).get(case_name, {})
        entries.append({
            "name": case_name,
            "type": str(meta.get("type") or case_name),
            "description": str(meta.get("description", "")).strip(),
            "factor": float(visible.get(case_name, 1.0)),
            "color": _case_color(model, case_name),
        })
    sw_case = model.get("self_weight_case") or "SW"
    if model.get("self_weight") and show_sw and sw_case in visible:
        entries.append({
            "name": sw_case, "type": "Self-weight", "description": "Automatic gravity load",
            "factor": float(visible.get(sw_case, 1.0)), "color": _case_color(model, sw_case, self_weight=True),
        })
    return entries


def _draw_load_legend(painter, model, selected_case, rect, active_only=True, options=None):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPen
    entries = _visible_legend_entries(model, selected_case, active_only, options=options)
    painter.setPen(QPen(QColor("#1f2933"), 1))
    font = QFont(painter.font()); font.setPointSize(8); painter.setFont(font)
    x = rect.left(); y = rect.top()
    painter.drawText(QRectF(x, y, rect.width(), 16), Qt.AlignmentFlag.AlignLeft, "Load legend")
    y += 18
    for entry in entries:
        painter.setPen(QPen(QColor(entry["color"]), 1)); painter.setBrush(QBrush(QColor(entry["color"])))
        painter.drawEllipse(QPointF(x + 5, y + 5), 4, 4)
        painter.setPen(QPen(QColor("#1f2933"), 1))
        factor = entry["factor"]
        factor_text = "" if abs(factor - 1.0) < 1e-12 else f" x{factor:.3g}"
        label = f"{entry['name']} - {entry['type']}{factor_text}"
        if entry["description"]:
            label += f" ({entry['description']})"
        painter.drawText(QRectF(x + 16, y - 3, rect.width() - 16, 16), Qt.AlignmentFlag.AlignLeft, label)
        y += 16
        if y > rect.bottom() - 14:
            break


def _fit_image_rect(image, target):
    from PySide6.QtCore import QRectF
    if image is None or image.isNull() or image.width() <= 0 or image.height() <= 0:
        return target
    scale = min(target.width() / image.width(), target.height() / image.height())
    width = image.width() * scale
    height = image.height() * scale
    return QRectF(target.center().x() - width / 2.0, target.center().y() - height / 2.0, width, height)


def export_csv(directory, model, result, case):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    data = result["cases"][case]
    paths = []

    def write(name, header, rows):
        path = root / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        paths.append(str(path))

    write(
        "model_nodes.csv",
        ["Node", "X [m]", "Z [m]", "Support", "Springs"],
        [[n["id"], n["x"], n["z"], n.get("support", "Free"), n.get("springs", {})] for n in model["nodes"]],
    )
    write(
        "model_members.csv",
        ["Member", "i", "j", "Type", "Material", "Section", "Release i", "Release j"],
        [[m["id"], m["i"], m["j"], m.get("type", "Frame"), m["material"], m["section"], m.get("release_i", False), m.get("release_j", False)] for m in model["members"]],
    )
    write(
        "node_results.csv",
        ["Case", "Node", "UX [m]", "UZ [m]", "Rotation [rad]", "RX [kN]", "RZ [kN]", "MY [kN.m]"],
        [[case, nid, row["ux"], row["uz"], row["rotation"], row["Rx"], row["Rz"], row["My"]] for nid, row in data["nodes"].items()],
    )
    write(
        "member_extrema.csv",
        ["Case", "Member", "Quantity", "Type", "Value", "x [m]", "Side"],
        [[case, mid, quantity, kind, row["value"], row["x"], row["side"]]
         for mid, member in data["members"].items()
         for quantity, extrema in member["extrema"].items()
         for kind, row in extrema.items()],
    )
    write(
        "member_diagrams.csv",
        ["Case", "Member", "x [m]", "Side", "N [kN]", "V [kN]", "M [kN.m]", "d [m]", "UX [m]", "UZ [m]"],
        [[case, mid, row["x"], row["side"], row["N"], row["V"], row["M"], row["d"], row["ux"], row["uz"]]
         for mid, member in data["members"].items() for row in member["plot"]],
    )
    return paths


def _bounds(model):
    xs = [float(n["x"]) for n in model["nodes"]]
    zs = [float(n["z"]) for n in model["nodes"]]
    xmin, xmax = min(xs), max(xs)
    zmin, zmax = min(zs), max(zs)
    if xmax - xmin < 1e-9:
        xmax += 0.5; xmin -= 0.5
    if zmax - zmin < 1e-9:
        zmax += 0.5; zmin -= 0.5
    return xmin, xmax, zmin, zmax


def _xy_mapper(model, rect):
    xmin, xmax, zmin, zmax = _bounds(model)
    spanx, spanz = xmax - xmin, zmax - zmin
    sx = rect.width() / spanx
    sz = rect.height() / spanz
    scale = min(sx, sz) * 0.82
    cx = (xmin + xmax) / 2.0
    cz = (zmin + zmax) / 2.0
    rx = rect.center().x()
    ry = rect.center().y()
    def point(x, z):
        from PySide6.QtCore import QPointF
        return QPointF(rx + (x - cx) * scale, ry - (z - cz) * scale)
    return point, scale


def _draw_arrow(painter, a, b, color, width=2):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
    painter.setPen(QPen(QColor(color), width))
    painter.setBrush(QBrush(QColor(color)))
    painter.drawLine(a, b)
    dx, dy = b.x() - a.x(), b.y() - a.y()
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    size = 7.0
    p1 = QPointF(b.x() - ux * size + nx * size * 0.45, b.y() - uy * size + ny * size * 0.45)
    p2 = QPointF(b.x() - ux * size - nx * size * 0.45, b.y() - uy * size - ny * size * 0.45)
    painter.drawPolygon(QPolygonF([b, p1, p2]))


def _draw_moment(painter, p, sign, color, label=""):
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
    radius = 14.0
    rect = QRectF(p.x() - radius, p.y() - radius, radius * 2, radius * 2)
    painter.setPen(QPen(QColor(color), 1.5)); painter.setBrush(QBrush(QColor(color)))
    start = 35 * 16 if sign >= 0 else 145 * 16
    span = 285 * 16 if sign >= 0 else -285 * 16
    painter.drawArc(rect, start, span)
    angle = math.radians(320 if sign >= 0 else 220)
    tip = QPointF(p.x() + radius * math.cos(angle), p.y() - radius * math.sin(angle))
    tangent = angle - (math.pi / 2 if sign >= 0 else -math.pi / 2)
    ux, uy = math.cos(tangent), -math.sin(tangent)
    nx, ny = -uy, ux
    size = 6.0
    p1 = QPointF(tip.x() - ux * size + nx * size * 0.4, tip.y() - uy * size + ny * size * 0.4)
    p2 = QPointF(tip.x() - ux * size - nx * size * 0.4, tip.y() - uy * size - ny * size * 0.4)
    painter.drawPolygon(QPolygonF([tip, p1, p2]))
    if label:
        painter.drawText(QPointF(p.x() + 18, p.y() - 14), label)


def _draw_support(painter, p, support):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPen, QPolygonF
    painter.setPen(QPen(QColor("#34495e"), 1.5))
    x, y = p.x(), p.y()
    if support == "Fixed":
        painter.drawLine(QPointF(x - 8, y + 5), QPointF(x + 8, y + 5))
        for dx in (-6, -2, 2, 6):
            painter.drawLine(QPointF(x + dx, y + 5), QPointF(x + dx - 4, y + 11))
    elif support in ("Pin", "Roller"):
        painter.drawPolygon(QPolygonF([QPointF(x, y + 3), QPointF(x - 8, y + 14), QPointF(x + 8, y + 14)]))
        if support == "Roller":
            painter.drawEllipse(QPointF(x - 4, y + 18), 2.5, 2.5)
            painter.drawEllipse(QPointF(x + 4, y + 18), 2.5, 2.5)
    elif support == "RollerX":
        painter.drawPolygon(QPolygonF([QPointF(x + 3, y), QPointF(x + 14, y - 8), QPointF(x + 14, y + 8)]))
    elif support == "Spring":
        painter.drawText(QPointF(x + 5, y + 12), "SPR")


def _member_point(model, member, x):
    nodes = {n["id"]: n for n in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    L = math.hypot(b["x"] - a["x"], b["z"] - a["z"])
    t = 0.0 if L <= 1e-12 else float(x) / L
    return a["x"] + t * (b["x"] - a["x"]), a["z"] + t * (b["z"] - a["z"])


def _normal(model, member):
    nodes = {n["id"]: n for n in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    dx, dz = b["x"] - a["x"], b["z"] - a["z"]
    L = math.hypot(dx, dz)
    return -dz / L, dx / L


def _draw_model_page(painter, model, result, case, rect, title_text):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QPen
    point, _ = _xy_mapper(model, rect)
    nodes = {n["id"]: n for n in model["nodes"]}
    painter.setPen(QPen(QColor("#53616d"), 2))
    for m in model["members"]:
        a, b = nodes[m["i"]], nodes[m["j"]]
        pa, pb = point(a["x"], a["z"]), point(b["x"], b["z"])
        painter.drawLine(pa, pb)
        painter.drawText((pa + pb) / 2 + QPointF(5, -5), m["id"])
    for n in model["nodes"]:
        p = point(n["x"], n["z"])
        painter.drawEllipse(p, 3.0, 3.0)
        _draw_support(painter, p, n.get("support", "Free"))
        painter.drawText(p + QPointF(5, -7), n["id"])
    members = {m["id"]: m for m in model["members"]}
    for load in model.get("point_loads", []):
        f = _case_factor(model, case, load["case"])
        if abs(f) < 1e-12:
            continue
        if "node" in load:
            n = nodes[load["node"]]; base = point(n["x"], n["z"])
        else:
            x,z = _member_point(model, members[load["member"]], load["x"]); base = point(x,z)
        value = float(load["value"]) * f
        color = _case_color(model, load["case"])
        if load["direction"] == "FZ":
            tail = base + QPointF(0, -34 if value < 0 else 34)
            _draw_arrow(painter, tail, base, color, 1)
            painter.setPen(QPen(QColor(color), 1)); painter.drawText(base + QPointF(7, -7), f"FZ {value:.4g} kN")
        elif load["direction"] == "FX":
            tail = base + QPointF(-34 if value > 0 else 34, 0)
            _draw_arrow(painter, tail, base, color, 1)
            painter.setPen(QPen(QColor(color), 1)); painter.drawText(base + QPointF(7, -7), f"FX {value:.4g} kN")
        elif load["direction"] == "MY":
            _draw_moment(painter, base, 1.0 if value >= 0 else -1.0, color, f"MY {value:.4g} kN·m")

    for load in model.get("distributed_loads", []):
        f = _case_factor(model, case, load["case"])
        if abs(f) < 1e-12:
            continue
        member = members[load["member"]]
        x1 = float(load.get("x1", 0.0)); x2 = float(load.get("x2", 0.0))
        if x2 <= x1:
            continue
        w1 = float(load["w1"]) * f; w2 = float(load["w2"]) * f
        color = _case_color(model, load["case"])
        bases=[]; tails=[]
        peak=max(abs(w1),abs(w2),1e-12)
        for i in range(7):
            t=i/6.0; x=x1+(x2-x1)*t; value=w1+(w2-w1)*t
            wx,wz=_member_point(model,member,x); base=point(wx,wz)
            arrow=14.0+28.0*(abs(value)/peak)
            if load["direction"] == "FZ":
                tail=base+QPointF(0,-arrow if value<0 else arrow)
            else:
                tail=base+QPointF(-arrow if value>0 else arrow,0)
            bases.append(base); tails.append(tail); _draw_arrow(painter,tail,base,color,1)
        painter.setPen(QPen(QColor(color),1))
        for a,b in zip(tails,tails[1:]): painter.drawLine(a,b)
        label=f"{load['direction']} w={w1:.3g} kN/m" if abs(w1-w2)<1e-12 else f"{load['direction']} w={w1:.3g}->{w2:.3g} kN/m"
        painter.drawText(tails[len(tails)//2]+QPointF(5,-5),label)

    if model.get("self_weight"):
        sw_case=model.get("self_weight_case") or "DL"; f=_case_factor(model,case,sw_case)
        if abs(f)>1e-12:
            materials={row["id"]:row for row in model.get("materials",[])}
            sections={row["id"]:row for row in model.get("sections",[])}
            color=_case_color(model,sw_case,self_weight=True)
            for member in model.get("members",[]):
                rho=float(materials[member["material"]].get("rho",0.0)); area=float(sections[member["section"]]["A"])
                q=-rho*area*f
                L=math.hypot(nodes[member["j"]]["x"]-nodes[member["i"]]["x"],nodes[member["j"]]["z"]-nodes[member["i"]]["z"])
                for x in (0.2*L,0.5*L,0.8*L):
                    wx,wz=_member_point(model,member,x); base=point(wx,wz); tail=base+QPointF(0,-22)
                    _draw_arrow(painter,tail,base,color,1)

    painter.setFont(QFont(painter.font().family(), 10))
    painter.setPen(QPen(QColor("#1f2933"), 1))
    painter.drawText(QRectF(rect.left(), rect.top() - 24, rect.width(), 20), Qt.AlignmentFlag.AlignLeft, title_text)


def _draw_diagram_page(painter, model, result, case, quantity, rect):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPolygonF
    point, scale_model = _xy_mapper(model, rect)
    data = result["cases"][case]
    members = {m["id"]: m for m in model["members"]}
    nodes = {n["id"]: n for n in model["nodes"]}
    painter.setPen(QPen(QColor("#6b7280"), 1.5))
    for m in model["members"]:
        a,b=nodes[m["i"]],nodes[m["j"]]
        painter.drawLine(point(a["x"],a["z"]), point(b["x"],b["z"]))
    if quantity == "Reaction":
        peak = max((max(abs(v["Rx"]), abs(v["Rz"])) for v in data["nodes"].values()), default=0.0)
        k = 48.0 / peak if peak > 1e-12 else 0.0
        for nid,v in data["nodes"].items():
            n=nodes[nid]; base=point(n["x"],n["z"])
            if abs(v["Rx"])>1e-12:
                tail=base+QPointF(-v["Rx"]*k,0); _draw_arrow(painter,tail,base,"#cf7f20",1)
            if abs(v["Rz"])>1e-12:
                tail=base+QPointF(0,v["Rz"]*k); _draw_arrow(painter,tail,base,"#cf7f20",1)
            if abs(v["Rx"])+abs(v["Rz"])+abs(v["My"])>1e-12:
                painter.drawText(base+QPointF(6,-7),f"Rx {v['Rx']:.3g}  Rz {v['Rz']:.3g}  My {v['My']:.3g}")
        return
    if quantity == "Deflection":
        peak = max((abs(p["d"]) for mr in data["members"].values() for p in mr["plot"]), default=0.0)
        xmin, xmax, zmin, zmax = _bounds(model)
        span = max(xmax - xmin, zmax - zmin, 1.0)
        k_world = 0.16 * span / peak if peak > 1e-12 else 0.0
        painter.setPen(QPen(QColor("#8b5cb8"),2))
        for mid,mr in data["members"].items():
            m=members[mid]; nx,nz=_normal(model,m); pts=[]
            for row in mr["plot"]:
                x,z=_member_point(model,m,row["x"])
                # Positive anaStruct transverse d is displayed opposite the local
                # normal, matching the engineering viewport convention.
                pts.append(point(x - nx*row["d"]*k_world, z - nz*row["d"]*k_world))
            for a,b in zip(pts,pts[1:]): painter.drawLine(a,b)
        return
    if quantity == "Deformed":
        peak = max((math.hypot(p["ux"],p["uz"]) for mr in data["members"].values() for p in mr["plot"]), default=0.0)
        xmin, xmax, zmin, zmax = _bounds(model)
        span = max(xmax - xmin, zmax - zmin, 1.0)
        k_world = 0.16 * span / peak if peak > 1e-12 else 0.0
        painter.setPen(QPen(QColor("#8b5cb8"),2))
        for mid,mr in data["members"].items():
            m=members[mid]; pts=[]
            for row in mr["plot"]:
                x,z=_member_point(model,m,row["x"])
                pts.append(point(x+row["ux"]*k_world,z+row["uz"]*k_world))
            for a,b in zip(pts,pts[1:]): painter.drawLine(a,b)
        return
    peak = max((abs(row[quantity]) for mr in data["members"].values() for row in mr["plot"]), default=0.0)
    amp = min(rect.width(),rect.height()) * 0.18 / peak if peak > 1e-12 else 0.0
    pos=QColor("#3b82f6");pos.setAlpha(70); neg=QColor("#ef4444");neg.setAlpha(70)
    line_color={"N":"#244a7c","V":"#236b48","M":"#8f3030"}[quantity]
    for mid,mr in data["members"].items():
        m=members[mid]; nx,nz=_normal(model,m)
        rows=mr["plot"]
        base=[]; curve=[]
        for row in rows:
            x,z=_member_point(model,m,row["x"]); bp=point(x,z)
            # amp is in page pixels; offset directly in page coordinates after mapping the member normal.
            cp=QPointF(bp.x()+nx*row[quantity]*amp, bp.y()-nz*row[quantity]*amp)
            base.append(bp); curve.append(cp)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        for i in range(len(rows)-1):
            v0,v1=float(rows[i][quantity]),float(rows[i+1][quantity])
            if abs(v0)<1e-14 and abs(v1)<1e-14: continue
            parts=[(0.0,1.0,1 if (v0+v1)>=0 else -1)]
            if v0*v1<0:
                t=abs(v0)/(abs(v0)+abs(v1)); parts=[(0.0,t,1 if v0>=0 else -1),(t,1.0,1 if v1>=0 else -1)]
            for t0,t1,sgn in parts:
                def lerp(a,b,t): return QPointF(a.x()+(b.x()-a.x())*t,a.y()+(b.y()-a.y())*t)
                poly=QPolygonF([lerp(base[i],base[i+1],t0),lerp(curve[i],curve[i+1],t0),lerp(curve[i],curve[i+1],t1),lerp(base[i],base[i+1],t1)])
                painter.setBrush(QBrush(pos if sgn>=0 else neg)); painter.drawPolygon(poly)
        painter.setBrush(QBrush())
        painter.setPen(QPen(QColor(line_color),2))
        for a,b in zip(curve,curve[1:]): painter.drawLine(a,b)
        ex=mr.get("extrema",{}).get(quantity,{})
        unit={"N":"kN","V":"kN","M":"kN·m"}[quantity]
        for kind in ("min","max"):
            if kind not in ex: continue
            row=ex[kind]; x,z=_member_point(model,m,row["x"]); bp=point(x,z)
            cp=QPointF(bp.x()+nx*row["value"]*amp,bp.y()-nz*row["value"]*amp)
            painter.setPen(QPen(QColor("#1f2933"),1)); painter.drawText(cp+QPointF(5,-5),f"{row['value']:.4g} {unit}")


def export_pdf(path, model, result, case=None, viewport_image=None, viewport_options=None):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QFont, QPainter, QPageSize, QPdfWriter

    cases = [case] if case is not None else list(result.get("cases", {}))
    if not cases:
        raise ValueError("No analysis cases / combinations to export")
    for name in cases:
        if name not in result.get("cases", {}):
            raise ValueError(f"Unknown result case: {name}")

    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(96)
    painter = QPainter(writer)
    try:
        page_w, page_h = writer.width(), writer.height()
        margin = 48

        def title_at(y, text, size=16):
            font = QFont(); font.setPointSize(size); font.setBold(True); painter.setFont(font)
            painter.drawText(QRectF(margin, y, page_w - 2 * margin, 30), Qt.AlignmentFlag.AlignLeft, text)
            return y + 34

        def row_at(y, text, size=9, indent=0):
            font = QFont(); font.setPointSize(size); painter.setFont(font)
            painter.drawText(QRectF(margin + indent, y, page_w - 2 * margin - indent, 22), Qt.AlignmentFlag.AlignLeft, text)
            return y + 20

        # Cover / model overview.
        y = margin
        y = title_at(y, "GO 2D Structural — anaStruct Report", 17)
        y = row_at(y, f"Solver: {result.get('solver')} {result.get('solver_version')}")
        y = row_at(y, f"Cases / combinations: {', '.join(cases)}")
        y = row_at(y, f"Nodes: {len(model['nodes'])}    Members: {len(model['members'])}")
        y = row_at(y, "Analysis units: m, kN, kN·m")
        y = row_at(y, f"Coordinate mapping: {result.get('coordinate_map', '')}")
        y += 10
        graph = QRectF(margin, y + 20, page_w - 2 * margin, page_h - y - margin - 40)
        _draw_model_page(painter, model, result, cases[0], graph, "Analytical model + applied loads")

        # Capture the exact IngeTrazo viewport state when available. This gives
        # the report a visual record of what the engineer was reviewing.
        selected_view_case = (viewport_options or {}).get("case") or cases[0]
        active_only = bool((viewport_options or {}).get("active_only", True))
        if viewport_image is not None and not viewport_image.isNull():
            writer.newPage()
            painter.setFont(QFont(painter.font().family(), 14, QFont.Weight.Bold))
            painter.drawText(QRectF(margin, margin, page_w - 2 * margin, 26), Qt.AlignmentFlag.AlignLeft, "IngeTrazo viewport snapshot")
            painter.setFont(QFont(painter.font().family(), 9))
            diagram_name = (viewport_options or {}).get("diagram", "Model")
            painter.drawText(QRectF(margin, margin + 28, page_w - 2 * margin, 18), Qt.AlignmentFlag.AlignLeft, f"Case / combination: {selected_view_case}    Diagram: {diagram_name}")
            image_area = QRectF(margin, margin + 52, page_w - 2 * margin, page_h - 2 * margin - 150)
            painter.drawImage(_fit_image_rect(viewport_image, image_area), viewport_image)
            legend_rect = QRectF(margin, image_area.bottom() + 10, page_w - 2 * margin, 88)
            _draw_load_legend(painter, model, selected_view_case, legend_rect, active_only=active_only, options=viewport_options)

        for case_name in cases:
            data = result["cases"][case_name]
            # Case summary page.
            writer.newPage()
            y = margin
            y = title_at(y, f"Results summary — {case_name}", 15)
            y = title_at(y, "Support reactions", 11)
            for nid, values in data["nodes"].items():
                if abs(values["Rx"]) + abs(values["Rz"]) + abs(values["My"]) > 1e-9:
                    y = row_at(y, f"{nid}: Rx={values['Rx']:.5g} kN   Rz={values['Rz']:.5g} kN   My={values['My']:.5g} kN·m")
            y += 8
            y = title_at(y, "Member extrema", 11)
            units = {"N": "kN", "V": "kN", "M": "kN·m", "d": "m"}
            for mid, member in data["members"].items():
                y = row_at(y, mid, 9)
                for quantity, extrema in member["extrema"].items():
                    lo, hi = extrema["min"], extrema["max"]
                    y = row_at(y, f"{quantity}: min {lo['value']:.5g} {units[quantity]} @ {lo['x']:.4g} m | max {hi['value']:.5g} {units[quantity]} @ {hi['x']:.4g} m", 8, 12)
                    if y > page_h - margin - 80:
                        writer.newPage(); y = margin
                        y = title_at(y, f"Results summary — {case_name} (cont.)", 13)

            pages = [
                ("Analytical model + applied loads", "Model"),
                ("Axial force N", "N"),
                ("Shear force V", "V"),
                ("Bending moment M", "M"),
                ("Deflection", "Deflection"),
                ("Deformed shape", "Deformed"),
                ("Support reactions", "Reaction"),
            ]
            for heading, quantity in pages:
                writer.newPage()
                painter.setFont(QFont(painter.font().family(), 14, QFont.Weight.Bold))
                painter.drawText(QRectF(margin, margin, page_w - 2 * margin, 26), Qt.AlignmentFlag.AlignLeft, f"{heading} — {case_name}")
                graph_height = page_h - 2 * margin - (150 if quantity == "Model" else 70)
                graph = QRectF(margin, margin + 46, page_w - 2 * margin, graph_height)
                if quantity == "Model":
                    _draw_model_page(painter, model, result, case_name, graph, "Analytical model")
                    legend_rect = QRectF(margin, page_h - margin - 72, page_w - 2 * margin, 66)
                    _draw_load_legend(painter, model, case_name, legend_rect, active_only=True)
                else:
                    _draw_diagram_page(painter, model, result, case_name, quantity, graph)

        writer.newPage()
        y = margin
        y = title_at(y, "Scope / limitations", 13)
        y = row_at(y, "Linear elastic first-order 2D frame/truss analysis.")
        y = row_at(y, "No member capacity, nonlinear, P-Delta, shell/plate or code-compliance check.")
        y = row_at(y, "Engineering results are drafts and should be reviewed by a competent engineer before design decisions.")
    finally:
        painter.end()
    return str(path)
