"""GO Engineering Core v0.1: shared read-only, nominal steel section properties.

This module and steel_sections_v1.json are *byte-identical vendored snapshots* in
GO Factory and GO anaStruct. The catalog is a transport format, not a design
approval. Do not couple this file to IngeTrazo, Qt, anaStruct or a 3D engine.
"""
from __future__ import annotations

import copy
import hashlib
from functools import lru_cache
import json
import math
from pathlib import Path

SCHEMA = "go-steel-sections/1"
CATALOG_VERSION = "0.1.0"
STATUS_NOMINAL = "NOMINAL_GEOMETRY_ONLY"
STATUS_UNSUPPORTED = "NO_FEM_PROPERTIES"


class CatalogError(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_catalog():
    filename = Path(__file__).with_name("steel_sections_v1.json")
    raw = json.loads(filename.read_text(encoding="utf-8"))
    if raw.get("schema") != SCHEMA or raw.get("catalog_version") != CATALOG_VERSION:
        raise CatalogError("Unsupported GO Steel Catalog schema or version")
    sections = raw.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise CatalogError("GO Steel Catalog has no sections")
    for key, row in sections.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            raise CatalogError("GO Steel Catalog entry is invalid")
        for field in ("h_m", "b_m", "tw_m", "tf_m", "t_m", "legacy_weight_kg_m"):
            v = row.get(field)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise CatalogError(f"{key}.{field}: invalid nominal dimension/weight")
    return raw


@lru_cache(maxsize=1)
def catalog_sha256():
    return hashlib.sha256(Path(__file__).with_name("steel_sections_v1.json").read_bytes()).hexdigest()


def catalog_info():
    doc = _load_catalog()
    return {
        "schema": doc["schema"], "version": doc["catalog_version"],
        "sha256": catalog_sha256(),
        "source": doc["source"], "count": len(doc["sections"]),
        "nominal_count": sum(row["analysis_status"] == STATUS_NOMINAL
                             for row in doc["sections"].values()),
    }


def section_names():
    return list(_load_catalog()["sections"])


def section_record(section_id):
    row = _load_catalog()["sections"].get(section_id)
    if row is None:
        raise CatalogError(f"Unknown GO Steel Catalog section: {section_id}")
    return copy.deepcopy({"id": section_id, **row, "catalog_version": CATALOG_VERSION})


def nominal_section_properties(section_id, *, axis, acknowledge_unverified=False):
    """Return A and strong/weak I for simple idealized profiles in SI units.

    Requires two explicit decisions: axis AND consent to use approximate
    unverified nominal geometry. Radius, fillets, actual rolling tolerances
    and net-section reductions are not accounted for. For H/WF flanges are
    ideal rectangles; RHS/SHS corners are ideal right angles.
    """
    if axis not in ("strong", "weak"):
        raise CatalogError("Select an explicit section bending axis: strong/weak")
    if acknowledge_unverified is not True:
        raise CatalogError("Section properties are nominal/unverified; explicit preview acceptance required")
    s = section_record(section_id)
    if s["analysis_status"] != STATUS_NOMINAL:
        raise CatalogError(
            f"{section_id} ({s['family']}) has no defensible v0.1 FEM properties; "
            "an independently verified engineering section is required"
        )
    h, b, tw, tf, t = (s[k] for k in ("h_m", "b_m", "tw_m", "tf_m", "t_m"))
    if s["family"] == "H":
        if min(h, b, tw, tf) <= 0 or 2 * tf >= h or tw >= b:
            raise CatalogError(f"{section_id}: invalid ideal H geometry")
        web_h = h - 2 * tf
        area = 2 * b * tf + web_h * tw
        strong = 2 * ((b * tf**3) / 12 + (b * tf) * ((h - tf) / 2)**2) + tw * web_h**3 / 12
        weak = 2 * tf * b**3 / 12 + web_h * tw**3 / 12
    elif s["family"] in ("RHS", "SHS"):
        if min(h, b, t) <= 0 or 2 * t >= min(h, b):
            raise CatalogError(f"{section_id}: invalid ideal hollow rectangle")
        hi, bi = h - 2*t, b - 2*t
        area = b*h - bi*hi
        strong = (b*h**3 - bi*hi**3)/12
        weak = (h*b**3 - hi*bi**3)/12
    elif s["family"] == "PIPE":
        if b <= 0 or t <= 0 or 2*t >= b:
            raise CatalogError(f"{section_id}: invalid ideal circular hollow geometry")
        d, di = b, b - 2*t
        area = math.pi * (d*d - di*di)/4
        strong = weak = math.pi * (d**4 - di**4)/64
    else:
        raise CatalogError(f"Unsupported nominal family {s['family']}")
    if not all(math.isfinite(v) and v > 0 for v in (area, strong, weak)):
        raise CatalogError(f"{section_id}: invalid derived nominal properties")
    # Rough mass calculated at 7850 kg/m3 for diagnostic comparison only.
    mass_est = area * 7850.0
    source_mass = s["legacy_weight_kg_m"]
    diff = None if source_mass <= 0 else 100.0 * (mass_est - source_mass) / source_mass
    return {
        "section_id": section_id, "catalog_version": CATALOG_VERSION,
        "family": s["family"], "axis": axis, "A_m2": area,
        "Ix_m4": strong, "Iy_m4": weak,
        "Iz_m4": strong if axis == "strong" else weak,
        "nominal_mass_kg_m": mass_est,
        "legacy_approx_mass_kg_m": source_mass,
        "mass_difference_pct": diff,
        "status": STATUS_NOMINAL, "verified": False,
        "warning": "Approximate idealized geometry only; not verified for engineering design",
    }


def section_identity(section_id):
    """Metadata for geometry/BOQ; deliberately no FEM A/I without explicit axis."""
    rec = section_record(section_id)
    return {
        "section_catalog_id": rec["id"],
        "section_catalog_version": CATALOG_VERSION,
        "section_catalog_sha256": catalog_sha256(),
        "section_property_status": rec["analysis_status"],
        "section_legacy_mass_status": "APPROXIMATE_UNVERIFIED",
    }
