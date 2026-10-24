import { arrowBearing, orientationDelta } from '../camera/ar/OverlayArrow';
import type { Point, ReachableRoute } from '../api/types';

/**
 * Camera mode (UX J5/J5b, C04): a direction-only arrow over the live camera. The arrow is anchored by a
 * scanned position code (standing point + facing direction) and turned by the motion sensor since that
 * scan. It never claims position tracking: position still comes from steps and codes.
 */
export type Anchor = { point: Point; heading_deg: number; floor_id: string; alphaAtScan: number | null };

/** Where the arrow should point: the next maneuver on this floor, else the end of this floor's walk. */
export function nextWaypoint(leg: ReachableRoute, step: number): Point | null {
  const here = leg.maneuvers[step];
  if (!here) return null;
  const ahead = leg.maneuvers.slice(step + 1).find(item => item.floor_id === here.floor_id && Math.hypot(item.at[0] - here.at[0], item.at[1] - here.at[1]) > 0.5);
  if (ahead) return ahead.at;
  const walk = leg.segments.filter(segment => segment.kind === 'walk' && segment.floor_id === here.floor_id).at(-1);
  return walk?.points.at(-1) ?? null;
}

export type ArrowState =
  | { kind: 'arrow'; bearing: number; relative: boolean }
  | { kind: 'scan'; reason: 'no_anchor' | 'other_floor' }
  | { kind: 'arrived' }
  | { kind: 'none' };

/** What the camera overlay shows for the current step; `alpha` is the live device alpha or null without motion. */
export function arrowState(leg: ReachableRoute | null, step: number, position: Point | null, floorId: string, anchor: Anchor | null, alpha: number | null): ArrowState {
  if (!leg || !position) return { kind: 'none' };
  if (leg.maneuvers[step]?.kind === 'arrive') return { kind: 'arrived' };
  // a code scanned before the motion sensor ran has no reference angle: scan again with the sensor on
  if (!anchor || (alpha !== null && anchor.alphaAtScan === null)) return { kind: 'scan', reason: 'no_anchor' };
  if (anchor.floor_id !== floorId) return { kind: 'scan', reason: 'other_floor' };
  const target = nextWaypoint(leg, step);
  if (!target) return { kind: 'none' };
  const delta = alpha !== null && anchor.alphaAtScan !== null ? orientationDelta(alpha, anchor.alphaAtScan) : null;
  const bearing = arrowBearing({ position, headingDeg: anchor.heading_deg, deviceAlpha: delta, nextWaypoint: target });
  return bearing === null ? { kind: 'none' } : { kind: 'arrow', bearing, relative: delta === null };
}
