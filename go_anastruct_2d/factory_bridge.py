"""Read GO Factory v0.3.1 member metadata; no GO Factory import is required.

The bridge is deliberately read-only: it never alters scene.groups, steel meshes,
component instances, layers, colors or BIM metadata.
"""
from __future__ import annotations

import math
from .examples import factory_gable_demo
from .model import member_length, validate
from .sections import starter_sections

FACTORY_KEY = "go_factory_generator"
ALIGN_TOLERANCE_M = 1e-5
DEFAULT_EXAMPLE = "11 — Gable Frame from GO Factory"


class FactoryImportError(ValueError):
    """Factory model is absent, inconsistent or requires engineering input."""


def _point(raw, label):
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise FactoryImportError(f"{label} must be an XYZ coordinate [m]")
    try:
        xyz = tuple(float(v) for v in raw)
    except (TypeError, ValueError) as exc:
        raise FactoryImportError(f"{label} has non-numeric coordinates") from exc
    if not all(math.isfinite(v) for v in xyz):
        raise FactoryImportError(f"{label} has non-finite coordinates")
    return xyz


def _close(a, b, tol=ALIGN_TOLERANCE_M):
    return math.dist(a, b) <= tol


def _cluster(values, tol=ALIGN_TOLERANCE_M):
    distinct = []
    for value in sorted(values):
        if not distinct or abs(value - distinct[-1]) > tol:
            distinct.append(value)
    return distinct


def members_from_scene(scene):
    """Return centerline metadata from the live IngeTrazo scene.

    GO Factory stores authoritative world coordinates under group.ext. No
    geometry traversal, mesh reconstruction, or undocumented APIs are used.
    """
    if scene is None:
        return []
    rows = []
    for group in getattr(scene, "groups", ()) or ():
        ext = getattr(group, "ext", None) or {}
        metadata = ext.get(FACTORY_KEY) if isinstance(ext, dict) else None
        if not isinstance(metadata, dict):
            continue
        if metadata.get("category") not in ("Column", "Rafter"):
            continue
        project = metadata.get("project")
        if not isinstance(project, str) or not project.strip():
            raise FactoryImportError("GO Factory member has no project name")
        mark = metadata.get("mark", "?")
        a = _point(metadata.get("start"), f"GO Factory {mark}.start")
        b = _point(metadata.get("end"), f"GO Factory {mark}.end")
        if _close(a, b):
            raise FactoryImportError(f"GO Factory {mark} has a zero-length centerline")
        section = metadata.get("section")
        if not isinstance(section, str) or not section.strip():
            raise FactoryImportError(f"GO Factory {mark} is missing its section name")
        rows.append({
            "project": project.strip(), "category": metadata["category"],
            "section": section.strip(), "mark": str(mark), "start": a, "end": b,
        })
    return rows


def project_stations(rows):
    """Map project names to the transverse frame stations of planar members."""
    projects = {}
    for row in rows:
        a, b = row["start"], row["end"]
        if abs(a[1] - b[1]) <= ALIGN_TOLERANCE_M:
            projects.setdefault(row["project"], []).append((a[1] + b[1]) / 2)
    return {name: _cluster(stations) for name, stations in sorted(projects.items())}


def _at_station(rows, project, y):
    return [
        row for row in rows if row["project"] == project
        and abs(row["start"][1] - y) <= ALIGN_TOLERANCE_M
        and abs(row["end"][1] - y) <= ALIGN_TOLERANCE_M
    ]


def _geometry(rows, project, frame_y):
    chosen = _at_station(rows, project, frame_y)
    columns = [r for r in chosen if r["category"] == "Column"]
    rafters = [r for r in chosen if r["category"] == "Rafter"]
    if len(columns) != 2 or len(rafters) != 2:
        raise FactoryImportError(
            f"{project} at Y={frame_y:g} m: expected 2 columns and 2 rafters "
            f"for an unsupported-free gable portal; found {len(columns)} "
            f"columns and {len(rafters)} rafters. Center columns, trusses, "
            "hip/cross-gable and segmented roofs require a separate adapter."
        )
    standing = []
    for col in columns:
        a, b = sorted((col["start"], col["end"]), key=lambda p: p[2])
        if abs(a[0] - b[0]) > ALIGN_TOLERANCE_M:
            raise FactoryImportError("Skewed/non-vertical column not supported")
        standing.append((a, b, col))
    standing.sort(key=lambda r: r[0][0])
    (lb, le, left_col), (rb, re, right_col) = standing
    if re[0] - le[0] < ALIGN_TOLERANCE_M:
        raise FactoryImportError("Invalid/zero width portal")
    if not math.isclose(lb[2], rb[2], abs_tol=ALIGN_TOLERANCE_M):
        raise FactoryImportError("Factory column bases have different elevations")
    if not math.isclose(le[2], re[2], abs_tol=ALIGN_TOLERANCE_M):
        raise FactoryImportError("Factory eaves have different elevations")

    def rafter_from(eave):
        matching = [
            (row, row["end"] if _close(row["start"], eave)
             else row["start"])
            for row in rafters
            if _close(row["start"], eave) or _close(row["end"], eave)
        ]
        if len(matching) != 1:
            raise FactoryImportError("Cannot uniquely connect a rafter to the column eave")
        return matching[0]

    left_raf, left_peak = rafter_from(le)
    right_raf, right_peak = rafter_from(re)
    if left_raf is right_raf or not _close(left_peak, right_peak):
        raise FactoryImportError("Roof rafters do not meet at a shared ridge")
    ridge = tuple((a+b)/2 for a, b in zip(left_peak, right_peak))
    if not le[0] < ridge[0] < re[0] or ridge[2] <= max(le[2], re[2]):
        raise FactoryImportError("Ridge is not above and between the eaves")
    named = (("N1", lb), ("N2", le), ("N3", ridge), ("N4", re), ("N5", rb))
    source = (left_col, left_raf, right_raf, right_col)
    return named, source


def required_section_mappings(rows, project, frame_y):
    """Only use exact existing IDs automatically; otherwise require user choice."""
    _, source = _geometry(rows, project, frame_y)
    known = {section["id"] for section in starter_sections()}
    return sorted({r["section"] for r in source if r["section"] not in known})


def build_analysis_from_factory(rows, project, frame_y, section_mapping=None,
                                support="Fixed"):
    """Create a validated local XZ FEM frame and precise world-space overlay info.

    The SectionSpec's nominal name alone does not establish authoritative A/Iz.
    Therefore unknown GO Factory steel sections MUST be explicitly mapped by
    the user to an existing analysis section. We never estimate section data.
    """
    frame_y = float(frame_y)
    if not math.isfinite(frame_y):
        raise FactoryImportError("Frame station must be finite")
    if support not in ("Fixed", "Pin"):
        raise FactoryImportError("Base restraint must be explicitly Fixed or Pin")
    named, sources = _geometry(rows, project, frame_y)
    existing = {row["id"] for row in starter_sections()}
    section_mapping = section_mapping or {}
    section_ids = []
    for record in sources:
        section = record["section"]
        target = section if section in existing else section_mapping.get(section)
        if target not in existing:
            raise FactoryImportError(
                f"Section {section} has no verified analytical A/Iz. "
                "Select an explicit analysis section mapping and verify properties."
            )
        section_ids.append(target)

    model = factory_gable_demo()
    coords = dict(named)
    model["nodes"] = [
        {"id": name, "x": point[0], "z": point[2],
         "support": support if name in ("N1", "N5") else "Free"}
        for name, point in named
    ]
    for member, section in zip(model["members"], section_ids):
        member["section"] = section
    for load in model["distributed_loads"]:
        load["x2"] = member_length(model, next(m for m in model["members"]
                                                  if m["id"] == load["member"]))
    model = validate(model)

    point_errors = []
    for key, point in named:
        centerline = (coords[key][0], frame_y, coords[key][2])
        point_errors.append(math.dist(point, centerline))
    err = max(point_errors)
    if err > ALIGN_TOLERANCE_M:
        raise FactoryImportError(f"Alignment error {err:g} m exceeds tolerance")
    placement = {
        "enabled": True, "frame_y": frame_y, "project": project,
        "source": FACTORY_KEY, "frame_stations": project_stations(rows).get(project, [frame_y]),
        "alignment_error_m": err,
        "markers": [[float(x), float(y), float(z)] for _, (x, y, z) in named],
        "section_mapping": {name: section_mapping[name] for name in section_mapping},
    }
    return model, placement
