import type { PathPoint } from "@building/view";

/** How far ahead on the route the arrow points. It smooths small bends but still shows the next turn early. */
const LOOKAHEAD_M = 3;
/** Within this walking distance of the route's end, the walker has arrived. */
const ARRIVED_M = 1.5;
/**
 * A walker this close to the route walks parallel to it instead of back onto the line, so the arrow does not lead
 * into furniture beside the line. Further away, the arrow leads back to this distance.
 */
const BAND_M = 1.5;
/** Smaller turns show as straight ahead, so the arrow does not wobble while the walker keeps roughly on course. */
const STRAIGHT_DEG = 20;

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
 * The arrow for a live camera position, relative to where the camera looks. It takes the walker's nearest point on
 * the route and the route a few metres past it. Near the route, the arrow points parallel to it; towards the next
 * door or corner it leads to the line, so the walker meets the door. Only the route's part on the walker's floor
 * counts; where the route leaves that floor, the arrow points to the stair or lift. Undefined when the route does
 * not touch the floor.
 */
export function liveArrow(path: readonly PathPoint[], pose: Pose): LiveArrow | undefined {
  const along = [0];
  for (let i = 1; i < path.length; i++) along.push(along[i - 1]! + distance(path[i - 1]!, path[i]!));

  let nearest: { x: number; y: number; gap: number; at: number; index: number } | undefined;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1]!;
    const b = path[i]!;
    if (a.floor_id !== pose.floorId || b.floor_id !== pose.floorId) continue;
    const length = along[i]! - along[i - 1]!;
    const t = length === 0 ? 0 : clamp(((pose.x - a.x) * (b.x - a.x) + (pose.y - a.y) * (b.y - a.y)) / length ** 2);
    const x = a.x + t * (b.x - a.x);
    const y = a.y + t * (b.y - a.y);
    const gap = Math.hypot(x - pose.x, y - pose.y);
    if (!nearest || gap < nearest.gap) nearest = { x, y, gap, at: along[i - 1]! + t * length, index: i };
  }
  if (!nearest) return undefined;
  if (path.at(-1)!.floor_id === pose.floorId && along.at(-1)! - nearest.at < ARRIVED_M) return { kind: "arrive" };

  // Shift the point ahead by the walker's offset from the route: fully inside the band, so the arrow runs parallel,
  // and less towards the end of the segment, where the next door or corner is.
  const ahead = pointAlong(path, along, nearest.at + LOOKAHEAD_M, nearest.index, pose.floorId);
  const toCorner = along[nearest.index]! - nearest.at;
  const keep = nearest.gap === 0 ? 0 : Math.min(1, BAND_M / nearest.gap) * clamp(toCorner / LOOKAHEAD_M);
  const target = { x: ahead.x + (pose.x - nearest.x) * keep, y: ahead.y + (pose.y - nearest.y) * keep };
  const bearingDeg = (Math.atan2(target.y - pose.y, target.x - pose.x) * 180) / Math.PI;
  const turnDeg = signedDeg(bearingDeg - pose.headingDeg);
  return { kind: "turn", turnDeg: Math.abs(turnDeg) < STRAIGHT_DEG ? 0 : turnDeg };
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
