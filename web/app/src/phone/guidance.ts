import type { Maneuver, Point, Position, ReachableRoute, Tour, TourStop, UnreachableReason } from '../api/types';
import type { Model } from '../map/model';
import { floorName, spaceName } from '../map/model';

/** Pending stops in tour order; the server replans so that `legs[0]` always leads to the first of them. */
export function pendingStops(tour: Tour): TourStop[] {
  const byId = new Map(tour.stops.map(stop => [stop.stop_id, stop]));
  return tour.order.map(id => byId.get(id)).filter((stop): stop is TourStop => !!stop && stop.status === 'pending');
}

export const collectedCount = (tour: Tour) => tour.stops.filter(stop => stop.status === 'collected').length;

/** C7: with every part collected, an optional end destination keeps the tour active with one last leg. */
export function finalLegIndex(tour: Tour): number {
  if (pendingStops(tour).length || !tour.end || tour.status === 'completed') return -1;
  return tour.legs.findIndex(leg => leg.reachable && leg.to_space_id === tour.end!.space_id);
}
export const onFinalLeg = (tour: Tour) => finalLegIndex(tour) !== -1;

/** The leg that leads to the current stop (normally `legs[0]`), or the final leg to the end destination. */
export function currentLeg(tour: Tour): ReachableRoute | null {
  const next = pendingStops(tour)[0];
  if (!next) { const leg = tour.legs[finalLegIndex(tour)]; return leg?.reachable ? leg : null; }
  const leg = tour.legs.find(item => item.to_space_id === next.space_id) ?? tour.legs[0];
  return leg?.reachable ? leg : null;
}

export function currentLegIndex(tour: Tour): number {
  const next = pendingStops(tour)[0];
  if (!next) return finalLegIndex(tour);
  const index = tour.legs.findIndex(item => item.to_space_id === next.space_id);
  return index === -1 ? 0 : index;
}

/** Done: the server says so, or every part is collected and no final leg or unreachable stop is left. */
export function isComplete(tour: Tour): boolean {
  if (tour.status === 'completed') return true;
  if (!tour.stops.length || tour.unreachable_stops.length || pendingStops(tour).length) return false;
  return tour.stops.every(stop => stop.status === 'collected') && !onFinalLeg(tour);
}

/** Reserved progress id for arriving at the end destination (CR-H-4 / C7). */
export const END_STOP = 'end';

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
const stopName = (tour: Tour, stopId: string) => (stopId === END_STOP ? 'your finish point' : tour.stops.find(stop => stop.stop_id === stopId)?.label.split(' · ')[0] ?? 'a stop');
const REASON: Record<string, string> = { no_step_free_path: 'no step-free way', blocked_by_closure: 'blocked by a closure', too_narrow: 'the doors are too narrow', disconnected: 'not connected' };
const unreachableList = (tour: Tour) => list(tour.unreachable_stops.map(item => `${stopName(tour, item.stop_id)} (${REASON[item.reason] ?? String(item.reason).replace(/_/g, ' ')})`));
const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

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
    return { text: `${summary}. ${capital(list(lost.map(id => stopName(after, id))))} can no longer be reached${stepFree ? ' step-free' : ''}${why}.${rest}`, blocked: true };
  }
  const blocked = blockedReason(after);
  if (blocked) {
    const why = blocked.reason === 'no_step_free_path' || stepFree ? 'There is no step-free route to the next stop any more.' : 'The next stop cannot be reached any more.';
    return { text: `${summary}. ${why}`, blocked: true };
  }
  if (regained.length) return { text: `${summary}. ${capital(list(regained.map(id => stopName(after, id))))} can be reached again and is back in the tour.`, blocked: false };
  const delta = Math.round(remainingLength(after) - remainingLength(before));
  const via = viaLandmark(after, model);
  return { text: `${summary}. New route${via ? ` via ${via}` : ''}${delta > 0 ? ` (+${delta} m)` : delta < 0 ? ` (${delta} m)` : ''}.`, blocked: false };
}

/** The persistent banner for stops (or the finish) that cannot be reached, with the change that caused it when known. */
export function unavailableText(tour: Tour): string {
  const cause = tour.changed_because?.summary ? `${humanSummary(tour.changed_because.summary)}. ` : '';
  const names = capital(list(tour.unreachable_stops.map(item => stopName(tour, item.stop_id))));
  return `${cause}${names} cannot be reached${tour.constraints.step_free ? ' step-free' : ''} right now.`;
}

const nextLabel = (tour: Tour) => pendingStops(tour)[0]?.label ?? (onFinalLeg(tour) ? 'the finish point' : 'none');

/** CONTRACTS §8 context phrasings for the voice agent. */
export const context = {
  position: (model: Model, position: Position) => `Position: ${spaceName(model, position.space_id)} (${floorName(model, position.floor_id ?? model.space.get(position.space_id)?.floor_id ?? '')}), source ${position.source === 'tour_start' ? 'tour start' : position.source}.`,
  tourLoaded: (tour: Tour) => {
    const pending = pendingStops(tour).length;
    const what = pending ? `${pending} ${pending === 1 ? 'stop' : 'stops'}, next ${nextLabel(tour)}` : onFinalLeg(tour) ? 'all parts collected, next the finish point' : 'no stop can be reached';
    return `Tour ${tour.tour_id} loaded: ${what}.${tour.unreachable_stops.length ? ` Not reachable now: ${unreachableList(tour)}.` : ''}`;
  },
  /** CR-M-3: a fully blocked tour says which stop and why, never "replanned: 0 m, next none". */
  replanned: (rawSummary: string, tour: Tour) => {
    const summary = humanSummary(rawSummary);
    const routed = pendingStops(tour).length > 0 || onFinalLeg(tour);
    if (!routed && tour.unreachable_stops.length) return `Building changed: ${summary}. No route is available any more: ${unreachableList(tour)}.`;
    const blocked = blockedReason(tour);
    if (blocked && !routed) return `Building changed: ${summary}. No route is available any more: ${REASON[blocked.reason] ?? blocked.reason}.`;
    const missing = tour.unreachable_stops.length ? ` Not reachable now: ${unreachableList(tour)}.` : '';
    return `Building changed: ${summary}. The active tour was replanned: ${Math.round(remainingLength(tour))} m, next ${nextLabel(tour)}.${missing}`;
  },
  collected: (label: string, tour: Tour) => `Stop collected: ${label}. ${collectedCount(tour)} of ${tour.stops.length} done.`,
};
