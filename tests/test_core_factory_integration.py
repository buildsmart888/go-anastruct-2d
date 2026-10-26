"""GO Core nominal vs manual section mapping, load persistence and support edits."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from go_anastruct_2d.factory_bridge import (
    FactoryImportError, build_analysis_from_factory, members_from_scene,
)
from go_anastruct_2d.factory_reimport import (
    ReimportNeedsConfirmation, preserve_analysis_edits,
)
from go_anastruct_2d.model import fingerprint, validate


def source_scene(y=0.0):
    parts = [
        ("Column", "H-300x300x10x15", (0, y, 0), (0, y, 6)),
        ("Column", "H-300x300x10x15", (18, y, 0), (18, y, 6)),
        ("Rafter", "WF-300x150", (0, y, 6), (9, y, 8.5)),
        ("Rafter", "WF-300x150", (9, y, 8.5), (18, y, 6)),
    ]
    return SimpleNamespace(groups=[
        SimpleNamespace(ext={"go_factory_generator": {
            "project": "Factory 01", "category": kind, "section": sec,
            "start": list(a), "end": list(b), "mark": f"G{i}",
        }}) for i, (kind, sec, a, b) in enumerate(parts)
    ])


def mapping():
    return {
        "H-300x300x10x15": {"mode": "go_core_nominal", "axis": "strong", "acknowledged": True},
        "WF-300x150": {"mode": "go_core_nominal", "axis": "strong", "acknowledged": True},
    }


class SharedSteelAnalysisTests(unittest.TestCase):
    def test_factory_h_and_wf_have_nominal_properties_not_rc(self):
        model, placement = build_analysis_from_factory(
            members_from_scene(source_scene()), "Factory 01", 0.0, mapping(),
        )
        validate(model)
        sections = {row["id"]: row for row in model["sections"]}
        ids = {row["id"]: row["section"] for row in model["members"]}
        self.assertEqual(ids["C1"], "GOCORE:H-300x300x10x15:strong")
        self.assertEqual(ids["R1"], "GOCORE:WF-300x150:strong")
        for sid in (ids["C1"], ids["R1"]):
            self.assertEqual(sections[sid]["kind"], "Steel")
            self.assertEqual(sections[sid]["property_status"], "NOMINAL_GEOMETRY_ONLY")
            self.assertGreater(sections[sid]["A"], 0)
            self.assertGreater(sections[sid]["Iz"], 0)
            self.assertFalse(sections[sid]["verified"])
        self.assertNotIn("RC200x400", set(ids.values()))
        self.assertEqual(placement["alignment_error_m"], 0.0)

    def test_incomplete_mapping_or_unapproved_nominal_rejected(self):
        rows = members_from_scene(source_scene())
        with self.assertRaises(FactoryImportError):
            build_analysis_from_factory(rows, "Factory 01", 0, {})
        bad = mapping()
        bad["WF-300x150"]["acknowledged"] = False
        with self.assertRaises(FactoryImportError):
            build_analysis_from_factory(rows, "Factory 01", 0, bad)
        bad = mapping()
        bad["H-300x300x10x15"] = "RC200x400"
        with self.assertRaisesRegex(FactoryImportError, "RC section substitutions"):
            build_analysis_from_factory(rows, "Factory 01", 0, bad)

    def test_unedited_station_switch_preserves_fem_hash(self):
        m0, p0 = build_analysis_from_factory(
            members_from_scene(source_scene(0)), "Factory 01", 0, mapping())
        m12, p12 = build_analysis_from_factory(
            members_from_scene(source_scene(12)), "Factory 01", 12, mapping())
        self.assertEqual(fingerprint(m0), fingerprint(m12))
        self.assertEqual(p12["frame_y"], 12)
        self.assertNotEqual(p0["frame_y"], p12["frame_y"])

    def test_reimport_keeps_releases_and_modified_loads(self):
        m0, _ = build_analysis_from_factory(
            members_from_scene(source_scene()), "Factory 01", 0, mapping())
        changed = deepcopy(m0)
        changed["distributed_loads"][0]["w1"] = -11.25
        changed["distributed_loads"][0]["w2"] = -11.25
        changed["combinations"]["ULS"]["DL"] = 1.35
        changed["members"][1]["release_j"] = True
        refreshed, _ = build_analysis_from_factory(
            members_from_scene(source_scene(12)), "Factory 01", 12, mapping())
        merged = preserve_analysis_edits(changed, refreshed)
        self.assertEqual(merged["distributed_loads"][0]["w1"], -11.25)
        self.assertEqual(merged["combinations"]["ULS"]["DL"], 1.35)
        self.assertTrue(merged["members"][1]["release_j"])
        self.assertEqual(fingerprint(changed), fingerprint(merged))

    def test_geometry_change_refuses_silent_reset(self):
        m0, _ = build_analysis_from_factory(
            members_from_scene(source_scene()), "Factory 01", 0, mapping())
        modified = deepcopy(m0)
        modified["nodes"][2]["z"] += .1
        with self.assertRaises(ReimportNeedsConfirmation):
            preserve_analysis_edits(m0, modified)

    def test_base_change_requires_new_analysis_fingerprint(self):
        m0, _ = build_analysis_from_factory(
            members_from_scene(source_scene()), "Factory 01", 0, mapping(), support="Fixed")
        mpin, _ = build_analysis_from_factory(
            members_from_scene(source_scene()), "Factory 01", 0, mapping(), support="Pin")
        self.assertNotEqual(fingerprint(m0), fingerprint(mpin))
        self.assertTrue(all(n["support"] == "Pin" for n in mpin["nodes"]
                            if n["id"] in ("N1", "N5")))


if __name__ == "__main__":
    unittest.main()
