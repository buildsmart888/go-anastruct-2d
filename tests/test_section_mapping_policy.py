"""Safe factory section choices without PySide6 or IngeTrazo imports."""
import unittest

from go_anastruct_2d.section_mapping_policy import (
    choices_for_section, preview_values,
)
from go_anastruct_2d.engineering_core import CatalogError


class SectionMappingPolicyTests(unittest.TestCase):
    def test_h_steel_has_strong_and_weak_in_same_review(self):
        options = choices_for_section("H-300x300x10x15")
        headings = [text for text, _ in options]
        self.assertTrue(any("STRONG" in title for title in headings))
        self.assertTrue(any("WEAK" in title for title in headings))
        self.assertTrue(all("RC" not in text for text in headings))
        strong = next(p for n,p in options if "STRONG" in n)
        weak = next(p for n,p in options if "WEAK" in n)
        a1, iz1, status1 = preview_values("H-300x300x10x15", strong)
        a2, iz2, status2 = preview_values("H-300x300x10x15", weak)
        self.assertEqual(a1, a2)
        self.assertGreater(float(iz1), float(iz2))
        self.assertIn("NOMINAL", status1)
        self.assertIn("NOMINAL", status2)

    def test_unsupported_c_section_has_no_fake_nominal_properties(self):
        options = choices_for_section("C-150x65x20x2.3")
        self.assertTrue(options)
        self.assertFalse(any(p.get("mode") == "go_core_nominal" for _,p in options))
        self.assertTrue(all(p["mode"] == "manual_starter" for _,p in options))

    def test_manual_alternatives_are_steel_only_and_warning_visible(self):
        options = choices_for_section("WF-300x150")
        manual = [(title, val) for title,val in options if val["mode"] == "manual_starter"]
        self.assertTrue(manual)
        for title, payload in manual:
            self.assertNotIn("RC", title)
            self.assertIn("not physically equivalent", title)
            a, i, status = preview_values("WF-300x150", payload)
            self.assertGreater(float(a),0)
            self.assertGreater(float(i),0)
            self.assertIn("NOT SAME", status.upper().replace("NOT SAME", "NOT SAME")
                          if "NOT SAME" in status.upper() else status.upper().replace("NOT", "NOT"))
            
    def test_invalid_choice_fails(self):
        with self.assertRaises(CatalogError):
            preview_values("WF-300x150", {"mode":"manual_starter","section":"RC200x400"})
        with self.assertRaises(CatalogError):
            preview_values("WF-300x150", {"mode":"go_core_nominal","axis":"foo"})


if __name__ == "__main__":
    unittest.main()
