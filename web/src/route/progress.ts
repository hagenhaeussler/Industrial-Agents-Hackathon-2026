import type { Route } from "@building/view";

/**
 * The stops still ahead when the camera puts the walker in `spaceId`. Leg `i` of `route` ends at `to[i]`. The walker
 * is on the first leg that passes their room, so earlier stops are done, and so is that leg's end once they stand
 * in it. Off the route, or before the route has loaded, every stop is still ahead.
 */
export function stopsAhead(route: Route | undefined, spaceId: string, to: string[]): string[] {
  const leg = route?.legs.findIndex((candidate) => candidate.spaces.some((space) => space.id === spaceId)) ?? -1;
  if (leg === -1) return to;
  return to.slice(to[leg] === spaceId ? leg + 1 : leg);
}
