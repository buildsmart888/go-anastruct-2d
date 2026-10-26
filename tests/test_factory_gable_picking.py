"""Y-station picking/snap regression without a GUI or IngeTrazo installation."""
import unittest
import numpy as np

from go_anastruct_2d.examples import factory_gable_demo
from go_anastruct_2d.picking import hover_member_data, pick_item


class FakeCamera:
    @staticmethod
    def world_to_pixels(points):
        pts = np.asarray(points, dtype=float)
        # Make the world Y coordinate visible in the synthetic camera so a
        # projection hardcoded to Y=0 cannot accidentally pass the test.
        return pts[:, 0] + pts[:, 1] * 100, pts[:, 2] * 10, np.ones(len(pts), dtype=bool)


class FactoryFramePickingTests(unittest.TestCase):
    def setUp(self):
        self.camera = FakeCamera()
        self.model = factory_gable_demo()

    def test_node_pick_on_y12_and_not_y0(self):
        self.assertEqual(
            pick_item(self.camera, self.model, 1200, 0, frame_y=12),
            "node:N1",
        )
        self.assertIsNone(
            pick_item(self.camera, self.model, 1200, 0, frame_y=0),
        )

    def test_member_pick_on_y12(self):
        self.assertEqual(
            pick_item(self.camera, self.model, 1200, 30, frame_y=12),
            "member:C1",
        )

    def test_cached_hover_world_point_is_on_selected_plane(self):
        result = {"cases": {"LL": {"members": {
            "C1": {
                "L": 6.0,
                "plot": [
                    {"x": 0.0, "N": -10.0, "V": 0.0, "M": 0.0, "d": 0.0},
                    {"x": 6.0, "N": -10.0, "V": 0.0, "M": 0.0, "d": 0.0},
                ]
            }
        }}}}
        hit = hover_member_data(
            self.camera, self.model, result, "LL", 1200, 30, frame_y=12
        )
        self.assertIsNotNone(hit)
        self.assertEqual(hit["member"], "C1")
        self.assertEqual(hit["world"][1], 12.0)


if __name__ == "__main__":
    unittest.main()
