import type { PathPoint } from "@building/view";

/** How far ahead on the route the arrow points. It smooths small bends but still shows the next turn early. */
const LOOKAHEAD_M = 3;
/** Within this walking distance of the route's end, the walker has arrived. */
const ARRIVED_M = 1.5;

/** A camera position with the viewing direction, counterclockwise from +x like the plan. */
export interface Pose {
  floorId: string;
  x: number;
  y: number;
  headingDeg: number;
}

/** `turnDeg` is counterclockwise from straight ahead, so positive means left. */
export type LiveArrow = { kind: "turn"; turnDeg: number } | { kind: "arrive" };

/**
 * The arrow for a live camera position. It points from the walker to the route a few metres past their nearest
 * point on it, relative to where the camera looks. Only the route's part on the walker's floor counts; where the
 * route leaves that floor, the arrow points to the stair or lift. Undefined when the route does not touch the floor.
 */
export function liveArrow(path: readonly PathPoint[], pose: Pose): LiveArrow | undefined {
  const along = [0];
  for (let i = 1; i < path.length; i++) along.push(along[i - 1]! + distance(path[i - 1]!, path[i]!));

  let nearest: { gap: number; at: number; index: number } | undefined;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1]!;
    const b = path[i]!;
    if (a.floor_id !== pose.floorId || b.floor_id !== pose.floorId) continue;
    const length = along[i]! - along[i - 1]!;
    const t = length === 0 ? 0 : clamp(((pose.x - a.x) * (b.x - a.x) + (pose.y - a.y) * (b.y - a.y)) / length ** 2);
    const gap = Math.hypot(a.x + t * (b.x - a.x) - pose.x, a.y + t * (b.y - a.y) - pose.y);
    if (!nearest || gap < nearest.gap) nearest = { gap, at: along[i - 1]! + t * length, index: i };
  }
  if (!nearest) return undefined;
  if (path.at(-1)!.floor_id === pose.floorId && along.at(-1)! - nearest.at < ARRIVED_M) return { kind: "arrive" };

  const target = pointAlong(path, along, nearest.at + LOOKAHEAD_M, nearest.index, pose.floorId);
  const bearingDeg = (Math.atan2(target.y - pose.y, target.x - pose.x) * 180) / Math.PI;
  return { kind: "turn", turnDeg: signedDeg(bearingDeg - pose.headingDeg) };
}

/** An angle in (-180, 180]. */
export function signedDeg(angle: number): number {
  const turned = ((angle % 360) + 360) % 360;
  return turned > 180 ? turned - 360 : turned;
}

function pointAlong(path: readonly PathPoint[], along: number[], at: number, from: number, floorId: string) {
  for (let i = from; i < path.length; i++) {
    const a = path[i - 1]!;
    const b = path[i]!;
    if (b.floor_id !== floorId) return a;
    if (along[i]! >= at) {
      const t = clamp((at - along[i - 1]!) / (along[i]! - along[i - 1]!));
      return { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) };
    }
  }
  return path.at(-1)!;
}

const distance = (a: PathPoint, b: PathPoint) => Math.hypot(b.x - a.x, b.y - a.y);
const clamp = (value: number) => Math.min(1, Math.max(0, value));
