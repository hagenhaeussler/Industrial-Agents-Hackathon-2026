"""Independent synthetic correspondences test the plan-to-map calibration, not evaluation answers."""

import unittest

from scripts.prepare_campus import fit_frame, geographic, google_mask, mercator
from shapely.geometry import Point, Polygon


def correspondences():
    document = {"floors": [{"id": "ground", "level": 0}], "spaces": []}
    elements = []
    for i in range(12):
        x, y = (i % 4) * 12, (i // 4) * 10
        ring = [(x, y), (x + 4, y), (x + 4, y + 3), (x, y + 3)]
        document["spaces"].append({"ref": str(i), "floor_id": "ground", "polygon": ring})
        ids = []
        for j, (px, py) in enumerate(ring):
            id_ = i * 10 + j
            # Scale, rotate and translate: this must be recovered, not assumed north-aligned.
            lon, lat = geographic(1.5 * px - 0.2 * py + 1290000, 0.2 * px + 1.5 * py + 6150000)
            elements.append({"type": "node", "id": id_, "lon": lon, "lat": lat})
            ids.append(id_)
        elements.append({"type": "way", "id": i, "nodes": ids + ids[:1], "tags": {"ref": str(i), "level": "0"}})
    return document, {"elements": elements}


class CampusAlignmentTests(unittest.TestCase):
    def test_google_mask_clears_facade_spill_and_preserves_the_courtyard(self):
        outer = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
        hole = [(30, 30), (70, 30), (70, 70), (30, 70), (30, 30)]
        outline = {"type": "Polygon", "coordinates": [[geographic(*p) for p in ring] for ring in [outer, hole]]}
        mask = google_mask(outline, 0)
        rings = [[mercator(*p) for p in ring] for ring in mask["coordinates"]]
        polygon = Polygon(rings[0], rings[1:])
        self.assertTrue(polygon.contains(Point(-2, 50)))
        self.assertFalse(polygon.contains(Point(-4, 50)))
        self.assertFalse(polygon.contains(Point(50, 50)))
        self.assertEqual(len(outline["coordinates"][0]), 5)

    def test_recovers_rotation_scale_and_translation(self):
        document, raw = correspondences()
        result = fit_frame(document, raw)
        self.assertEqual(result["matchedSpaces"], 12)
        for actual, expected in zip(result["matrix"], [[1.5, -0.2, 1290000], [0.2, 1.5, 6150000]]):
            for value, target in zip(actual, expected):
                self.assertAlmostEqual(value, target, places=5)
        self.assertLess(result["p95ResidualM"], 0.001)

    def test_refuses_insufficient_or_ambiguous_correspondences(self):
        document, raw = correspondences()
        with self.assertRaisesRegex(ValueError, "10 unambiguous"):
            fit_frame({**document, "spaces": document["spaces"][:3]}, raw)
        ways = [e for e in raw["elements"] if e["type"] == "way"]
        with self.assertRaisesRegex(ValueError, "10 unambiguous"):
            fit_frame(document, {"elements": raw["elements"] + ways})

    def test_refuses_badly_matching_geometry(self):
        document, raw = correspondences()
        document["spaces"][0]["polygon"] = [(100, 100), (105, 100), (105, 105), (100, 105)]
        with self.assertRaisesRegex(ValueError, "alignment failed"):
            fit_frame(document, raw)
