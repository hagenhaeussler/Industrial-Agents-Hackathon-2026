// What a view draws on top of the building. The views only display these values; routes and positions
// come from the building tools.

/** A point on a floor, in the building's plan frame. */
export interface FloorPoint {
  floorId: string;
  x: number;
  y: number;
}

export type CoworkerMarker = FloorPoint & { id: string; name: string; color: string };

export interface Overlay {
  /** A walking path in order. Consecutive points on different floors are a change of floor. */
  route?: FloorPoint[];
  /** Where the user is. */
  position?: FloorPoint & { headingDeg?: number };
  /** Spaces or assets to emphasise. */
  highlightIds?: string[];
  /** Spaces, openings or connectors that cannot be used. */
  closedIds?: string[];
  /** AI coworkers at their current display positions. An empty list hides them. */
  coworkers?: CoworkerMarker[];
}

/** The entity under the pointer when the user clicks a view. */
export type PickResult =
  | { kind: "space" | "asset" | "opening"; id: string; floorId: string; x: number; y: number }
  | ({ kind: "coworker" } & CoworkerMarker);
