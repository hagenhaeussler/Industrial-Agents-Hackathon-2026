"""Preview tests: the exterior view shows one solid outline per floor above ground."""

import json
import unittest

from building_api.preview import ROOF, isometric_svg
from building_db.source import BuildingDocument


def space(space_id: str, floor_id: str, x: float, width: float) -> dict:
    return {
        "id": space_id,
        "floor_id": floor_id,
        "type": "room",
        "room_type": "office",
        "name": space_id,
        "ref": space_id,
        "polygon": [[x, 0], [x + width, 0], [x + width, 6], [x, 6]],
        "synthetic": False,
    }


def building(spaces: list[dict]) -> BuildingDocument:
    return BuildingDocument.model_validate_json(
        json.dumps(
            {
                "building": {
                    "id": "b",
                    "name": "B",
                    "source": "test",
                    "source_ref": {},
                    "license": "",
                    "attribution": "",
                    "split": "",
                    "units": "m",
                },
                "floors": [
                    {"id": f"f{level}", "level": level, "name": str(level), "elevation_m": level * 3, "height_m": 3}
                    for level in (-1, 0, 1)
                ],
                "spaces": spaces,
                "openings": [],
                "vertical_connectors": [],
                "assets": [],
            }
        )
    )


class PreviewTest(unittest.TestCase):
    def test_rooms_split_by_a_wall_gap_form_one_outline_and_basements_stay_hidden(self) -> None:
        # Two rooms per floor with a 0.2 m wall gap between them, on a basement, a ground floor and a first floor.
        spaces = [
            space(f"{floor}-{side}", floor, x, 5)
            for floor in ("f-1", "f0", "f1")
            for side, x in (("west", 0), ("east", 5.2))
        ]
        svg = isometric_svg(building(spaces))
        self.assertEqual(svg.count(f'fill="{ROOF}"'), 2)

    def test_building_without_indoor_spaces_gives_an_empty_drawing(self) -> None:
        # Imports now require a nonempty space list. An outdoor-only building is still valid
        # and should have no exterior slab, because previews deliberately omit outdoor spaces.
        outdoor = space("outside-room", "f0", 0, 5)
        outdoor["type"] = "outdoor"
        outdoor["room_type"] = "outdoor"
        self.assertEqual(isometric_svg(building([outdoor])).count("<path"), 0)


if __name__ == "__main__":
    unittest.main()
