// The scene model: what the 2D and 3D views draw. compileScene derives it from a building; it holds no
// rendering state, so one scene can feed several views at once.
import type { Asset, Opening, Space, VerticalConnector } from "../building";

/** A point in the building's plan frame, in metres. x points right, y points up. */
export type Point = readonly [x: number, y: number];

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export interface BuildingScene {
  id: string;
  name: string;
  /** Lowest level first. */
  floors: FloorScene[];
  connectors: ConnectorShape[];
  bounds: Bounds;
}

export interface FloorScene {
  id: string;
  level: number;
  name: string;
  elevation: number;
  height: number;
  spaces: SpaceShape[];
  walls: Wall[];
  openings: OpeningMark[];
  assets: AssetShape[];
  bounds: Bounds;
}

export interface SpaceShape {
  id: string;
  type: Space["type"];
  roomType: string;
  name: string;
  ref: string;
  outline: Point[];
  /** The point farthest inside the outline, where a label fits best. */
  labelPoint: Point;
  /** Distance from labelPoint to the nearest edge. Views size labels with it. */
  labelRadius: number;
}

/** A straight wall piece along a space edge. Door gaps are already cut out. */
export interface Wall {
  spaceId: string;
  start: Point;
  end: Point;
}

export interface OpeningMark {
  id: string;
  kind: Opening["kind"];
  spaceIds: Opening["space_ids"];
  position: Point;
  width: number;
  /** Unit vector along the wall the opening cuts, or null if no wall is near enough. */
  direction: Point | null;
  stepFree: boolean;
}

export interface AssetShape {
  id: string;
  name: string;
  category: Asset["category"];
  type: string;
  spaceId: string;
  position: Point;
  width: number;
  depth: number;
  rotationDeg: number;
  /** Footprint corners, counterclockwise. */
  corners: readonly [Point, Point, Point, Point];
}

export interface ConnectorShape {
  id: string;
  kind: VerticalConnector["kind"];
  name: string;
  stepFree: boolean;
  /** One stop per served floor, in source order. The point is the stop space's label point. */
  stops: { floorId: string; spaceId: string; point: Point }[];
}
