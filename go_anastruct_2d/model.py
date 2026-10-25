"""Solver-independent JSON model for 2D XZ structural analysis."""
from __future__ import annotations
import copy
import hashlib
import json
import math
from .constants import MEMBER_TYPES, SCHEMA_VERSION, SPRING_DOF, SUPPORTS


class ModelError(ValueError):
    pass


def _finite(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ModelError(f"{label}: expected finite number")
    if positive and value <= 0:
        raise ModelError(f"{label}: expected positive number")


def member_length(model: dict, member: dict) -> float:
    nodes = {row["id"]: row for row in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    return math.hypot(b["x"] - a["x"], b["z"] - a["z"])


def validate(data: dict) -> dict:
    try:
        model = json.loads(json.dumps(data, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ModelError(f"Model must be JSON-safe: {exc}") from exc
    if not isinstance(model, dict) or model.get("schema") != SCHEMA_VERSION:
        raise ModelError(f"Unsupported schema; expected {SCHEMA_VERSION}")

    required = ("nodes", "members", "materials", "sections", "cases")
    for name in required:
        if name not in model or not isinstance(model[name], list):
            raise ModelError(f"Missing/invalid {name}")

    registries = {}
    for name in ("nodes", "members", "materials", "sections"):
        rows = model[name]
        ids = [row.get("id") for row in rows]
        if any(not isinstance(v, str) or not v.strip() for v in ids) or len(ids) != len(set(ids)):
            raise ModelError(f"{name}: duplicate/invalid IDs")
        registries[name] = {row["id"]: row for row in rows}
    if len(model["nodes"]) < 2 or not model["members"]:
        raise ModelError("At least two nodes and one member are required")

    positions = set()
    for node in model["nodes"]:
        _finite(node.get("x"), f"{node['id']}.x")
        _finite(node.get("z"), f"{node['id']}.z")
        pos = (node["x"], node["z"])
        if pos in positions:
            raise ModelError("Coincident nodes are not allowed")
        positions.add(pos)
        support = node.get("support", "Free")
        if support not in SUPPORTS:
            raise ModelError(f"Unknown support: {support}")
        springs = node.get("springs", {}) or {}
        if not isinstance(springs, dict):
            raise ModelError(f"{node['id']}.springs must be an object")
        if springs and support not in ("Free", "Spring"):
            raise ModelError("Use support Free/Spring when assigning nodal springs")
        for dof, stiffness in springs.items():
            if dof not in SPRING_DOF:
                raise ModelError(f"Unsupported 2D spring DOF: {dof}")
            _finite(stiffness, f"{node['id']}.springs.{dof}", positive=True)

    for material in model["materials"]:
        _finite(material.get("E"), f"{material['id']}.E", positive=True)
        _finite(material.get("rho", 0.0), f"{material['id']}.rho")
        if material.get("rho", 0.0) < 0:
            raise ModelError("rho cannot be negative")

    for section in model["sections"]:
        _finite(section.get("A"), f"{section['id']}.A", positive=True)
        _finite(section.get("Iz"), f"{section['id']}.Iz", positive=True)

    lengths = {}
    for member in model["members"]:
        if member.get("type", "Frame") not in MEMBER_TYPES:
            raise ModelError(f"Unknown member type: {member.get('type')}")
        if member.get("i") not in registries["nodes"] or member.get("j") not in registries["nodes"]:
            raise ModelError(f"{member['id']}: missing node reference")
        if member.get("material") not in registries["materials"]:
            raise ModelError(f"{member['id']}: missing material")
        if member.get("section") not in registries["sections"]:
            raise ModelError(f"{member['id']}: missing section")
        for key in ("release_i", "release_j"):
            if key in member and not isinstance(member[key], bool):
                raise ModelError(f"{member['id']}.{key} must be boolean")
        length = member_length(model, member)
        if length < 1e-9:
            raise ModelError("Zero-length member")
        lengths[member["id"]] = length

    cases = model["cases"]
    if not cases or len(cases) != len(set(cases)) or any(not isinstance(v, str) or not v.strip() for v in cases):
        raise ModelError("Invalid load cases")
    case_metadata = model.get("case_metadata", {}) or {}
    if not isinstance(case_metadata, dict):
        raise ModelError("case_metadata must be an object")
    for case, metadata in case_metadata.items():
        if case not in cases or not isinstance(metadata, dict):
            raise ModelError("Invalid case_metadata")
        if metadata.get("type") is not None and not isinstance(metadata.get("type"), str):
            raise ModelError(f"case_metadata {case}.type must be text")
        if metadata.get("description") is not None and not isinstance(metadata.get("description"), str):
            raise ModelError(f"case_metadata {case}.description must be text")

    combinations = model.get("combinations", {}) or {}
    if not isinstance(combinations, dict):
        raise ModelError("combinations must be an object")
    for name, factors in combinations.items():
        if not isinstance(name, str) or not name or not isinstance(factors, dict) or not factors:
            raise ModelError("Invalid load combination")
        for case, factor in factors.items():
            if case not in cases:
                raise ModelError(f"Combination {name}: unknown case {case}")
            _finite(factor, f"Combination {name}.{case}")

    combination_metadata = model.get("combination_metadata", {}) or {}
    if not isinstance(combination_metadata, dict):
        raise ModelError("combination_metadata must be an object")
    for name, metadata in combination_metadata.items():
        if name not in combinations or not isinstance(metadata, dict):
            raise ModelError("Invalid combination_metadata")
        if metadata.get("method") is not None and not isinstance(metadata.get("method"), str):
            raise ModelError(f"combination_metadata {name}.method must be text")

    for load in model.get("point_loads", []):
        if ("node" in load) == ("member" in load):
            raise ModelError("Point load needs exactly one node or member target")
        if load.get("case") not in cases:
            raise ModelError("Point load has unknown case")
        if load.get("direction") not in ("FX", "FZ", "MY"):
            raise ModelError("Point load direction must be FX/FZ/MY")
        _finite(load.get("value"), "point load value")
        if "node" in load:
            if load["node"] not in registries["nodes"]:
                raise ModelError("Point load has unknown node")
        else:
            if load["member"] not in registries["members"]:
                raise ModelError("Point load has unknown member")
            _finite(load.get("x"), "point load x")
            if not 0 <= load["x"] <= lengths[load["member"]]:
                raise ModelError("Point load is outside member")
            if registries["members"][load["member"]].get("type") == "Truss":
                raise ModelError("Apply truss loads at nodes")

    for load in model.get("distributed_loads", []):
        if load.get("member") not in registries["members"]:
            raise ModelError("Distributed load has unknown member")
        if load.get("case") not in cases or load.get("direction") not in ("FX", "FZ"):
            raise ModelError("Invalid distributed load case/direction")
        if registries["members"][load["member"]].get("type") == "Truss":
            raise ModelError("Apply truss loads at nodes")
        length = lengths[load["member"]]
        x1, x2 = load.get("x1", 0.0), load.get("x2", length)
        for key, value in (("w1", load.get("w1")), ("w2", load.get("w2")), ("x1", x1), ("x2", x2)):
            _finite(value, key)
        if not 0 <= x1 < x2 <= length:
            raise ModelError("Invalid distributed load extent")

    self_weight = model.get("self_weight", False)
    if not isinstance(self_weight, bool):
        raise ModelError("self_weight must be boolean")
    if self_weight:
        sw_case = model.get("self_weight_case")
        if sw_case is not None and sw_case not in cases:
            raise ModelError("Unknown self_weight_case")

    return model


def copy_model(data: dict) -> dict:
    return copy.deepcopy(validate(data))


def fingerprint(model: dict) -> str:
    checked = validate(model)
    raw = json.dumps(checked, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
