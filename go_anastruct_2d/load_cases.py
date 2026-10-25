from __future__ import annotations
import copy
from .model import validate

CASE_TYPES = ("Dead", "Live", "Roof Live", "Wind", "Seismic", "Other")
COMBINATION_METHODS = ("LRFD", "ASD", "Service", "Custom")


def guess_case_type(case_id: str) -> str:
    key = (case_id or "").strip().upper()
    if key.startswith("DL") or key in {"D", "DEAD", "SW"}:
        return "Dead"
    if key.startswith("LL") or key in {"L", "LIVE"}:
        return "Live"
    if key.startswith("RL") or "ROOF" in key:
        return "Roof Live"
    if key.startswith("W"):
        return "Wind"
    if key.startswith("E") or key.startswith("EQ") or "SEISM" in key:
        return "Seismic"
    return "Other"


def metadata_for_cases(model: dict) -> dict:
    stored = model.get("case_metadata", {}) or {}
    out = {}
    for case in model.get("cases", []):
        row = stored.get(case, {}) if isinstance(stored, dict) else {}
        out[case] = {
            "type": row.get("type") or guess_case_type(case),
            "description": row.get("description", ""),
        }
    return out


def combination_metadata(model: dict) -> dict:
    stored = model.get("combination_metadata", {}) or {}
    return {
        name: {"method": (stored.get(name, {}) or {}).get("method", "Custom")}
        for name in (model.get("combinations", {}) or {})
    }


def apply_load_case_configuration(
    model: dict,
    *,
    cases: list[str],
    case_metadata: dict,
    combinations: dict,
    combination_meta: dict,
    self_weight: bool,
    self_weight_case: str | None,
) -> dict:
    cases = [str(case).strip() for case in cases if str(case).strip()]
    if not cases:
        raise ValueError("At least one load case is required")
    if len(cases) != len(set(cases)):
        raise ValueError("Load Case IDs must be unique")

    referenced = {
        row.get("case")
        for field in ("point_loads", "distributed_loads")
        for row in model.get(field, [])
        if row.get("case")
    }
    missing = sorted(referenced - set(cases))
    if missing:
        raise ValueError(
            "Cannot remove load case(s) still used by loads: " + ", ".join(missing)
        )

    if self_weight and self_weight_case not in cases:
        raise ValueError("Select a valid Self-weight case")

    cleaned_combinations = {}
    cleaned_combo_meta = {}
    for name, factors in combinations.items():
        name = str(name).strip()
        if not name:
            continue
        row = {}
        for case in cases:
            value = float((factors or {}).get(case, 0.0))
            if value:
                row[case] = value
        if not row:
            raise ValueError(f"Combination {name}: enter at least one non-zero factor")
        cleaned_combinations[name] = row
        method = (combination_meta.get(name, {}) or {}).get("method", "Custom")
        cleaned_combo_meta[name] = {"method": method if method in COMBINATION_METHODS else "Custom"}

    out = copy.deepcopy(model)
    out["cases"] = cases
    out["case_metadata"] = {
        case: {
            "type": (case_metadata.get(case, {}) or {}).get("type", guess_case_type(case)),
            "description": (case_metadata.get(case, {}) or {}).get("description", ""),
        }
        for case in cases
    }
    out["combinations"] = cleaned_combinations
    out["combination_metadata"] = cleaned_combo_meta
    out["self_weight"] = bool(self_weight)
    out["self_weight_case"] = self_weight_case if self_weight else (self_weight_case if self_weight_case in cases else cases[0])
    return validate(out)
