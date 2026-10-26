"""GO Factory v0.3.1 -> GO anaStruct 2D gable frame; no GUI dependencies."""
from __future__ import annotations

from copy import deepcopy
import math
from types import SimpleNamespace
import unittest

from go_anastruct_2d.examples import example_names, factory_gable_demo
from go_anastruct_2d.factory_bridge import (
    FactoryImportError, build_analysis_from_factory, members_from_scene,
    project_stations, required_section_mappings,
)
from go_anastruct_2d.model import fingerprint, validate


def fake_factory(project="Factory 01", y_positions=(0.0, 6.0, 12.0, 18.0,
                                                  24.0, 30.0, 36.0)):
    groups = []
    for y in y_positions:
        members = [
            ("Column", "H-300x300x10x15", (0, y, 0), (0, y, 6)),
            ("Column", "H-300x300x10x15", (18, y, 0), (18, y, 6)),
            ("Rafter", "WF-300x150", (0, y, 6), (9, y, 8.5)),
            ("Rafter", "WF-300x150", (9, y, 8.5), (18, y, 6)),
        ]
        for i, (category, section, start, end) in enumerate(members):
            groups.append(SimpleNamespace(ext={"go_factory_generator": {
                "project": project, "category": category, "section": section,
                "start": list(start), "end": list(end), "mark": f"M{y:g}-{i}",
                "role": category.lower(),
            }}))
    return SimpleNamespace(groups=groups)


SECTION_MAPPING = {"H-300x300x10x15": "RHS100x50x3",
                   "WF-300x150": "SHS100x100x4"}


class GableBridgeTests(unittest.TestCase):
    def test_example_11_gable(self):
        self.assertIn("11 — Gable Frame from GO Factory", example_names())
        model = validate(factory_gable_demo())
        self.assertEqual([(n["x"], n["z"]) for n in model["nodes"]],
                         [(0, 0), (0, 6), (9, 8.5), (18, 6), (18, 0)])
        self.assertEqual([m["id"] for m in model["members"]],
                         ["C1", "R1", "R2", "C2"])
        self.assertTrue({"DL", "LL", "WL"} <= set(model["cases"]))
        self.assertIn("ULS", model["combinations"])
        self.assertIn("SLS", model["combinations"])
        self.assertTrue(all("DEMO ONLY" in m["description"]
                            for m in model["case_metadata"].values()))

    def test_exact_3d_alignment_at_y0_and_y12(self):
        scene = fake_factory()
        before = deepcopy([g.ext for g in scene.groups])
        rows = members_from_scene(scene)
        for y in (0.0, 12.0):
            model, placement = build_analysis_from_factory(
                rows, "Factory 01", y, SECTION_MAPPING
            )
            validate(model)
            self.assertEqual(placement["frame_y"], y)
            self.assertEqual(placement["alignment_error_m"], 0.0)
            self.assertEqual(placement["markers"],
                             [[0, y, 0], [0, y, 6], [9, y, 8.5],
                              [18, y, 6], [18, y, 0]])
        self.assertEqual(before, [g.ext for g in scene.groups])

    def test_frame_movement_does_not_change_fem_fingerprint(self):
        rows = members_from_scene(fake_factory())
        one, first = build_analysis_from_factory(rows, "Factory 01", 0, SECTION_MAPPING)
        two, second = build_analysis_from_factory(rows, "Factory 01", 12, SECTION_MAPPING)
        self.assertEqual(fingerprint(one), fingerprint(two))
        self.assertNotEqual(first["frame_y"], second["frame_y"])

    def test_station_discovery_and_multiple_projects(self):
        one = fake_factory()
        other = fake_factory("Factory B", (0.0, 6.0))
        scene = SimpleNamespace(groups=one.groups + other.groups)
        rows = members_from_scene(scene)
        self.assertEqual(project_stations(rows)["Factory 01"], [float(i) for i in range(0, 37, 6)])
        self.assertEqual(project_stations(rows)["Factory B"], [0.0, 6.0])

    def test_missing_or_bad_geometry(self):
        self.assertEqual(members_from_scene(None), [])
        with self.assertRaises(FactoryImportError):
            build_analysis_from_factory([], "missing", 0, SECTION_MAPPING)
        scene = fake_factory()
        scene.groups.pop()  # missing right rafter at Y=36
        with self.assertRaisesRegex(FactoryImportError, "expected 2 columns and 2 rafters"):
            build_analysis_from_factory(members_from_scene(scene), "Factory 01", 36, SECTION_MAPPING)
        broken = fake_factory()
        broken.groups[0].ext["go_factory_generator"]["end"] = [float("nan"), 0, 6]
        with self.assertRaisesRegex(FactoryImportError, "non-finite"):
            members_from_scene(broken)

    def test_no_silent_section_mapping(self):
        rows = members_from_scene(fake_factory(y_positions=(0.0,)))
        self.assertEqual(required_section_mappings(rows, "Factory 01", 0),
                         ["H-300x300x10x15", "WF-300x150"])
        with self.assertRaisesRegex(FactoryImportError, "verified analytical A/Iz"):
            build_analysis_from_factory(rows, "Factory 01", 0)
        with self.assertRaisesRegex(FactoryImportError, "verified analytical A/Iz"):
            build_analysis_from_factory(rows, "Factory 01", 0, {"WF-300x150": "RHS100x50x3"})
        with self.assertRaisesRegex(FactoryImportError, "explicitly Fixed or Pin"):
            build_analysis_from_factory(rows, "Factory 01", 0, SECTION_MAPPING, support="Roller")

    def test_reversed_rafter_orientation_is_supported(self):
        scene = fake_factory(y_positions=(12.0,))
        for g in scene.groups:
            if g.ext["go_factory_generator"]["category"] == "Rafter":
                meta = g.ext["go_factory_generator"]
                meta["start"], meta["end"] = meta["end"], meta["start"]
        rows = members_from_scene(scene)
        model, placement = build_analysis_from_factory(rows, "Factory 01", 12, SECTION_MAPPING)
        self.assertEqual(placement["alignment_error_m"], 0.0)
        self.assertEqual([m["section"] for m in model["members"]],
                         ["RHS100x50x3", "SHS100x100x4", "SHS100x100x4", "RHS100x50x3"])


if __name__ == "__main__":
    unittest.main()
