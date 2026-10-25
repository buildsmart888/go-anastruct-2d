from __future__ import annotations
from .sections import starter_sections


def _base(cases=None, combinations=None, case_metadata=None, combo_metadata=None):
    cases = list(cases or ["DL", "LL"])
    combinations = combinations or {"ULS": {"DL": 1.2, "LL": 1.6}}
    case_metadata = case_metadata or {
        "DL": {"type": "Dead", "description": "Dead load / self-weight"},
        "LL": {"type": "Live", "description": "Live load"},
    }
    combo_metadata = combo_metadata or {name: {"method": "LRFD"} for name in combinations}
    return {
        "schema": 1,
        "version": 6,
        "self_weight": True,
        "self_weight_case": "DL" if "DL" in cases else cases[0],
        "materials": [
            {"id": "Steel", "E": 200_000_000.0, "rho": 76.98},
            {"id": "Concrete", "E": 30_000_000.0, "rho": 24.0},
        ],
        "sections": starter_sections(),
        "cases": cases,
        "case_metadata": case_metadata,
        "combinations": combinations,
        "combination_metadata": combo_metadata,
        "point_loads": [],
        "distributed_loads": [],
    }


def _portal_combos():
    cases = ["DL", "LL", "WL"]
    combos = {
        "ULS": {"DL": 1.2, "LL": 1.6},
        "ULS-G": {"DL": 1.4, "LL": 1.4},
        "ULS-W": {"DL": 1.2, "LL": 1.0, "WL": 1.0},
        "SLS": {"DL": 1.0, "LL": 1.0, "WL": 0.6},
    }
    case_metadata = {
        "DL": {"type": "Dead", "description": "Dead load + self-weight"},
        "LL": {"type": "Live", "description": "Live load"},
        "WL": {"type": "Wind", "description": "Lateral wind load"},
    }
    combo_metadata = {
        "ULS": {"method": "LRFD"},
        "ULS-G": {"method": "LRFD"},
        "ULS-W": {"method": "LRFD"},
        "SLS": {"method": "Service"},
    }
    return cases, combos, case_metadata, combo_metadata


def beam_demo():
    d = _base(
        combinations={"ULS": {"DL": 1.2, "LL": 1.6}, "SLS": {"DL": 1.0, "LL": 1.0}},
        combo_metadata={"ULS": {"method": "LRFD"}, "SLS": {"method": "Service"}},
    )
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Pin"},
            {"id": "N2", "x": 6.0, "z": 0.0, "support": "Roller"},
        ],
        members=[
            {"id": "B1", "i": "N1", "j": "N2", "type": "Beam", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False}
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -10.0, "w2": -10.0, "x1": 0.0, "x2": 6.0, "case": "LL"},
        ],
    )
    return d


def point_load_beam_demo():
    d = _base(
        combinations={"ULS": {"DL": 1.2, "LL": 1.6}, "SLS": {"DL": 1.0, "LL": 1.0}},
        combo_metadata={"ULS": {"method": "LRFD"}, "SLS": {"method": "Service"}},
    )
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Pin"},
            {"id": "N2", "x": 8.0, "z": 0.0, "support": "Roller"},
        ],
        members=[
            {"id": "B1", "i": "N1", "j": "N2", "type": "Beam", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False}
        ],
        point_loads=[
            {"member": "B1", "direction": "FZ", "value": -35.0, "x": 3.0, "case": "LL"},
            {"member": "B1", "direction": "MY", "value": 12.0, "x": 6.0, "case": "LL"},
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -2.0, "w2": -2.0, "x1": 0.0, "x2": 8.0, "case": "DL"},
        ],
    )
    return d


def cantilever_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d["case_metadata"]["LL"]["description"] = "Tip live load"
    d["case_metadata"]["WL"]["description"] = "Horizontal tip load"
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 4.0, "z": 0.0, "support": "Free"},
        ],
        members=[
            {"id": "B1", "i": "N1", "j": "N2", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False}
        ],
        point_loads=[
            {"node": "N2", "direction": "FZ", "value": -12.0, "case": "LL"},
            {"node": "N2", "direction": "FX", "value": 8.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -1.5, "w2": -1.5, "x1": 0.0, "x2": 4.0, "case": "DL"},
        ],
    )
    return d


def portal_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 0.0, "z": 3.0, "support": "Free"},
            {"id": "N3", "x": 5.0, "z": 3.0, "support": "Free"},
            {"id": "N4", "x": 5.0, "z": 0.0, "support": "Pin"},
        ],
        members=[
            {"id": "C1", "i": "N1", "j": "N2", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False},
            {"id": "B1", "i": "N2", "j": "N3", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False},
            {"id": "C2", "i": "N4", "j": "N3", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N2", "direction": "FX", "value": 12.0, "case": "WL"},
            {"node": "N3", "direction": "FX", "value": 12.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -6.0, "w2": -6.0, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B1", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 5.0, "case": "LL"},
        ],
    )
    return d


def continuous_beam_demo():
    cases = ["DL", "LL-L", "LL-R"]
    combos = {
        "ULS-FULL": {"DL": 1.2, "LL-L": 1.6, "LL-R": 1.6},
        "ULS-LEFT": {"DL": 1.2, "LL-L": 1.6},
        "ULS-RIGHT": {"DL": 1.2, "LL-R": 1.6},
        "SLS": {"DL": 1.0, "LL-L": 1.0, "LL-R": 1.0},
    }
    d = _base(
        cases=cases,
        combinations=combos,
        case_metadata={
            "DL": {"type": "Dead", "description": "Dead load / self-weight"},
            "LL-L": {"type": "Live", "description": "Live load on left span"},
            "LL-R": {"type": "Live", "description": "Live load on right span"},
        },
        combo_metadata={
            "ULS-FULL": {"method": "LRFD"}, "ULS-LEFT": {"method": "LRFD"},
            "ULS-RIGHT": {"method": "LRFD"}, "SLS": {"method": "Service"},
        },
    )
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Pin"},
            {"id": "N2", "x": 5.0, "z": 0.0, "support": "Roller"},
            {"id": "N3", "x": 10.0, "z": 0.0, "support": "Roller"},
        ],
        members=[
            {"id": "B1", "i": "N1", "j": "N2", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False},
            {"id": "B2", "i": "N2", "j": "N3", "type": "Frame", "material": "Steel", "section": "RHS100x50x3", "release_i": False, "release_j": False},
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -4.0, "w2": -4.0, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B2", "direction": "FZ", "w1": -4.0, "w2": -4.0, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B1", "direction": "FZ", "w1": -9.0, "w2": -9.0, "x1": 0.0, "x2": 5.0, "case": "LL-L"},
            {"member": "B2", "direction": "FZ", "w1": -9.0, "w2": -9.0, "x1": 0.0, "x2": 5.0, "case": "LL-R"},
        ],
    )
    return d


def portal_2storey_2bay_irregular_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 4.5, "z": 0.0, "support": "Pin"},
            {"id": "N3", "x": 10.5, "z": 0.0, "support": "Pin"},
            {"id": "N4", "x": 0.0, "z": 3.4, "support": "Free"},
            {"id": "N5", "x": 4.5, "z": 3.4, "support": "Free"},
            {"id": "N6", "x": 10.5, "z": 3.4, "support": "Free"},
            {"id": "N7", "x": 0.0, "z": 7.6, "support": "Free"},
            {"id": "N8", "x": 4.5, "z": 7.6, "support": "Free"},
            {"id": "N9", "x": 10.5, "z": 7.6, "support": "Free"},
        ],
        members=[
            {"id": "C11", "i": "N1", "j": "N4", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C12", "i": "N4", "j": "N7", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C21", "i": "N2", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C22", "i": "N5", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C31", "i": "N3", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C32", "i": "N6", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "B11", "i": "N4", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B12", "i": "N5", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B21", "i": "N7", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B22", "i": "N8", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N4", "direction": "FX", "value": 6.0, "case": "WL"},
            {"node": "N5", "direction": "FX", "value": 7.5, "case": "WL"},
            {"node": "N6", "direction": "FX", "value": 6.0, "case": "WL"},
            {"node": "N7", "direction": "FX", "value": 10.0, "case": "WL"},
            {"node": "N8", "direction": "FX", "value": 12.0, "case": "WL"},
            {"node": "N9", "direction": "FX", "value": 10.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B11", "direction": "FZ", "w1": -8.5, "w2": -8.5, "x1": 0.0, "x2": 4.5, "case": "DL"},
            {"member": "B12", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B21", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 4.5, "case": "DL"},
            {"member": "B22", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B11", "direction": "FZ", "w1": -10.0, "w2": -10.0, "x1": 0.0, "x2": 4.5, "case": "LL"},
            {"member": "B12", "direction": "FZ", "w1": -9.0, "w2": -9.0, "x1": 0.0, "x2": 6.0, "case": "LL"},
            {"member": "B21", "direction": "FZ", "w1": -6.5, "w2": -6.5, "x1": 0.0, "x2": 4.5, "case": "LL"},
            {"member": "B22", "direction": "FZ", "w1": -6.0, "w2": -6.0, "x1": 0.0, "x2": 6.0, "case": "LL"},
        ],
    )
    return d


def portal_3storey_2bay_irregular_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 5.0, "z": 0.0, "support": "Pin"},
            {"id": "N3", "x": 11.5, "z": 0.0, "support": "Pin"},
            {"id": "N4", "x": 0.0, "z": 3.2, "support": "Free"},
            {"id": "N5", "x": 5.0, "z": 3.2, "support": "Free"},
            {"id": "N6", "x": 11.5, "z": 3.2, "support": "Free"},
            {"id": "N7", "x": 0.0, "z": 6.7, "support": "Free"},
            {"id": "N8", "x": 5.0, "z": 6.7, "support": "Free"},
            {"id": "N9", "x": 11.5, "z": 6.7, "support": "Free"},
            {"id": "N10", "x": 0.0, "z": 10.8, "support": "Free"},
            {"id": "N11", "x": 5.0, "z": 10.8, "support": "Free"},
            {"id": "N12", "x": 11.5, "z": 10.8, "support": "Free"},
        ],
        members=[
            {"id": "C11", "i": "N1", "j": "N4", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C12", "i": "N4", "j": "N7", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C13", "i": "N7", "j": "N10", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C21", "i": "N2", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C22", "i": "N5", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C23", "i": "N8", "j": "N11", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C31", "i": "N3", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C32", "i": "N6", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C33", "i": "N9", "j": "N12", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "B11", "i": "N4", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B12", "i": "N5", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B21", "i": "N7", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B22", "i": "N8", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B31", "i": "N10", "j": "N11", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B32", "i": "N11", "j": "N12", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N4", "direction": "FX", "value": 4.5, "case": "WL"},
            {"node": "N5", "direction": "FX", "value": 5.0, "case": "WL"},
            {"node": "N6", "direction": "FX", "value": 4.5, "case": "WL"},
            {"node": "N7", "direction": "FX", "value": 7.0, "case": "WL"},
            {"node": "N8", "direction": "FX", "value": 8.0, "case": "WL"},
            {"node": "N9", "direction": "FX", "value": 7.0, "case": "WL"},
            {"node": "N10", "direction": "FX", "value": 10.0, "case": "WL"},
            {"node": "N11", "direction": "FX", "value": 11.5, "case": "WL"},
            {"node": "N12", "direction": "FX", "value": 10.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B11", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B12", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 6.5, "case": "DL"},
            {"member": "B21", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B22", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 6.5, "case": "DL"},
            {"member": "B31", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 5.0, "case": "DL"},
            {"member": "B32", "direction": "FZ", "w1": -6.5, "w2": -6.5, "x1": 0.0, "x2": 6.5, "case": "DL"},
            {"member": "B11", "direction": "FZ", "w1": -9.5, "w2": -9.5, "x1": 0.0, "x2": 5.0, "case": "LL"},
            {"member": "B12", "direction": "FZ", "w1": -9.0, "w2": -9.0, "x1": 0.0, "x2": 6.5, "case": "LL"},
            {"member": "B21", "direction": "FZ", "w1": -8.5, "w2": -8.5, "x1": 0.0, "x2": 5.0, "case": "LL"},
            {"member": "B22", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 6.5, "case": "LL"},
            {"member": "B31", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 5.0, "case": "LL"},
            {"member": "B32", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 6.5, "case": "LL"},
        ],
    )
    return d


def portal_3storey_3bay_irregular_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 4.0, "z": 0.0, "support": "Pin"},
            {"id": "N3", "x": 9.5, "z": 0.0, "support": "Pin"},
            {"id": "N4", "x": 15.5, "z": 0.0, "support": "Pin"},
            {"id": "N5", "x": 0.0, "z": 3.5, "support": "Free"},
            {"id": "N6", "x": 4.0, "z": 3.5, "support": "Free"},
            {"id": "N7", "x": 9.5, "z": 3.5, "support": "Free"},
            {"id": "N8", "x": 15.5, "z": 3.5, "support": "Free"},
            {"id": "N9", "x": 0.0, "z": 7.0, "support": "Free"},
            {"id": "N10", "x": 4.0, "z": 7.0, "support": "Free"},
            {"id": "N11", "x": 9.5, "z": 7.0, "support": "Free"},
            {"id": "N12", "x": 15.5, "z": 7.0, "support": "Free"},
            {"id": "N13", "x": 0.0, "z": 10.2, "support": "Free"},
            {"id": "N14", "x": 4.0, "z": 10.2, "support": "Free"},
            {"id": "N15", "x": 9.5, "z": 10.2, "support": "Free"},
            {"id": "N16", "x": 15.5, "z": 10.2, "support": "Free"},
        ],
        members=[
            {"id": "C11", "i": "N1", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C12", "i": "N5", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C13", "i": "N9", "j": "N13", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C21", "i": "N2", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C22", "i": "N6", "j": "N10", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C23", "i": "N10", "j": "N14", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C31", "i": "N3", "j": "N7", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C32", "i": "N7", "j": "N11", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C33", "i": "N11", "j": "N15", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C41", "i": "N4", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C42", "i": "N8", "j": "N12", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C43", "i": "N12", "j": "N16", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "B11", "i": "N5", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B12", "i": "N6", "j": "N7", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B13", "i": "N7", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B21", "i": "N9", "j": "N10", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B22", "i": "N10", "j": "N11", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B23", "i": "N11", "j": "N12", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B31", "i": "N13", "j": "N14", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B32", "i": "N14", "j": "N15", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B33", "i": "N15", "j": "N16", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N5", "direction": "FX", "value": 4.0, "case": "WL"}, {"node": "N6", "direction": "FX", "value": 4.5, "case": "WL"},
            {"node": "N7", "direction": "FX", "value": 4.5, "case": "WL"}, {"node": "N8", "direction": "FX", "value": 4.0, "case": "WL"},
            {"node": "N9", "direction": "FX", "value": 6.5, "case": "WL"}, {"node": "N10", "direction": "FX", "value": 7.0, "case": "WL"},
            {"node": "N11", "direction": "FX", "value": 7.0, "case": "WL"}, {"node": "N12", "direction": "FX", "value": 6.5, "case": "WL"},
            {"node": "N13", "direction": "FX", "value": 9.0, "case": "WL"}, {"node": "N14", "direction": "FX", "value": 9.5, "case": "WL"},
            {"node": "N15", "direction": "FX", "value": 9.5, "case": "WL"}, {"node": "N16", "direction": "FX", "value": 9.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B11", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 4.0, "case": "DL"},
            {"member": "B12", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 5.5, "case": "DL"},
            {"member": "B13", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B21", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 4.0, "case": "DL"},
            {"member": "B22", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 5.5, "case": "DL"},
            {"member": "B23", "direction": "FZ", "w1": -6.5, "w2": -6.5, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B31", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 4.0, "case": "DL"},
            {"member": "B32", "direction": "FZ", "w1": -6.5, "w2": -6.5, "x1": 0.0, "x2": 5.5, "case": "DL"},
            {"member": "B33", "direction": "FZ", "w1": -6.0, "w2": -6.0, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B11", "direction": "FZ", "w1": -9.5, "w2": -9.5, "x1": 0.0, "x2": 4.0, "case": "LL"},
            {"member": "B12", "direction": "FZ", "w1": -9.0, "w2": -9.0, "x1": 0.0, "x2": 5.5, "case": "LL"},
            {"member": "B13", "direction": "FZ", "w1": -8.5, "w2": -8.5, "x1": 0.0, "x2": 6.0, "case": "LL"},
            {"member": "B21", "direction": "FZ", "w1": -8.5, "w2": -8.5, "x1": 0.0, "x2": 4.0, "case": "LL"},
            {"member": "B22", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 5.5, "case": "LL"},
            {"member": "B23", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 6.0, "case": "LL"},
            {"member": "B31", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 4.0, "case": "LL"},
            {"member": "B32", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 5.5, "case": "LL"},
            {"member": "B33", "direction": "FZ", "w1": -6.5, "w2": -6.5, "x1": 0.0, "x2": 6.0, "case": "LL"},
        ],
    )
    return d


def portal_mixed_loads_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 0.0, "z": 3.8, "support": "Free"},
            {"id": "N3", "x": 0.0, "z": 7.2, "support": "Free"},
            {"id": "N4", "x": 5.5, "z": 0.0, "support": "Pin"},
            {"id": "N5", "x": 5.5, "z": 4.6, "support": "Free"},
            {"id": "N6", "x": 5.5, "z": 8.3, "support": "Free"},
            {"id": "N7", "x": 11.5, "z": 0.0, "support": "Pin"},
            {"id": "N8", "x": 11.5, "z": 4.2, "support": "Free"},
            {"id": "N9", "x": 11.5, "z": 8.0, "support": "Free"},
        ],
        members=[
            {"id": "C11", "i": "N1", "j": "N2", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C12", "i": "N2", "j": "N3", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C21", "i": "N4", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C22", "i": "N5", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C31", "i": "N7", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C32", "i": "N8", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "B11", "i": "N2", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B12", "i": "N5", "j": "N8", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B21", "i": "N3", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B22", "i": "N6", "j": "N9", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N5", "direction": "FZ", "value": -18.0, "case": "LL"},
            {"node": "N6", "direction": "FZ", "value": -12.0, "case": "LL"},
            {"node": "N3", "direction": "MY", "value": 28.0, "case": "LL"},
            {"node": "N6", "direction": "FX", "value": 8.5, "case": "WL"},
            {"node": "N9", "direction": "FX", "value": 10.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B11", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 5.5, "case": "DL"},
            {"member": "B12", "direction": "FZ", "w1": -7.5, "w2": -7.5, "x1": 0.0, "x2": 6.0, "case": "DL"},
            {"member": "B21", "direction": "FZ", "w1": -6.0, "w2": -11.0, "x1": 0.0, "x2": 5.5, "case": "LL"},
            {"member": "B22", "direction": "FZ", "w1": -10.0, "w2": -4.0, "x1": 0.0, "x2": 6.0, "case": "LL"},
            {"member": "B21", "direction": "FX", "w1": 1.5, "w2": 3.0, "x1": 0.0, "x2": 5.5, "case": "WL"},
            {"member": "B22", "direction": "FX", "w1": 2.0, "w2": 3.5, "x1": 0.0, "x2": 6.0, "case": "WL"},
        ],
    )
    return d


def portal_wind_moment_frame_demo():
    cases, combos, case_metadata, combo_metadata = _portal_combos()
    combos = dict(combos)
    combos.update({
        "ULS-W+": {"DL": 1.2, "LL": 1.0, "WL": 1.6},
        "SLS-W": {"DL": 1.0, "LL": 0.5, "WL": 1.0},
    })
    combo_metadata = dict(combo_metadata)
    combo_metadata.update({"ULS-W+": {"method": "LRFD"}, "SLS-W": {"method": "Service"}})
    d = _base(cases=cases, combinations=combos, case_metadata=case_metadata, combo_metadata=combo_metadata)
    d["case_metadata"]["WL"]["description"] = "Wind story forces + joint moments"
    d.update(
        nodes=[
            {"id": "N1", "x": 0.0, "z": 0.0, "support": "Fixed"},
            {"id": "N2", "x": 0.0, "z": 3.6, "support": "Free"},
            {"id": "N3", "x": 0.0, "z": 7.5, "support": "Free"},
            {"id": "N4", "x": 6.5, "z": 0.0, "support": "Fixed"},
            {"id": "N5", "x": 6.5, "z": 3.6, "support": "Free"},
            {"id": "N6", "x": 6.5, "z": 7.5, "support": "Free"},
        ],
        members=[
            {"id": "C11", "i": "N1", "j": "N2", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C12", "i": "N2", "j": "N3", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C21", "i": "N4", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "C22", "i": "N5", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC300x500", "release_i": False, "release_j": False},
            {"id": "B1", "i": "N2", "j": "N5", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
            {"id": "B2", "i": "N3", "j": "N6", "type": "Frame", "material": "Concrete", "section": "RC200x400", "release_i": False, "release_j": False},
        ],
        point_loads=[
            {"node": "N2", "direction": "FX", "value": 10.0, "case": "WL"},
            {"node": "N5", "direction": "FX", "value": 10.0, "case": "WL"},
            {"node": "N3", "direction": "FX", "value": 18.0, "case": "WL"},
            {"node": "N6", "direction": "FX", "value": 18.0, "case": "WL"},
            {"node": "N3", "direction": "MY", "value": 24.0, "case": "WL"},
            {"node": "N6", "direction": "MY", "value": -24.0, "case": "WL"},
        ],
        distributed_loads=[
            {"member": "B1", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 6.5, "case": "DL"},
            {"member": "B2", "direction": "FZ", "w1": -7.0, "w2": -7.0, "x1": 0.0, "x2": 6.5, "case": "DL"},
            {"member": "B1", "direction": "FZ", "w1": -10.0, "w2": -10.0, "x1": 0.0, "x2": 6.5, "case": "LL"},
            {"member": "B2", "direction": "FZ", "w1": -8.0, "w2": -8.0, "x1": 0.0, "x2": 6.5, "case": "LL"},
        ],
    )
    return d


EXAMPLES = {
    "1 — Simply Supported Beam": beam_demo,
    "2 — Beam + Point Load": point_load_beam_demo,
    "3 — Cantilever": cantilever_demo,
    "4 — Portal Frame": portal_demo,
    "5 — Two-span Continuous Beam": continuous_beam_demo,
    "6 — Portal 2 Storey 2 Bay (Irregular)": portal_2storey_2bay_irregular_demo,
    "7 — Portal 3 Storey 2 Bay (Irregular)": portal_3storey_2bay_irregular_demo,
    "8 — Portal 3 Storey 3 Bay (Irregular)": portal_3storey_3bay_irregular_demo,
    "9 — Portal Mixed Loads (Point / Moment / Triangular)": portal_mixed_loads_demo,
    "10 — Portal Wind + Moment Frame": portal_wind_moment_frame_demo,
}


def example_names():
    return list(EXAMPLES)


def get_example(name):
    return EXAMPLES[name]()
