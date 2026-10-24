import type { Maneuver, Point, Position, ReachableRoute, Tour, TourStop, UnreachableReason } from '../api/types';
import type { Model } from '../map/model';
import { floorName, spaceName } from '../map/model';

/** Pending stops in tour order; the server replans so that `legs[0]` always leads to the first of them. */
export function pendingStops(tour: Tour): TourStop[] {
  const byId = new Map(tour.stops.map(stop => [stop.stop_id, stop]));
  return tour.order.map(id => byId.get(id)).filter((stop): stop is TourStop => !!stop && stop.status === 'pending');
}

export const collectedCount = (tour: Tour) => tour.stops.filter(stop => stop.status === 'collected').length;

/** The leg that leads to the current stop: the first leg arriving there (normally `legs[0]`). */
export function currentLeg(tour: Tour): ReachableRoute | null {
  const next = pendingStops(tour)[0];
  if (!next) return null;
  const leg = tour.legs.find(item => item.to_space_id === next.space_id) ?? tour.legs[0];
  return leg?.reachable ? leg : null;
}

export function currentLegIndex(tour: Tour): number {
  const next = pendingStops(tour)[0];
  if (!next) return -1;
  const index = tour.legs.findIndex(item => item.to_space_id === next.space_id);
  return index === -1 ? 0 : index;
}

/** Why the current stop cannot be reached, if it cannot. */
export function blockedReason(tour: Tour): { reason: UnreachableReason | string; blocking: string[] } | null {
  const next = pendingStops(tour)[0];
  if (!next) return null;
  const listed = tour.unreachable_stops.find(item => item.stop_id === next.stop_id);
  if (listed) return { reason: listed.reason, blocking: listed.blocking_ids ?? [] };
  const leg = tour.legs.find(item => item.to_space_id === next.space_id);
  if (leg && !leg.reachable) return { reason: leg.reason, blocking: leg.blocking_ids };
  if (!tour.legs.length) return { reason: 'disconnected', blocking: [] };
  return null;
}

export const clampStep = (leg: ReachableRoute | null, step: number) => (leg ? Math.max(0, Math.min(step, leg.maneuvers.length - 1)) : 0);

/** Metres still to walk on this leg from the shown maneuver: the next maneuvers' distances. */
export function metresAhead(leg: ReachableRoute, step: number): number {
  return Math.round(leg.maneuvers.slice(step + 1).reduce((sum, item) => sum + item.distance_m, 0));
}

/** Distance to the next maneuver point, which is what the banner shows next to the instruction. */
export const metresToNext = (leg: ReachableRoute, step: number) => Math.round(leg.maneuvers[step + 1]?.distance_m ?? 0);

/** Display text: drops bracketed kit IDs that provisional adapter texts still carry ("Office 0.30 [proc-…-S030]"). */
export const cleanText = (text: string) => text.replace(/\s*\[[^\]]*\]/g, '').replace(/\s{2,}/g, ' ').trim();

export const atStop = (leg: ReachableRoute | null, step: number) => !!leg && leg.maneuvers[clampStep(leg, step)]?.kind === 'arrive';

/** Ray casting; polygons are simple rings in building metres. */
export function pointInPolygon([x, y]: Point, polygon: readonly Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i]!, [xj, yj] = polygon[j]!;
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Where the person is after following steps: the shown maneuver's point, inside its room. Manual progress, not tracking. */
export function stepPosition(model: Model, maneuver: Maneuver): Position | null {
  const space = (model.spacesOn.get(maneuver.floor_id) ?? []).find(item => pointInPolygon(maneuver.at, item.polygon));
  if (!space) return null;
  return { space_id: space.id, floor_id: maneuver.floor_id, point: maneuver.at, source: 'manual', confidence: 'low', heading_deg: null, marker_id: null };
}

/** The first landmark the new route leads through (a lift or stair first), for "New route via …". */
export function viaLandmark(tour: Tour, model?: Model): string | null {
  const leg = currentLeg(tour);
  if (!leg) return null;
  const vertical = leg.segments.find(segment => segment.kind === 'lift' || segment.kind === 'stairs');
  const connector = vertical?.kind === 'walk' ? undefined : vertical ? model?.connector.get(vertical.element_id)?.name : undefined;
  return leg.maneuvers.find(item => item.kind === 'take_lift' || item.kind === 'take_stairs')?.landmark ?? connector
    ?? leg.maneuvers.find(item => item.landmark && item.kind !== 'depart' && item.kind !== 'arrive')?.landmark ?? null;
}

/** "Close Office staircase" → "Office staircase is closed"; "Undo: Close X" → "X is open again". */
export function humanSummary(summary: string): string {
  const undo = /^undo:\s*/i.test(summary);
  const text = summary.replace(/^undo:\s*/i, '').replace(/\.$/, '');
  const close = /^close\s+(.+)$/i.exec(text), open = /^(?:open|reopen)\s+(.+)$/i.exec(text);
  if (close?.[1]) return undo ? `${close[1]} is open again` : `${close[1]} is closed`;
  if (open?.[1]) return undo ? `${open[1]} is closed again` : `${open[1]} is open again`;
  return undo ? `Undone: ${text}` : text;
}

export const remainingLength = (tour: Tour) => tour.legs.reduce((sum, leg) => sum + (leg.reachable ? leg.length_m : 0), 0);

/** The banner text after a building change (UX J6/J6b). */
export function rerouteNotice(rawSummary: string, before: Tour, after: Tour, model?: Model): { text: string; blocked: boolean } {
  const summary = humanSummary(rawSummary);
  const blocked = blockedReason(after);
  if (blocked) {
    const why = blocked.reason === 'no_step_free_path' ? 'There is no step-free route to the next stop any more.' : 'The next stop cannot be reached any more.';
    return { text: `${summary}. ${why}`, blocked: true };
  }
  const delta = Math.round(remainingLength(after) - remainingLength(before));
  const via = viaLandmark(after, model);
  return { text: `${summary}. New route${via ? ` via ${via}` : ''}${delta > 0 ? ` (+${delta} m)` : delta < 0 ? ` (${delta} m)` : ''}.`, blocked: false };
}

/** CONTRACTS §8 context phrasings for the voice agent. */
export const context = {
  position: (model: Model, position: Position) => `Position: ${spaceName(model, position.space_id)} (${floorName(model, position.floor_id ?? model.space.get(position.space_id)?.floor_id ?? '')}), source ${position.source === 'tour_start' ? 'tour start' : position.source}.`,
  tourLoaded: (tour: Tour) => `Tour ${tour.tour_id} loaded: ${pendingStops(tour).length} stops, next ${pendingStops(tour)[0]?.label ?? 'none'}.`,
  replanned: (summary: string, tour: Tour) => {
    const blocked = blockedReason(tour);
    return blocked ? `Building changed: ${summary}. No route is available any more: ${blocked.reason}.` : `Building changed: ${summary}. The active tour was replanned: ${Math.round(remainingLength(tour))} m, next ${pendingStops(tour)[0]?.label ?? 'none'}.`;
  },
  collected: (label: string, tour: Tour) => `Stop collected: ${label}. ${collectedCount(tour)} of ${tour.stops.length} done.`,
};
