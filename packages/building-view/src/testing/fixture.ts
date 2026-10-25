import type { Building } from "../building";

/** Two touching rooms on the ground floor, a room above, a lift between them and one rotated desk. */
export function fixture(): Building {
  return {
    building: {
      id: "fixture",
      name: "Fixture",
      source: "fixture",
      source_ref: {},
      license: "CC0-1.0",
      attribution: "test",
      split: "dev",
      units: "m",
    },
    floors: [
      { id: "F1", level: 1, name: "Floor 1", elevation_m: 3, height_m: 3 },
      { id: "F0", level: 0, name: "Ground floor", elevation_m: 0, height_m: 3 },
    ],
    spaces: [
      { id: "B", floor_id: "F0", type: "lift", room_type: "lift", name: "Lift", ref: "", polygon: [[4, 0], [8, 0], [8, 3], [4, 3]], synthetic: false },
      { id: "A", floor_id: "F0", type: "room", room_type: "office", name: "Office 0.01", ref: "0.01", polygon: [[0, 0], [4, 0], [4, 3], [0, 3]], synthetic: false },
      // L-shaped: its centroid lies outside the room.
      { id: "C", floor_id: "F1", type: "lift", room_type: "lift", name: "Lift", ref: "", polygon: [[4, 0], [8, 0], [8, 1], [5, 1], [5, 3], [4, 3]], synthetic: false },
    ],
    openings: [
      { id: "O2", floor_id: "F0", space_ids: ["A", "outside"], kind: "entrance", position: [2, 0], width_m: 1.2, step_free: true, synthetic: false },
      { id: "O1", floor_id: "F0", space_ids: ["A", "B"], kind: "door", position: [4, 1.5], width_m: 1, step_free: true, synthetic: false },
    ],
    vertical_connectors: [
      { id: "V1", kind: "lift", name: "Lift", floor_ids: ["F0", "F1"], space_ids: ["B", "C"], step_free: true, synthetic: false },
    ],
    assets: [
      {
        id: "D1",
        name: "Desk 0.01-A",
        category: "furniture",
        type: "desk",
        space_id: "A",
        floor_id: "F0",
        position: [1, 1.5],
        footprint: { width_m: 2, depth_m: 1, rotation_deg: 90 },
        source: "generated",
      },
    ],
  };
}
