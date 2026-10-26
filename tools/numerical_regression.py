"""Numerical regression: v0.5.4 reference ZIP vs v0.5.5 ZIP and optional EXE.

Runs identical models through isolated worker processes; verifies global equilibrium,
member N/V/M/displacement curves, support reactions, nodal DOFs and end forces.
No GUI assumptions. Uses the actual published v0.5.4 package, not screenshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_ZIP = ROOT / "dist/go_anastruct_2d-v0.5.4-plugin.zip"
CAND_ZIP = ROOT / "dist/go_anastruct_2d-v0.5.5-plugin.zip"
CAND_MANIFEST = Path(str(CAND_ZIP) + ".sha256")
BASE_SHA = "096ad236fa737b66d4a77ae79ed6690a452da168e6c8757b08f0d707d2f6056f"
MODEL_NAMES = (
    "1 — Simply Supported Beam",
    "4 — Portal Frame",
    "8 — Portal 3 Storey 3 Bay (Irregular)",
    "10 — Portal Wind + Moment Frame",
)
NODE_FIELDS = ("ux", "uz", "rotation", "Rx", "Rz", "My")
PLOT_FIELDS = ("x", "N", "V", "M", "d", "u", "ux", "uz")
END_FIELDS = ("N", "V", "M")
ABS_TOL = 1e-6
REL_TOL = 1e-5
PYTHON_BOOT = (
    "import runpy,sys;"
    "sys.path.insert(0,sys.argv[1]);"
    "runpy.run_module('go_anastruct_2d.worker',run_name='__main__')"
)


def checked_archive(path: Path, expected_sha: str, destination: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha:
        raise AssertionError(f"{path.name} SHA-256 mismatch {digest} != {expected_sha}")
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise AssertionError(f"{path.name} CRC failed")
        seen = set()
        for item in z.infolist():
            rel = Path(item.filename.replace("\\", "/"))
            if (
                item.filename in seen or rel.is_absolute() or ".." in rel.parts
                or not rel.parts or rel.parts[0] != "go_anastruct_2d"
            ):
                raise AssertionError(f"Unsafe/duplicate entry: {item.filename}")
            seen.add(item.filename)
        z.extractall(destination)
    if not (destination / "go_anastruct_2d/worker.py").is_file():
        raise AssertionError(f"{path.name} is missing worker.py")
    return digest


def request_worker(command: list[str], model: dict) -> dict:
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "_MEIPASS2"):
        env.pop(key, None)
    request = json.dumps({"protocol": 1, "model": model}, allow_nan=False)
    proc = subprocess.run(
        command, input=request, text=True, encoding="utf-8",
        errors="replace", capture_output=True, env=env, timeout=240,
    )
    try:
        reply = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Worker returned invalid JSON (exit {proc.returncode}): "
            f"stdout={proc.stdout[-1200:]} stderr={proc.stderr[-1800:]}"
        ) from exc
    if proc.returncode != 0 or reply.get("protocol") != 1 or not reply.get("ok"):
        raise AssertionError(f"Worker failed: {reply} {proc.stderr[-1800:]}")
    result = reply["result"]
    if result.get("solver_version") != "1.7.0":
        raise AssertionError(f"Wrong solver: {result.get('solver_version')}")
    return result


def check_equilibrium(result: dict, label: str):
    cases = result.get("cases", {})
    if not cases:
        raise AssertionError(f"{label}: no cases solved")
    for name, data in cases.items():
        if data.get("empty_load_case"):
            continue
        balance = data.get("equilibrium", {})
        if balance.get("passed") is not True:
            raise AssertionError(f"{label}/{name}: global equilibrium failed: {balance}")
        if balance.get("load_mapping_passed", True) is not True:
            raise AssertionError(f"{label}/{name}: load mapping failed: {balance}")


def compare_number(a, b, context: str, diffs: list):
    a, b = float(a), float(b)
    if not (math.isfinite(a) and math.isfinite(b)):
        raise AssertionError(f"{context}: nonfinite value {a}/{b}")
    delta = abs(a - b)
    diffs.append((delta, context, a, b))
    if not math.isclose(a, b, abs_tol=ABS_TOL, rel_tol=REL_TOL):
        raise AssertionError(f"{context}: reference={a:.12g}, candidate={b:.12g}, delta={delta:.6g}")


def compare_results(ref: dict, test: dict, tag: str):
    diffs = []
    if ref["model_hash"] != test["model_hash"]:
        raise AssertionError(f"{tag}: model fingerprints differ")
    if set(ref["cases"]) != set(test["cases"]):
        raise AssertionError(f"{tag}: case lists differ")
    for case in ref["cases"]:
        base = ref["cases"][case]
        newer = test["cases"][case]
        if set(base["nodes"]) != set(newer["nodes"]):
            raise AssertionError(f"{tag}/{case}: node sets differ")
        if set(base["members"]) != set(newer["members"]):
            raise AssertionError(f"{tag}/{case}: member sets differ")
        for node in base["nodes"]:
            for field in NODE_FIELDS:
                compare_number(
                    base["nodes"][node][field], newer["nodes"][node][field],
                    f"{tag}/{case}/node/{node}/{field}", diffs,
                )
        for member in base["members"]:
            a = base["members"][member]
            b = newer["members"][member]
            compare_number(a["L"], b["L"], f"{tag}/{case}/{member}/length", diffs)
            for end in ("i", "j"):
                for field in END_FIELDS:
                    compare_number(
                        a["end_forces"][end][field], b["end_forces"][end][field],
                        f"{tag}/{case}/{member}/{end}/{field}", diffs,
                    )
            for field in ("N", "V", "M", "d"):
                for extreme in ("min", "max"):
                    for component in ("x", "value"):
                        compare_number(
                            a["extrema"][field][extreme][component],
                            b["extrema"][field][extreme][component],
                            f"{tag}/{case}/{member}/{field}/{extreme}/{component}", diffs,
                        )
            if len(a["plot"]) != len(b["plot"]):
                raise AssertionError(f"{tag}/{case}/{member}: curve point count changed")
            for idx, (pa, pb) in enumerate(zip(a["plot"], b["plot"])):
                if pa.get("side") != pb.get("side"):
                    raise AssertionError(f"{tag}/{case}/{member}/{idx}: curve sidedness changed")
                for field in PLOT_FIELDS:
                    compare_number(
                        pa[field], pb[field],
                        f"{tag}/{case}/{member}/point/{idx}/{field}", diffs,
                    )
        for field in ("applied", "reaction", "residual"):
            aa = base["equilibrium"][field]
            bb = newer["equilibrium"][field]
            if len(aa) != len(bb):
                raise AssertionError(f"{tag}/{case}: equilibrium {field} shape changed")
            for idx, (x, y) in enumerate(zip(aa, bb)):
                compare_number(x, y, f"{tag}/{case}/equilibrium/{field}/{idx}", diffs)
    max_diff, where, _, _ = max(diffs, default=(0.0, "none", 0.0, 0.0))
    return {"checked_values": len(diffs), "max_abs_difference": max_diff, "max_difference_location": where}


def beam_reference_check(result: dict):
    # The LL load of built-in model 1 is uniformly -10 kN/m on a 6 m beam.
    case = result["cases"]["LL"]
    left, right = case["nodes"]["N1"], case["nodes"]["N2"]
    for label, value in (("left reaction", left["Rz"]), ("right reaction", right["Rz"])):
        if not math.isclose(value, 30.0, abs_tol=0.01):
            raise AssertionError(f"Analytical beam {label}: expected +30 kN, got {value:.6g}")
    mm = case["members"]["B1"]["extrema"]["M"]
    max_m = max(abs(mm["min"]["value"]), abs(mm["max"]["value"]))
    if not math.isclose(max_m, 45.0, rel_tol=0.015, abs_tol=0.10):
        raise AssertionError(f"Analytical beam Mmax expected 45 kN-m, got {max_m:.6g}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portable-exe", type=Path, help="Also compare bundled .exe against v0.5.5 Python")
    parser.add_argument("--report", type=Path, default=ROOT / "dist/numerical-regression-v055.json")
    args = parser.parse_args()
    candidate_sha = CAND_MANIFEST.read_text(encoding="ascii").strip().lower()
    if len(candidate_sha) != 64 or any(c not in "0123456789abcdef" for c in candidate_sha):
        raise AssertionError("Invalid candidate SHA manifest")
    sys.path.insert(0, str(ROOT))
    from go_anastruct_2d.examples import EXAMPLES
    records = []
    with tempfile.TemporaryDirectory(prefix="go-anastruct-regression-") as tmp:
        base_root, new_root = Path(tmp) / "v054", Path(tmp) / "v055"
        base_root.mkdir()
        new_root.mkdir()
        base_sha = checked_archive(BASE_ZIP, BASE_SHA, base_root)
        new_sha = checked_archive(CAND_ZIP, candidate_sha, new_root)
        base_cmd = [sys.executable, "-I", "-X", "utf8", "-c", PYTHON_BOOT, str(base_root)]
        new_cmd = [sys.executable, "-I", "-X", "utf8", "-c", PYTHON_BOOT, str(new_root)]
        portable_cmd = [str(args.portable_exe.resolve())] if args.portable_exe else None
        if portable_cmd and not args.portable_exe.is_file():
            raise FileNotFoundError(args.portable_exe)
        for name in MODEL_NAMES:
            model = EXAMPLES[name]()
            baseline = request_worker(base_cmd, model)
            candidate = request_worker(new_cmd, model)
            check_equilibrium(baseline, "v0.5.4/" + name)
            check_equilibrium(candidate, "v0.5.5/" + name)
            comparisons = {"v054_vs_v055": compare_results(baseline, candidate, name)}
            if name.startswith("1"):
                beam_reference_check(baseline)
                beam_reference_check(candidate)
            if portable_cmd:
                portable = request_worker(portable_cmd, model)
                check_equilibrium(portable, "Portable/" + name)
                comparisons["v055_vs_portable"] = compare_results(candidate, portable, name)
                if name.startswith("1"):
                    beam_reference_check(portable)
            records.append({"model": name, "cases": list(candidate["cases"]), **comparisons})
            print("PASS:", name, comparisons)
    report = {
        "result": "PASS", "solver": "anaStruct 1.7.0",
        "reference_version": "0.5.4", "candidate_version": "0.5.5",
        "reference_package_sha256": base_sha, "candidate_package_sha256": new_sha,
        "portable_exe_tested": bool(portable_cmd),
        "abs_tolerance": ABS_TOL, "rel_tolerance": REL_TOL,
        "models": records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PASS: reference vs candidate numerical regression:", args.report)


if __name__ == "__main__":
    main()
