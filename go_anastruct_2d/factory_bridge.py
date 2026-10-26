"""Read GO Factory v0.3.1 member metadata; no GO Factory import is required.

The bridge is deliberately read-only: it never alters scene.groups, steel meshes,
component instances, layers, colors or BIM metadata.
"""
from __future__ import annotations

import math
from .examples import factory_gable_demo
from .model import member_length, validate
from .sections import starter_sections
from .engineering_core import (
    CATALOG_VERSION, CatalogError, nominal_section_properties,
    section_record,
)

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
    """Require explicit engineering choices for every factory section name."""
    _, source = _geometry(rows, project, frame_y)
    return sorted({row["section"] for row in source})


def _mapping_section(section_name, selection, available):
    """Return (analysis section ID, added row or None).

    GO Factory's sketch/catalog section name is not a validated engineering
    cross-section. Only an explicit nominal-preview axis selection permits
    generating A/Iz. Manual starter mapping is for preview and MUST be steel.
    """
    if isinstance(selection, str):
        # Old preview projects used plain analysis section IDs; preserve only
        # explicit steel mappings, never an RC substitution for a steel member.
        selection = {"mode": "manual_starter", "section": selection,
                     "acknowledged": True}
    if not isinstance(selection, dict) or selection.get("acknowledged") is not True:
        raise FactoryImportError(
            f"{section_name}: select a section and acknowledge that its "
            "properties are not verified for structural design"
        )
    mode = selection.get("mode")
    if mode == "go_core_nominal":
        axis = selection.get("axis")
        try:
            p = nominal_section_properties(
                section_name, axis=axis, acknowledge_unverified=True
            )
        except CatalogError as exc:
            raise FactoryImportError(str(exc)) from exc
        section_id = f"GOCORE:{section_name}:{axis}"
        return section_id, {
            "id": section_id, "A": p["A_m2"], "Iz": p["Iz_m4"],
            "kind": "Steel", "catalog_id": section_name,
            "catalog_version": CATALOG_VERSION, "bending_axis": axis,
            "Ix": p["Ix_m4"], "Iy": p["Iy_m4"],
            "property_status": "NOMINAL_GEOMETRY_ONLY",
            "verified": False,
        }
    if mode == "manual_starter":
        dest = selection.get("section")
        row = available.get(dest)
        if row is None or row.get("kind") != "Steel":
            raise FactoryImportError(
                f"{section_name}: mapping to {dest!r} is not a known Steel "
                "analysis section. RC section substitutions are prohibited."
            )
        return dest, None
    raise FactoryImportError(f"{section_name}: unsupported section mapping mode {mode!r}")


def build_analysis_from_factory(rows, project, frame_y, section_mapping=None,
                                support="Fixed"):
    """Build a planar GO Factory FEM frame from exact member centerlines.

    All nominal sections require explicit engineering approval for demonstration
    use. Source metadata is read-only. The selected world Y is a display
    placement and does not change the 2D FEM fingerprint.
    """
    frame_y = float(frame_y)
    if not math.isfinite(frame_y):
        raise FactoryImportError("Frame station must be finite")
    if support not in ("Fixed", "Pin"):
        raise FactoryImportError("Base restraint must be explicitly Fixed or Pin")
    named, sources = _geometry(rows, project, frame_y)
    section_mapping = section_mapping or {}
    available = {row["id"]: row for row in starter_sections()}
    model = factory_gable_demo()
    existing = {row["id"] for row in model["sections"]}
    section_ids = []
    for record in sources:
        section_name = record["section"]
        if section_name not in section_mapping:
            raise FactoryImportError(
                f"Section {section_name} requires a GO Core nominal-axis "
                "preview choice or a verified manual Steel section mapping"
            )
        sid, newrow = _mapping_section(section_name, section_mapping[section_name], available)
        if newrow is not None and sid not in existing:
            model["sections"].append(newrow)
            existing.add(sid)
        section_ids.append(sid)

    model["nodes"] = [
        {"id": name, "x": point[0], "z": point[2],
         "support": support if name in ("N1", "N5") else "Free"}
        for name, point in named
    ]
    for member, sid in zip(model["members"], section_ids):
        member["section"] = sid
    for load in model["distributed_loads"]:
        load["x2"] = member_length(
            model,
            next(m for m in model["members"] if m["id"] == load["member"]),
        )
    model = validate(model)

    # Independently compare each FEM member's world-space endpoints with the
    # original factory member endpoints (order may be reversed). This checks
    # endpoint mapping, NOT whether a user manually moved meshes afterwards.
    by_node = {row["id"]: row for row in model["nodes"]}
    errors = []
    for member, source in zip(model["members"], sources):
        one = by_node[member["i"]]
        two = by_node[member["j"]]
        p = (one["x"], frame_y, one["z"])
        q = (two["x"], frame_y, two["z"])
        a, b = source["start"], source["end"]
        errors.append(min(max(math.dist(p, a), math.dist(q, b)),
                          max(math.dist(p, b), math.dist(q, a))))
    err = max(errors)
    if err > ALIGN_TOLERANCE_M:
        raise FactoryImportError(
            f"Factory endpoint-to-analysis alignment error {err:g} m exceeds tolerance"
        )
    placement = {
        "enabled": True, "frame_y": frame_y, "project": project,
        "source": FACTORY_KEY, "frame_stations": project_stations(rows).get(project, [frame_y]),
        "alignment_error_m": err,
        "alignment_source": "factory-centerline-metadata",
        "markers": [[float(x), float(y), float(z)] for _, (x, y, z) in named],
        "section_mapping": dict(section_mapping),
        "catalog_version": CATALOG_VERSION,
        "preview_unverified_properties": True,
    }
    return model, placement
