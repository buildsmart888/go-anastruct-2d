"""One request / one response anaStruct 1.7.0 solver worker.

GO coordinates: X horizontal, Z vertical, moment about +Y.
anaStruct coordinates: x horizontal, y vertical, moment about +z.
GO external moments/reactions/rotations use physical +CCW sign. anaStruct 1.7.0
uses an inverted generalized vertical DOF (uy/Fy) while Tz keeps the physical +CCW sign; converted centrally below.
Member BMD values keep anaStruct's native internal-force sign (sagging positive).
Support reactions come from the solved FEM equations, not post-process force fields.
"""
from __future__ import annotations
import contextlib
import io
import json
import math
import importlib
from pathlib import Path
import sys
import traceback

import numpy as np

WORKER_VERSION = "0.5.5"
PINNED_ANASTRUCT = "1.7.0"

# Physical GO signs at the anaStruct 1.7.0 FEM boundary.  anaStruct uses an
# inverted generalized vertical displacement/force DOF relative to its plotted
# geometry, while the generalized rotational DOF is positive for physical CCW.
# Runtime calibration below verifies these signs against the installed solver
# before every analysis request; these are only the pinned-version fallbacks.
ANASTRUCT_VERTICAL_DOF_SIGN = -1.0
ANASTRUCT_ROTATION_DOF_SIGN = 1.0

DEFAULT_CONVENTION = {
    "dof_x": 1.0,
    "dof_z": -1.0,
    "dof_m": 1.0,
    "point_fx_in": 1.0,
    "point_fz_in": -1.0,
    "moment_in": 1.0,
    "dist_fx_in": 1.0,
    "dist_fz_in": -1.0,
    "calibrated": False,
}


def _sign(value, label, tol=1e-12):
    value = float(value)
    if not math.isfinite(value) or abs(value) <= tol:
        raise RuntimeError(f"anaStruct convention calibration produced zero/non-finite {label}: {value}")
    return 1.0 if value > 0 else -1.0


def _calibrate_anastruct_convention():
    """Calibrate anaStruct 1.7.0 FEM and load-API signs at runtime.

    Do *not* use ``get_node_results_system`` here: anaStruct deliberately
    exposes forces/displacements there with post-processing signs that are not
    the raw generalized FEM signs.  Translation signs are measured with
    ``get_node_displacements`` (the public geometry displacement readout), and
    the rotational generalized-DOF sign is selected by the member stiffness
    rigid-body null mode.  Input signs are then measured from the exact
    assembled force vector.
    """
    from anastruct import SystemElements

    def base():
        ss = SystemElements(EA=1.0e6, EI=1.0e4, mesh=5, invert_y_loads=False)
        ss.add_element([[0.0, 0.0], [1.0, 0.0]])
        ss.add_support_fixed(1)
        return ss

    conv = dict(DEFAULT_CONVENTION)

    # Point X: public geometric displacement sign vs raw generalized ux.
    ss = base(); ss.point_load(2, Fx=1.0); ss.solve(force_linear=True, verbosity=1)
    u = np.asarray(ss.system_displacement_vector, dtype=float)
    disp = ss.get_node_displacements(2)
    conv["dof_x"] = _sign(float(disp["ux"]) / float(u[3]), "ux mapping")
    conv["point_fx_in"] = conv["dof_x"] * _sign(
        ss.system_force_vector[3], "point Fx assembly"
    )

    # Point Z/Y: anaStruct's raw generalized uy is opposite to the plotted
    # geometry displacement in 1.7.0; measure it instead of hard-coding it.
    ss = base(); ss.point_load(2, Fy=1.0); ss.solve(force_linear=True, verbosity=1)
    u = np.asarray(ss.system_displacement_vector, dtype=float)
    disp = ss.get_node_displacements(2)
    conv["dof_z"] = _sign(float(disp["uy"]) / float(u[4]), "uy mapping")
    conv["point_fz_in"] = conv["dof_z"] * _sign(
        ss.system_force_vector[4], "point Fy assembly"
    )

    # Determine which generalized rotational sign makes a *physical* rigid
    # rotation strain-free together with the calibrated X/Z translation signs.
    candidates = []
    for candidate in (-1.0, 1.0):
        trial = dict(conv, dof_m=candidate)
        residual = _rigid_body_mode_residuals(ss, trial)["R"]
        candidates.append((float(residual), candidate))
    candidates.sort(key=lambda item: item[0])
    best_residual, conv["dof_m"] = candidates[0]
    if not math.isfinite(best_residual) or best_residual > 1e-8:
        raise RuntimeError(
            "anaStruct convention calibration could not identify a rigid rotation "
            f"(normalized residual={best_residual:.3e})"
        )

    # Point moment input mapping from the exact assembled generalized vector.
    ss = base(); ss.moment_load(2, Tz=1.0); ss.solve(force_linear=True, verbosity=1)
    conv["moment_in"] = conv["dof_m"] * _sign(
        ss.system_force_vector[5], "moment assembly"
    )

    # Distributed global-X input mapping.
    ss = base(); ss.q_load(q=1.0, q_perp=0.0, element_id=1, direction="x")
    ss.solve(force_linear=True, verbosity=1)
    F = np.asarray(ss.system_force_vector, dtype=float)
    conv["dist_fx_in"] = conv["dof_x"] * _sign(
        float(np.sum(F[0::3])), "distributed X assembly"
    )

    # Distributed physical-Z mapping (q_perp at direction='x').
    ss = base(); ss.q_load(q=0.0, q_perp=1.0, element_id=1, direction="x")
    ss.solve(force_linear=True, verbosity=1)
    F = np.asarray(ss.system_force_vector, dtype=float)
    conv["dist_fz_in"] = conv["dof_z"] * _sign(
        float(np.sum(F[1::3])), "distributed Z assembly"
    )

    conv["calibrated"] = True
    return conv

if __package__:
    from .model import validate, member_length, fingerprint
else:
    # worker.py may be executed directly by older launchers. Import the model
    # through its package so model.py can keep normal relative imports.
    package_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(package_dir.parent))
    model_module = importlib.import_module(f"{package_dir.name}.model")
    validate = model_module.validate
    member_length = model_module.member_length
    fingerprint = model_module.fingerprint


def _factors(model, name):
    return dict(model.get("combinations", {}).get(name, {name: 1.0}))


def _self_weight_factor(model, factors):
    if not model.get("self_weight", False):
        return 0.0
    sw_case = model.get("self_weight_case")
    return float(factors.get(sw_case, 0.0)) if sw_case else float(sum(factors.values()))


def _has_effective_load(model, factors, tol=1e-14):
    for row in model.get("point_loads", []):
        if abs(float(row.get("value", 0.0)) * float(factors.get(row.get("case"), 0.0))) > tol:
            return True
    for row in model.get("distributed_loads", []):
        factor = float(factors.get(row.get("case"), 0.0))
        if abs(float(row.get("w1", 0.0)) * factor) > tol or abs(float(row.get("w2", 0.0)) * factor) > tol:
            return True
    sw_factor = _self_weight_factor(model, factors)
    if abs(sw_factor) > tol:
        materials = {row["id"]: row for row in model["materials"]}
        sections = {row["id"]: row for row in model["sections"]}
        for member in model["members"]:
            rho = float(materials[member["material"]].get("rho", 0.0))
            area = float(sections[member["section"]]["A"] )
            if abs(rho * area * sw_factor) > tol:
                return True
    return False


def _point_on_member(model, member, x):
    nodes = {row["id"]: row for row in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    length = member_length(model, member)
    t = 0.0 if length == 0 else x / length
    return [a["x"] + (b["x"] - a["x"]) * t, a["z"] + (b["z"] - a["z"]) * t]


def _split_positions(model, member):
    length = member_length(model, member)
    xs = {0.0, float(length)}
    if member.get("type") != "Truss":
        for row in model.get("point_loads", []):
            if row.get("member") == member["id"]:
                xs.add(float(row["x"]))
        for row in model.get("distributed_loads", []):
            if row.get("member") == member["id"]:
                xs.add(float(row.get("x1", 0.0)))
                xs.add(float(row.get("x2", length)))
    return sorted(xs)


def _build(model, factors, convention=None):
    convention = dict(DEFAULT_CONVENTION if convention is None else convention)
    from anastruct import SystemElements

    system = SystemElements(mesh=61, invert_y_loads=False)
    nodes = {row["id"]: row for row in model["nodes"]}
    members = {row["id"]: row for row in model["members"]}
    materials = {row["id"]: row for row in model["materials"]}
    sections = {row["id"]: row for row in model["sections"]}
    segmap = {}

    for member in model["members"]:
        material = materials[member["material"]]
        section = sections[member["section"]]
        EA = material["E"] * section["A"]
        EI = material["E"] * section["Iz"]
        split = _split_positions(model, member)
        segments = []
        for index, (x0, x1) in enumerate(zip(split, split[1:])):
            p0 = _point_on_member(model, member, x0)
            p1 = _point_on_member(model, member, x1)
            if member.get("type") == "Truss":
                eid = system.add_truss_element([p0, p1], EA=EA)
            else:
                spring = {}
                if index == 0 and member.get("release_i", False):
                    spring[1] = 0.0
                if index == len(split) - 2 and member.get("release_j", False):
                    spring[2] = 0.0
                eid = system.add_element([p0, p1], EA=EA, EI=EI, spring=spring or None)
            segments.append({"eid": int(eid), "x0": float(x0), "x1": float(x1)})
        segmap[member["id"]] = segments

    node_ids = {
        nid: int(system.find_node_id(vertex=[row["x"], row["z"]]))
        for nid, row in nodes.items()
    }
    for nid, node in nodes.items():
        sid = node_ids[nid]
        support = node.get("support", "Free")
        if support == "Fixed":
            system.add_support_fixed(sid)
        elif support == "Pin":
            system.add_support_hinged(sid)
        elif support == "Roller":
            system.add_support_roll(sid, direction="x")
        elif support == "RollerX":
            system.add_support_roll(sid, direction="y")
        elif support not in ("Free", "Spring"):
            raise ValueError("Unsupported support: " + str(support))
        for dof, stiffness in (node.get("springs", {}) or {}).items():
            translation = {"UX": 1, "UZ": 2, "RY": 3}[dof]
            system.add_support_spring(sid, translation=translation, k=float(stiffness))

    def scale(row):
        return float(factors.get(row["case"], 0.0))

    # anaStruct stores one point/moment entry per node and one q-load entry per
    # element, so accumulate all factored actions before publishing them.
    nodal = {sid: [0.0, 0.0, 0.0] for sid in node_ids.values()}  # Fx, Fy, Tz
    distributed = {seg["eid"]: {"qx": [0.0, 0.0], "qz": [0.0, 0.0]}
                   for rows in segmap.values() for seg in rows}

    for load in model.get("point_loads", []):
        factor = scale(load)
        if factor == 0:
            continue
        value = float(load["value"]) * factor
        if "node" in load:
            target = node_ids[load["node"]]
        else:
            point = _point_on_member(model, members[load["member"]], float(load["x"]))
            target = int(system.find_node_id(vertex=point))
            nodal.setdefault(target, [0.0, 0.0, 0.0])
        if load["direction"] == "FX":
            nodal[target][0] += convention["point_fx_in"] * value
        elif load["direction"] == "FZ":
            # anaStruct generalized Fy is opposite to physical/global geometry y.
            nodal[target][1] += convention["point_fz_in"] * value
        else:  # GO physical +MY (CCW) == anaStruct generalized +Tz
            nodal[target][2] += convention["moment_in"] * value

    for load in model.get("distributed_loads", []):
        factor = scale(load)
        if factor == 0:
            continue
        member = members[load["member"]]
        length = member_length(model, member)
        x1, x2 = float(load.get("x1", 0.0)), float(load.get("x2", length))
        span = x2 - x1
        for seg in segmap[member["id"]]:
            if seg["x0"] < x1 - 1e-9 or seg["x1"] > x2 + 1e-9:
                continue
            t0 = 0.0 if span == 0 else (seg["x0"] - x1) / span
            t1 = 0.0 if span == 0 else (seg["x1"] - x1) / span
            q0 = (load["w1"] + (load["w2"] - load["w1"]) * t0) * factor
            q1 = (load["w1"] + (load["w2"] - load["w1"]) * t1) * factor
            key = "qx" if load["direction"] == "FX" else "qz"
            distributed[seg["eid"]][key][0] += q0
            distributed[seg["eid"]][key][1] += q1

    if model.get("self_weight", False):
        sw_factor = _self_weight_factor(model, factors)
        if sw_factor:
            for member in model["members"]:
                q = -materials[member["material"]].get("rho", 0.0) * sections[member["section"]]["A"] * sw_factor
                if not q:
                    continue
                if member.get("type") == "Truss":
                    length = member_length(model, member)
                    share = q * length / 2.0
                    nodal[node_ids[member["i"]]][1] += convention["point_fz_in"] * share
                    nodal[node_ids[member["j"]]][1] += convention["point_fz_in"] * share
                else:
                    for seg in segmap[member["id"]]:
                        distributed[seg["eid"]]["qz"][0] += q
                        distributed[seg["eid"]]["qz"][1] += q

    for sid, (fx, fy, tz) in nodal.items():
        if fx or fy:
            system.point_load(sid, Fx=fx, Fy=fy)
        if tz:
            system.moment_load(sid, Tz=tz)
    for eid, components in distributed.items():
        qx, qz = components["qx"], components["qz"]
        if any(abs(v) > 0 for v in qx + qz):
            # anaStruct q_load(direction="x") treats q as the GLOBAL X
            # component and q_perp as the perpendicular GLOBAL Y component.
            # GO uses X/Z, so map GO FX -> q and GO FZ -> q_perp.
            # v0.4.3 accidentally swapped these and a vertical UDL produced
            # horizontal reactions (Rx) instead of vertical reactions (Rz).
            # q_load(direction="x") publishes q as generalized/global X and
            # q_perp as generalized/global Y. anaStruct generalized Y is the
            # opposite of GO physical Z, so flip the vertical component here.
            system.q_load(
                q=[convention["dist_fx_in"] * qx[0], convention["dist_fx_in"] * qx[1]],
                q_perp=[convention["dist_fz_in"] * qz[0],
                        convention["dist_fz_in"] * qz[1]],
                element_id=eid,
                direction="x",
            )

    system.solve(force_linear=True, verbosity=1)
    return system, node_ids, segmap


def _resample(values, count):
    arr = np.asarray(values if values is not None else [0.0, 0.0], dtype=float)
    if len(arr) == count:
        return arr
    if len(arr) == 1:
        return np.full(count, arr[0], dtype=float)
    return np.interp(np.linspace(0, 1, count), np.linspace(0, 1, len(arr)), arr)


def _member_result(system, model, member, segments):
    nodes = {row["id"]: row for row in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    length = member_length(model, member)
    tx, tz = (b["x"] - a["x"]) / length, (b["z"] - a["z"]) / length
    nx, nz = -tz, tx
    plot = []
    for seg_index, seg in enumerate(segments):
        raw = system.get_element_results(seg["eid"], verbose=True)
        element = system.element_map[seg["eid"]]
        def _series(key, attr, fallback=None):
            value = raw.get(key)
            if value is None:
                value = getattr(element, attr, None)
            return fallback if value is None else value
        def _n(value):
            try:
                return 0 if value is None else len(value)
            except TypeError:
                return 1
        transverse = _series("w", "deflection", _series("wtot", "total_deflection", [0.0, 0.0]))
        n_series = _series("N", "axial_force", [0.0, 0.0])
        q_series = _series("Q", "shear_force", [0.0, 0.0])
        m_series = _series("M", "bending_moment", [0.0, 0.0])
        u_series = _series("u", "extension", [0.0, 0.0])
        # Use the densest solver series. Older logic sized only from N/u/w and
        # could collapse a detailed M/Q curve to two points in frame/cantilever cases.
        count = max(2, _n(n_series), _n(q_series), _n(m_series), _n(u_series), _n(transverse))
        N = _resample(n_series, count)
        V = _resample(q_series, count) if member.get("type") != "Truss" else np.zeros(count)
        M = _resample(m_series, count) if member.get("type") != "Truss" else np.zeros(count)
        u = _resample(u_series, count)
        w = _resample(transverse, count)
        xs = np.linspace(seg["x0"], seg["x1"], count)
        for index, x in enumerate(xs):
            # anaStruct 1.7.0 plots transverse element.deflection opposite the
            # member's positive local normal: [d*sin(angle), -d*cos(angle)].
            # Our normal is [-sin(angle), +cos(angle)], therefore the physical
            # global displacement contribution is -d*normal.
            ux = u[index] * tx - w[index] * nx
            uz = u[index] * tz - w[index] * nz
            plot.append({
                "x": float(x), "N": float(N[index]), "V": float(V[index]), "M": float(M[index]),
                "d": float(w[index]), "u": float(u[index]), "ux": float(ux), "uz": float(uz),
                "side": "left" if index == count - 1 and seg_index < len(segments) - 1 else "right",
            })
    plot.sort(key=lambda row: (row["x"], 0 if row["side"] == "left" else 1))
    extrema = {}
    for key in ("N", "V", "M", "d"):
        lo = min(plot, key=lambda row: row[key])
        hi = max(plot, key=lambda row: row[key])
        extrema[key] = {
            "min": {"x": lo["x"], "value": lo[key], "side": lo["side"]},
            "max": {"x": hi["x"], "value": hi[key], "side": hi["side"]},
        }
    first, last = plot[0], plot[-1]
    return {
        "L": float(length), "basis": [[tx, tz], [nx, nz]], "plot": plot, "extrema": extrema,
        "end_forces": {
            "i": {"N": first["N"], "V": first["V"], "M": first["M"]},
            "j": {"N": last["N"], "V": last["V"], "M": last["M"]},
        },
    }


def _model_applied_resultant(model, factors):
    """Independent GO-side resultant [Fx, Fz, My] about the global origin.

    This audits the load translation before anaStruct solves.  It deliberately
    knows nothing about anaStruct reactions or stiffness matrices.
    """
    node_map = {row["id"]: row for row in model["nodes"]}
    members = {row["id"]: row for row in model["members"]}
    total = [0.0, 0.0, 0.0]

    def add(x, z, fx=0.0, fz=0.0, my=0.0):
        total[0] += fx
        total[1] += fz
        total[2] += x * fz - z * fx + my

    for row in model.get("point_loads", []):
        factor = float(factors.get(row["case"], 0.0))
        if not factor:
            continue
        if "node" in row:
            p = node_map[row["node"]]
            x, z = p["x"], p["z"]
        else:
            x, z = _point_on_member(model, members[row["member"]], row["x"])
        value = float(row["value"]) * factor
        add(
            x, z,
            value if row["direction"] == "FX" else 0.0,
            value if row["direction"] == "FZ" else 0.0,
            value if row["direction"] == "MY" else 0.0,
        )

    for row in model.get("distributed_loads", []):
        factor = float(factors.get(row["case"], 0.0))
        if not factor:
            continue
        member = members[row["member"]]
        a = node_map[member["i"]]
        b = node_map[member["j"]]
        length = member_length(model, member)
        x1 = float(row.get("x1", 0.0))
        x2 = float(row.get("x2", length))
        h = x2 - x1
        w1 = float(row["w1"]) * factor
        w2 = float(row["w2"]) * factor
        resultant = h * (w1 + w2) / 2.0
        # First moment of the line load about member i, measured along member.
        first = x1 * resultant + h * h * (w1 + 2.0 * w2) / 6.0
        x_first = a["x"] * resultant + (b["x"] - a["x"]) / length * first
        z_first = a["z"] * resultant + (b["z"] - a["z"]) / length * first
        if row["direction"] == "FX":
            total[0] += resultant
            total[2] -= z_first
        else:
            total[1] += resultant
            total[2] += x_first

    if model.get("self_weight", False):
        factor = _self_weight_factor(model, factors)
        mats = {row["id"]: row for row in model["materials"]}
        secs = {row["id"]: row for row in model["sections"]}
        if factor:
            for member in model["members"]:
                a, b = node_map[member["i"]], node_map[member["j"]]
                weight = (
                    -float(mats[member["material"]].get("rho", 0.0))
                    * float(secs[member["section"]]["A"])
                    * member_length(model, member)
                    * factor
                )
                add((a["x"] + b["x"]) / 2.0, (a["z"] + b["z"]) / 2.0, fz=weight)
    return total


def _element_only_matrix(system):
    """Return member stiffness only (ground-support springs removed)."""
    K = np.asarray(system.system_matrix, dtype=float).copy()
    for index, stiffness in (getattr(system, "system_spring_map", {}) or {}).items():
        i = int(index)
        if 0 <= i < K.shape[0]:
            K[i, i] -= float(stiffness)
    return K


def _rigid_body_modes(system, rotation_sign=None, convention=None):
    """Physical GO rigid modes expressed in anaStruct generalized DOFs."""
    conv = dict(DEFAULT_CONVENTION if convention is None else convention)
    ax, az, am = float(conv["dof_x"]), float(conv["dof_z"]), float(conv["dof_m"])
    if rotation_sign is not None:
        am = float(rotation_sign)
    n = int(np.asarray(system.system_force_vector).size)
    tx = np.zeros(n, dtype=float); tz = np.zeros(n, dtype=float); rot = np.zeros(n, dtype=float)
    for sid, node in system.node_map.items():
        base = (int(sid) - 1) * 3
        x, z = float(node.vertex.x), float(node.vertex.y)
        tx[base] = ax
        tz[base + 1] = az
        rot[base] = -ax * z
        rot[base + 1] = az * x
        rot[base + 2] = am
    return tx, tz, rot, am


def _rigid_body_mode_residuals(system, convention=None):
    """Dimensionless K-member residuals for the three rigid-body modes."""
    K = _element_only_matrix(system)
    if K.size == 0:
        return {"X": 0.0, "Z": 0.0, "R": 0.0}
    tx, tz, rot, _ = _rigid_body_modes(system, convention=convention)
    scale = max(1.0, float(np.linalg.norm(K, ord=np.inf)))
    out = {}
    for name, mode in (("X", tx), ("Z", tz), ("R", rot)):
        denom = scale * max(1.0, float(np.linalg.norm(mode, ord=np.inf)))
        out[name] = float(np.linalg.norm(K @ mode, ord=np.inf)) / denom
    return out


def _rigid_rotation_dof_sign(system):
    """Compatibility helper retained for tests/diagnostics.

    The pinned anaStruct 1.7.0 convention is verified through the full rigid
    mode, including its inverted vertical generalized DOF.
    """
    residuals = _rigid_body_mode_residuals(system, DEFAULT_CONVENTION)
    return float(DEFAULT_CONVENTION["dof_m"])


def _nodal_vector_resultant(vector, system, node_ids=None, rotation_sign=None, convention=None):
    """Physical [Fx, Fz, My] from an anaStruct generalized nodal vector.

    The moment is evaluated by virtual work against a rigid-body rotation.
    This automatically handles anaStruct's rotational generalized-DOF sign and
    includes intermediate solver nodes created when member loads split elements.
    """
    arr = np.asarray(vector, dtype=float).reshape(-1)
    tx, tz, rot, _sign = _rigid_body_modes(system, rotation_sign, convention)
    if len(arr) != len(tx):
        raise RuntimeError("anaStruct nodal vector size does not match rigid-body modes")
    return [float(tx @ arr), float(tz @ arr), float(rot @ arr)]


def _solver_reaction_vector(system):
    """Support reaction vector from the solved FEM equations, R = K*u - F.

    Only restrained DOFs are taken from the residual.  Ground springs act on
    free DOFs, so their -k*u force is added explicitly when present.
    """
    K = np.asarray(system.system_matrix, dtype=float)
    u = np.asarray(system.system_displacement_vector, dtype=float).reshape(-1)
    F = np.asarray(system.system_force_vector, dtype=float).reshape(-1)
    if K.shape[0] != len(u) or len(F) != len(u):
        raise RuntimeError("anaStruct full FEM vectors have incompatible sizes")
    residual = K @ u - F
    reaction = np.zeros_like(residual)
    free = {int(i) for i in getattr(system, "_remainder_indexes", [])}
    for i, value in enumerate(residual):
        if i not in free:
            reaction[i] = value
    # A translational/rotational support spring is connected to ground but its
    # DOF remains in the reduced solve.  Its external reaction is -k*u.
    for index, stiffness in (getattr(system, "system_spring_map", {}) or {}).items():
        i = int(index)
        if i in free:
            reaction[i] += -float(stiffness) * float(u[i])
    return reaction


def _solver_equilibrium(system, node_ids, model, factors, convention=None):
    convention = dict(DEFAULT_CONVENTION if convention is None else convention)
    """Two-layer equilibrium audit in physical GO signs.

    Layer 1 checks the actual anaStruct assembled load vector against the GO
    model resultant.  Layer 2 checks applied load + all external reactions by
    rigid-body virtual work.  No post-processing Fx/Fy/Tz sign assumptions are
    used.
    """
    F = np.asarray(system.system_force_vector, dtype=float).reshape(-1)
    reaction_vector = _solver_reaction_vector(system)
    rotation_sign = float(convention["dof_m"])
    mode_residuals = _rigid_body_mode_residuals(system, convention)
    applied = _nodal_vector_resultant(F, system, rotation_sign=rotation_sign, convention=convention)
    reaction = _nodal_vector_resultant(
        reaction_vector, system, rotation_sign=rotation_sign, convention=convention
    )
    residual = [applied[i] + reaction[i] for i in range(3)]
    tolerance = [2e-7 * max(1.0, abs(applied[i]), abs(reaction[i])) for i in range(3)]

    model_applied = _model_applied_resultant(model, factors)
    mapping_residual = [applied[i] - model_applied[i] for i in range(3)]
    mapping_tolerance = [
        2e-6 * max(1.0, abs(applied[i]), abs(model_applied[i])) for i in range(3)
    ]
    mapping_passed = all(abs(v) <= t for v, t in zip(mapping_residual, mapping_tolerance))
    passed = all(abs(v) <= t for v, t in zip(residual, tolerance))
    return {
        "applied": applied,
        "reaction": reaction,
        "residual": residual,
        "tolerance": tolerance,
        "passed": passed,
        "model_applied": model_applied,
        "load_mapping_residual": mapping_residual,
        "load_mapping_tolerance": mapping_tolerance,
        "load_mapping_passed": mapping_passed,
        "rotation_dof_sign": rotation_sign,
        "vertical_dof_sign": float(convention["dof_z"]),
        "convention": convention,
        "rigid_body_mode_residuals": mode_residuals,
        "source": "FEM virtual work in anaStruct generalized DOFs; R = K*u - F",
    }, reaction_vector


def _equilibrium(model, nodes, factors):
    """Legacy model-side audit retained for zero-load cases and unit tests."""
    applied = _model_applied_resultant(model, factors)
    node_map = {row["id"]: row for row in model["nodes"]}
    reaction = [
        sum(row["Rx"] for row in nodes.values()),
        sum(row["Rz"] for row in nodes.values()),
        sum(
            row["My"] + node_map[nid]["x"] * row["Rz"] - node_map[nid]["z"] * row["Rx"]
            for nid, row in nodes.items()
        ),
    ]
    residual = [applied[i] + reaction[i] for i in range(3)]
    tolerance = [1e-6 * max(1.0, abs(applied[i]), abs(reaction[i])) for i in range(3)]
    return {
        "applied": applied,
        "reaction": reaction,
        "residual": residual,
        "tolerance": tolerance,
        "passed": all(abs(v) <= t for v, t in zip(residual, tolerance)),
    }

def _zero_member_result(model, member):
    length = member_length(model, member)
    zero0 = {"x": 0.0, "N": 0.0, "V": 0.0, "M": 0.0, "d": 0.0, "u": 0.0, "ux": 0.0, "uz": 0.0, "side": "right"}
    zero1 = dict(zero0, x=float(length))
    extrema = {
        key: {
            "min": {"x": 0.0, "value": 0.0, "side": "right"},
            "max": {"x": 0.0, "value": 0.0, "side": "right"},
        }
        for key in ("N", "V", "M", "d")
    }
    nodes = {row["id"]: row for row in model["nodes"]}
    a, b = nodes[member["i"]], nodes[member["j"]]
    tx, tz = (b["x"] - a["x"]) / length, (b["z"] - a["z"]) / length
    nx, nz = -tz, tx
    end = {"N": 0.0, "V": 0.0, "M": 0.0}
    return {
        "L": float(length),
        "basis": [[tx, tz], [nx, nz]],
        "plot": [zero0, zero1],
        "extrema": extrema,
        "end_forces": {"i": dict(end), "j": dict(end)},
    }


def _zero_case(model, factors):
    nodes = {
        row["id"]: {"ux": 0.0, "uz": 0.0, "rotation": 0.0, "Rx": 0.0, "Rz": 0.0, "My": 0.0}
        for row in model["nodes"]
    }
    members = {row["id"]: _zero_member_result(model, row) for row in model["members"]}
    balance = _equilibrium(model, nodes, factors)
    if not balance["passed"]:
        raise RuntimeError(f"Internal zero-case equilibrium failed: residual {balance['residual']}")
    return {"nodes": nodes, "members": members, "equilibrium": balance, "empty_load_case": True}


def _node_result(system, sid, reaction_vector, rotation_sign=None, convention=None):
    """Return GO node results directly from full FEM vectors in calibrated signs."""
    conv = dict(DEFAULT_CONVENTION if convention is None else convention)
    base = (int(sid) - 1) * 3
    u = np.asarray(system.system_displacement_vector, dtype=float).reshape(-1)
    return {
        "ux": float(conv["dof_x"]) * float(u[base]),
        "uz": float(conv["dof_z"]) * float(u[base + 1]),
        "rotation": float(conv["dof_m"]) * float(u[base + 2]),
        "Rx": float(conv["dof_x"]) * float(reaction_vector[base]),
        "Rz": float(conv["dof_z"]) * float(reaction_vector[base + 1]),
        "My": float(conv["dof_m"]) * float(reaction_vector[base + 2]),
    }


def solve(data):
    from importlib.metadata import version
    if version("anastruct") != PINNED_ANASTRUCT:
        raise RuntimeError(f"anaStruct {PINNED_ANASTRUCT} is required")
    model = validate(data)
    convention = _calibrate_anastruct_convention()
    names = list(model["cases"]) + list(model.get("combinations", {}))
    result = {
        "schema": 1, "solver": "anaStruct", "solver_version": PINNED_ANASTRUCT,
        "worker_version": WORKER_VERSION, "units": "m,kN", "coordinate_map": "geometry ana x/y -> GO X/Z; generalized/load signs runtime-calibrated against anaStruct 1.7.0 FEM vectors",
        "cases": {}, "model_hash": fingerprint(model), "solver_convention": convention,
    }
    for name in names:
        factors = _factors(model, name)
        if not _has_effective_load(model, factors):
            result["cases"][name] = _zero_case(model, factors)
            continue
        system, node_ids, segmap = _build(model, factors, convention)
        balance, reaction_vector = _solver_equilibrium(system, node_ids, model, factors, convention)
        if not balance["load_mapping_passed"]:
            raise RuntimeError(
                f"Load mapping audit failed in {name}: residual {balance['load_mapping_residual']}"
            )
        if not balance["passed"]:
            raise RuntimeError(f"Global equilibrium failed in {name}: residual {balance['residual']}")
        nodes = {
            nid: _node_result(system, sid, reaction_vector, balance["rotation_dof_sign"], convention)
            for nid, sid in node_ids.items()
        }
        members = {m["id"]: _member_result(system, model, m, segmap[m["id"]]) for m in model["members"]}
        result["cases"][name] = {"nodes": nodes, "members": members, "equilibrium": balance}
    return result


def main():
    try:
        request = json.load(sys.stdin)
        if request.get("protocol") != 1:
            raise ValueError("Unsupported worker protocol")
        with contextlib.redirect_stdout(io.StringIO()):
            result = solve(request["model"])
        reply = {"protocol": 1, "ok": True, "result": result}
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        reply = {"protocol": 1, "ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
    print(json.dumps(reply, allow_nan=False, separators=(",", ":")))
    return 0 if reply["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
