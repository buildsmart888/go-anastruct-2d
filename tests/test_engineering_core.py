"""GO Engineering Core v0.1 nominal section geometry and safety tests."""
import math
import unittest

try:
    from go_anastruct_2d.engineering_core import (
        catalog_info, section_names, section_record,
        nominal_section_properties, CatalogError, section_identity,
    )
except ImportError:
    from go_factory_generator.engineering_core import (
        catalog_info, section_names, section_record,
        nominal_section_properties, CatalogError, section_identity,
    )


class CatalogTests(unittest.TestCase):
    def test_same_stable_section_identity_as_factory(self):
        self.assertEqual(catalog_info()["version"], "0.1.0")
        self.assertEqual(catalog_info()["count"], 75)
        self.assertEqual(catalog_info()["nominal_count"], 40)
        self.assertIn("H-300x300x10x15", section_names())
        self.assertIn("WF-300x150", section_names())
        self.assertEqual(section_identity("H-300x300x10x15")["section_property_status"],
                         "NOMINAL_GEOMETRY_ONLY")

    def test_requires_explicit_axis_and_unverified_acknowledgement(self):
        with self.assertRaises(CatalogError):
            nominal_section_properties("H-300x300x10x15", axis="strong")
        with self.assertRaises(CatalogError):
            nominal_section_properties("H-300x300x10x15", axis="z", acknowledge_unverified=True)
        with self.assertRaises(CatalogError):
            nominal_section_properties("C-150x65x20x2.3", axis="strong", acknowledge_unverified=True)

    def test_h_shape_nominal_area_and_inertia(self):
        p = nominal_section_properties("H-300x300x10x15",
                                      axis="strong", acknowledge_unverified=True)
        h, b, tw, tf = .300, .300, .010, .015
        a = 2*b*tf + (h-2*tf)*tw
        ix = 2*((b*tf**3)/12 + b*tf*((h-tf)/2)**2) + tw*(h-2*tf)**3/12
        iy = 2*(tf*b**3/12) + (h-2*tf)*tw**3/12
        self.assertAlmostEqual(p["A_m2"], a)
        self.assertAlmostEqual(p["Ix_m4"], ix)
        self.assertAlmostEqual(p["Iy_m4"], iy)
        self.assertGreater(p["Ix_m4"], p["Iy_m4"])
        self.assertFalse(p["verified"])
        self.assertLess(p["nominal_mass_kg_m"], 100)

    def test_axis_switch_changes_in_plane_stiffness_not_area(self):
        a = nominal_section_properties("WF-300x150", axis="strong", acknowledge_unverified=True)
        b = nominal_section_properties("WF-300x150", axis="weak", acknowledge_unverified=True)
        self.assertAlmostEqual(a["A_m2"], b["A_m2"])
        self.assertAlmostEqual(a["Iz_m4"], b["Ix_m4"])
        self.assertGreater(a["Iz_m4"], b["Iz_m4"])

    def test_closed_tube_geometry(self):
        p = nominal_section_properties("RHS-150x100x6",
                                      axis="strong", acknowledge_unverified=True)
        self.assertAlmostEqual(p["A_m2"], .15*.10-(.15-.012)*(.10-.012))
        tube = nominal_section_properties("PIPE-60.5x3.2",
                                      axis="strong", acknowledge_unverified=True)
        self.assertAlmostEqual(tube["Ix_m4"], tube["Iy_m4"])
        self.assertGreater(tube["A_m2"], 0)

    def test_unknown_section_rejected(self):
        with self.assertRaises(CatalogError):
            section_record("RC200x400")
        with self.assertRaises(CatalogError):
            nominal_section_properties("RC200x400", axis="strong", acknowledge_unverified=True)


if __name__ == "__main__":
    unittest.main()
