"""Regression guard: example 10 must never receive example 1 beam formulas."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.numerical_regression import MODEL_NAMES, is_simple_beam_model


class SimpleBeamAnalyticalGuardTests(unittest.TestCase):
    def test_only_the_exact_simple_beam_fixture_is_eligible(self):
        self.assertEqual(len(MODEL_NAMES), 4)
        expected = {"1 — Simply Supported Beam"}
        eligible = {name for name in MODEL_NAMES if is_simple_beam_model(name)}
        self.assertEqual(eligible, expected)
        self.assertFalse(is_simple_beam_model("10 — Portal Wind + Moment Frame"))
        self.assertFalse(is_simple_beam_model("11 — Another Portal Frame"))

    def test_no_prefix_based_fixture_gate(self):
        text = (ROOT / "tools/numerical_regression.py").read_text(encoding="utf-8")
        self.assertNotIn('name.startswith("1")', text)
        self.assertEqual(text.count("if is_simple_beam_model(name):"), 2)


if __name__ == "__main__":
    unittest.main()
