import type { Display, Point, ReachableRoute } from '../api/types';
import type { Model } from './model';
import { sameBuildingState } from '../api/buildingState';

const point = (value: unknown): value is Point => Array.isArray(value) && value.length === 2 && value.every(n => typeof n === 'number' && Number.isFinite(n));

/** A route tool supplies its own geometry; never substitute the current collection tour. */
export function displayedRoute(display: Display | null | undefined, model: Model): ReachableRoute | null {
  if (display?.kind !== 'route' || !display.route || typeof display.route !== 'object') return null;
  const route = display.route as ReachableRoute;
  if (route.reachable !== true || route.building_id !== model.snapshot.building.building.id || !sameBuildingState(model.snapshot, route) || route.content_hash !== model.snapshot.content_hash) return null;
  if (!model.space.has(route.from_space_id) || !model.space.has(route.to_space_id) || !Number.isFinite(route.length_m) || route.length_m < 0 || !route.constraints || typeof route.constraints.step_free !== 'boolean' || !Array.isArray(route.segments) || !Array.isArray(route.maneuvers)) return null;
  if (!route.segments.every(segment => segment && model.floor.has(segment.floor_id) && Array.isArray(segment.points) && segment.points.every(point) && ['walk', 'lift', 'stairs'].includes(segment.kind))) return null;
  if (!route.maneuvers.every(maneuver => maneuver && model.floor.has(maneuver.floor_id) && point(maneuver.at) && typeof maneuver.text === 'string')) return null;
  return route;
}

/** All locations in a find/spatial response, including rooms returned on a different floor. */
export function displayedSpaces(display: Display, model: Model): string[] {
  return [...new Set([...(display.space_ids ?? []), ...(display.space_id ? [display.space_id] : []), ...(display.asset_ids ?? []).flatMap(id => model.asset.get(id)?.space_id ?? [])])].filter(id => model.space.has(id));
}

export const routeIsCurrent = (route: ReachableRoute | null, model: Model | null): route is ReachableRoute => !!route && !!model && route.building_id === model.snapshot.building.building.id && sameBuildingState(model.snapshot, route) && route.content_hash === model.snapshot.content_hash;
