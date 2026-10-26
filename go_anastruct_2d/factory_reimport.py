"""Preserve user-authored FEM parameters during a geometry-equivalent factory import."""
from __future__ import annotations
import copy
import math
from .model import validate


class ReimportNeedsConfirmation(ValueError):
    pass


def preserve_analysis_edits(previous, imported, *, retain_sections=True,
                            tolerance=1e-5):
    """Preserve loads, combos, material edits and end releases for matching frame.

    World Y is presentation-only. Different XZ geometry or topology requires
    explicit user confirmation to reset; never silently shift a load location.
    Base restraints follow the explicit current Fixed/Pin selector.
    """
    if previous is None:
        return validate(imported)
    old, new = validate(previous), validate(imported)
    old_nodes = {row["id"]: row for row in old["nodes"]}
    new_nodes = {row["id"]: row for row in new["nodes"]}
    old_members = {row["id"]: row for row in old["members"]}
    new_members = {row["id"]: row for row in new["members"]}
    if set(old_nodes) != set(new_nodes) or set(old_members) != set(new_members):
        raise ReimportNeedsConfirmation("Factory frame node/member IDs changed; confirm replacing edited loads")
    for nid, current in new_nodes.items():
        prev = old_nodes[nid]
        if math.hypot(current["x"] - prev["x"], current["z"] - prev["z"]) > tolerance:
            raise ReimportNeedsConfirmation("Factory frame geometry changed; manually review/reset load positions")
    for mid, current in new_members.items():
        prev = old_members[mid]
        if (current["i"], current["j"], current.get("type", "Frame")) != (
            prev["i"], prev["j"], prev.get("type", "Frame")
        ):
            raise ReimportNeedsConfirmation("Factory frame connectivity changed; confirm replacing edited analysis")
    fresh = copy.deepcopy(new)
    for key in (
        "cases", "case_metadata", "combinations", "combination_metadata",
        "point_loads", "distributed_loads", "self_weight", "self_weight_case",
        "materials",
    ):
        if key in old:
            fresh[key] = copy.deepcopy(old[key])

    # Preserve material IDs, analytical section edits and connection releases.
    # A changed explicit catalog selection will intentionally take precedence.
    old_section_rows = {row["id"]: row for row in old["sections"]}
    section_rows = {row["id"]: row for row in fresh["sections"]}
    if retain_sections:
        section_rows.update(copy.deepcopy(old_section_rows))
    for row in fresh["members"]:
        before = old_members[row["id"]]
        for key in ("release_i", "release_j"):
            if key in before:
                row[key] = before[key]
        if retain_sections:
            row["section"] = before["section"]
        if before.get("material") in {m["id"] for m in fresh["materials"]}:
            row["material"] = before["material"]
    fresh["sections"] = list(section_rows.values())
    return validate(fresh)
