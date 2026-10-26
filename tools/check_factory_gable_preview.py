"""Run Gable Factory v0.5.6-preview numerical acceptance against existing v0.5.5 EXE."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_anastruct_2d.examples import factory_gable_demo
from go_anastruct_2d.factory_bridge import build_analysis_from_factory, members_from_scene
from go_anastruct_2d.model import fingerprint, validate


class _Group:
    def __init__(self, project, category, section, start, end):
        self.ext = {"go_factory_generator": {
            "project": project, "category": category, "section": section,
            "start": list(start), "end": list(end), "mark": "TEST",
        }}


class _Scene:
    def __init__(self):
        self.groups = []
        for y in (0.0, 12.0):
            self.groups.extend((
                _Group("Factory 01", "Column", "H-300x300x10x15", (0, y, 0), (0, y, 6)),
                _Group("Factory 01", "Column", "H-300x300x10x15", (18, y, 0), (18, y, 6)),
                _Group("Factory 01", "Rafter", "WF-300x150", (0, y, 6), (9, y, 8.5)),
                _Group("Factory 01", "Rafter", "WF-300x150", (9, y, 8.5), (18, y, 6)),
            ))


def run(executable: Path, model: dict):
    proc = subprocess.run([str(executable.resolve())],
                          input=json.dumps({"protocol": 1, "model": model}, allow_nan=False),
                          text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=240)
    if proc.returncode != 0:
        raise RuntimeError(f"Worker exit {proc.returncode}: {proc.stderr[-1500:]}")
    reply = json.loads(proc.stdout)
    if not reply.get("ok") or reply.get("protocol") != 1:
        raise AssertionError("Worker protocol failed: " + str(reply)[:1500])
    result = reply["result"]
    if result.get("model_hash") != fingerprint(model):
        raise AssertionError("Worker model hash changed across protocol boundary")
    for case, data in result["cases"].items():
        if not data.get("empty_load_case"):
            eq = data.get("equilibrium") or {}
            if not eq.get("passed") or not eq.get("load_mapping_passed", True):
                raise AssertionError(f"{case}: equilibrium failed: {eq}")
        if not data.get("members"):
            raise AssertionError(f"{case}: no member force result")
    return list(result["cases"])


def main():
    exe = ROOT / "dist/go_anastruct_worker/go_anastruct_worker.exe"
    if not exe.is_file():
        raise FileNotFoundError("No existing v0.5.5 Portable worker. Build first using BUILD_PORTABLE_AND_TEST_WINDOWS.cmd.")
    mapping = {"H-300x300x10x15": "RHS100x50x3",
               "WF-300x150": "SHS100x100x4"}
    rows = members_from_scene(_Scene())
    m0, p0 = build_analysis_from_factory(rows, "Factory 01", 0, mapping)
    m12, p12 = build_analysis_from_factory(rows, "Factory 01", 12, mapping)
    assert fingerprint(m0) == fingerprint(m12), "Only display station should change"
    assert p0["alignment_error_m"] == p12["alignment_error_m"] == 0
    cases = run(exe, validate(factory_gable_demo()))
    imported_cases = run(exe, m0)
    assert {"DL", "LL", "WL", "ULS", "SLS"} <= set(cases)
    assert {"DL", "LL", "WL", "ULS", "SLS"} <= set(imported_cases)
    print("PASS: standalone Example 11 FEM cases:", cases)
    print("PASS: imported GO Factory Gable FEM cases:", imported_cases)
    print("PASS: Y=0/Y=12 alignment and unchanged model fingerprint")
    print("IMPORTANT: This is a demo-load validation, not structural design approval.")


if __name__ == "__main__":
    main()
