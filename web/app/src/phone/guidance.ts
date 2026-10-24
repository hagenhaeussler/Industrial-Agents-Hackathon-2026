import type { Maneuver, Point, Position, ReachableRoute, Tour, TourStop, UnreachableReason } from '../api/types';
import type { Model } from '../map/model';
import { floorName, spaceName } from '../map/model';

/** Pending stops in tour order; the server replans so that `legs[0]` always leads to the first of them. */
export function pendingStops(tour: Tour): TourStop[] {
  const byId = new Map(tour.stops.map(stop => [stop.stop_id, stop]));
  return tour.order.map(id => byId.get(id)).filter((stop): stop is TourStop => !!stop && stop.status === 'pending');
}

export const collectedCount = (tour: Tour) => tour.stops.filter(stop => stop.status === 'collected').length;
/** Completion belongs to the server: collected parts can still leave a final walk. */
export const tourDone = (tour: Tour) => tour.status === 'completed';
export const finalDestinationPending = (tour: Tour) => !!tour.end && !tourDone(tour) && tour.stops.every(stop => stop.status === 'collected');
/** C7 compatibility names share the server-authoritative completion semantics. */
export const isComplete = tourDone;
export const END_STOP = 'end';
export function finalLegIndex(tour: Tour): number {
  if (!finalDestinationPending(tour)) return -1;
  const index = tour.legs.length - 1;
  const leg = tour.legs[index];
  return leg?.reachable && leg.to_space_id === tour.end!.space_id ? index : -1;
}
export const onFinalLeg = (tour: Tour) => finalLegIndex(tour) !== -1;

/** The reserved `end` progress ID is a destination, never another collected part. */
export function currentTarget(tour: Tour, model?: Model): TourStop | null {
  if (tourDone(tour)) return null;
  const stop = pendingStops(tour)[0];
  if (stop) return stop;
  if (!finalDestinationPending(tour) || !tour.end) return null;
  return { stop_id: 'end', space_id: tour.end.space_id, asset_ids: [], status: 'pending',
    label: model ? spaceName(model, tour.end.space_id) : 'Final destination' };
}

export const destinationLabel = (tour: Tour, model?: Model) => tour.end && model ? spaceName(model, tour.end.space_id) : 'Final destination';
export const stopLabel = (tour: Tour, stopId: string, model?: Model) => stopId === 'end' ? destinationLabel(tour, model) : tour.stops.find(stop => stop.stop_id === stopId)?.label ?? 'A stop';

/** The leg that leads to the current stop: the first leg arriving there (normally `legs[0]`). */
export function currentLeg(tour: Tour): ReachableRoute | null {
  const index = currentLegIndex(tour);
  const leg = index < 0 ? undefined : tour.legs[index];
  return leg?.reachable ? leg : null;
}

export function currentLegIndex(tour: Tour): number {
  const next = currentTarget(tour);
  if (!next) return -1;
  if (next.stop_id === 'end') {
    const last = tour.legs.length - 1;
    return tour.legs[last]?.to_space_id === next.space_id ? last : -1;
  }
  const index = tour.legs.findIndex(item => item.to_space_id === next.space_id);
  return index === -1 ? 0 : index;
}

/** Why the current stop cannot be reached, if it cannot. */
export function blockedReason(tour: Tour): { reason: UnreachableReason | string; blocking: string[] } | null {
  const next = currentTarget(tour);
  if (!next) {
    const listed = tour.unreachable_stops.find(item => item.stop_id !== 'end' && tour.stops.some(stop => stop.stop_id === item.stop_id && stop.status === 'pending'));
    return listed ? { reason: listed.reason, blocking: listed.blocking_ids ?? [] } : null;
  }
  const listed = tour.unreachable_stops.find(item => item.stop_id === next.stop_id);
  if (listed) return { reason: listed.reason, blocking: listed.blocking_ids ?? [] };
  const leg = tour.legs[currentLegIndex(tour)];
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

/** The lift or stair the new route uses, for "New route via …" (only vertical connectors are named). */
export function viaLandmark(tour: Tour, model?: Model): string | null {
  const leg = currentLeg(tour);
  if (!leg) return null;
  const vertical = leg.segments.find(segment => segment.kind === 'lift' || segment.kind === 'stairs');
  const connector = vertical?.kind === 'walk' ? undefined : vertical ? model?.connector.get(vertical.element_id)?.name : undefined;
  return leg.maneuvers.find(item => item.kind === 'take_lift' || item.kind === 'take_stairs')?.landmark ?? connector ?? null;
}

const subjectOf = (summary: string) => /^(?:undo:\s*)?(?:close|open|reopen)\s+(.+?)\.?$/i.exec(summary)?.[1] ?? null;
const list = (items: string[]) => items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
const stopName = (tour: Tour, stopId: string, model?: Model) => stopId === END_STOP && !model ? 'your finish point' : stopLabel(tour, stopId, model).split(' · ')[0];
const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const REASON: Record<string, string> = { no_step_free_path: 'no step-free way', blocked_by_closure: 'blocked by a closure', too_narrow: 'the doors are too narrow', disconnected: 'not connected' };

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
  const stepFree = after.constraints.step_free;
  const wasBlocked = new Set(before.unreachable_stops.map(item => item.stop_id));
  const nowBlocked = new Set(after.unreachable_stops.map(item => item.stop_id));
  const lost = [...nowBlocked].filter(id => !wasBlocked.has(id));
  const regained = [...wasBlocked].filter(id => !nowBlocked.has(id));
  if (lost.length) {
    const subject = subjectOf(rawSummary);
    const why = stepFree && subject && /^close/i.test(rawSummary) ? `: the ${subject} was the only step-free way there` : '';
    const rest = pendingStops(after).length ? ' The other stops are replanned.' : '';
    return { text: `${summary}. ${capital(list(lost.map(id => stopName(after, id, model))))} can no longer be reached${stepFree ? ' step-free' : ''}${why}.${rest}`, blocked: true };
  }
  const blocked = blockedReason(after);
  if (blocked) {
    const target = finalDestinationPending(after) ? `the final destination (${destinationLabel(after, model)})` : 'the next stop';
    const why = blocked.reason === 'no_step_free_path' || stepFree ? `There is no step-free route to ${target} any more.` : `${target[0]!.toUpperCase()}${target.slice(1)} cannot be reached any more.`;
    return { text: `${summary}. ${why}`, blocked: true };
  }
  if (regained.length) return { text: `${summary}. ${capital(list(regained.map(id => stopName(after, id, model))))} can be reached again and is back in the tour.`, blocked: false };
  const delta = Math.round(remainingLength(after) - remainingLength(before));
  const via = viaLandmark(after, model);
  return { text: `${summary}. New route${via ? ` via ${via}` : ''}${delta > 0 ? ` (+${delta} m)` : delta < 0 ? ` (${delta} m)` : ''}.`, blocked: false };
}

/** CONTRACTS §8 context phrasings for the voice agent. */
const unavailableContext = (tour: Tour, model?: Model) => list(tour.unreachable_stops
  .filter(item => item.stop_id === 'end' ? !!tour.end && !tourDone(tour) : tour.stops.some(stop => stop.stop_id === item.stop_id && stop.status === 'pending'))
  .map(item => `${stopName(tour, item.stop_id, model)} (${REASON[item.reason] ?? item.reason.replaceAll('_', ' ')})`));
const nextContextLabel = (tour: Tour, model?: Model) => finalDestinationPending(tour) && !model ? 'the finish point' : currentTarget(tour, model)?.label ?? 'none';

export const context = {
  position: (model: Model, position: Position) => `Position: ${spaceName(model, position.space_id)} (${floorName(model, position.floor_id ?? model.space.get(position.space_id)?.floor_id ?? '')}), source ${position.source === 'tour_start' ? 'tour start' : position.source}.`,
  tourLoaded: (tour: Tour, model?: Model) => {
    const pending = pendingStops(tour).length;
    const what = tourDone(tour) ? 'completed' : pending ? `${pending} ${pending === 1 ? 'stop' : 'stops'}, next ${nextContextLabel(tour, model)}` : onFinalLeg(tour) ? `all parts collected, next ${nextContextLabel(tour, model)}` : 'no stop can be reached';
    const unavailable = unavailableContext(tour, model);
    return `Tour ${tour.tour_id} loaded: ${what}.${unavailable ? ` Not reachable now: ${unavailable}.` : ''}`;
  },
  replanned: (rawSummary: string, tour: Tour, model?: Model) => {
    const summary = humanSummary(rawSummary);
    const blocked = blockedReason(tour);
    const unavailable = unavailableContext(tour, model);
    if (!currentLeg(tour) && unavailable) return `Building changed: ${summary}. No route is available any more: ${unavailable}.`;
    const status = blocked ? `No route is available any more: ${REASON[blocked.reason] ?? blocked.reason}.` : `The active tour was replanned: ${Math.round(remainingLength(tour))} m, next ${nextContextLabel(tour, model)}.`;
    return `Building changed: ${summary}. ${status}${unavailable ? ` Not reachable now: ${unavailable}.` : ''}`;
  },
  collected: (label: string, tour: Tour) => `Stop collected: ${label}. ${collectedCount(tour)} of ${tour.stops.length} done.`,
};
