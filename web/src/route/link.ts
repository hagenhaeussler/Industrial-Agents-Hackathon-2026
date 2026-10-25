import type { RouteRequest } from "../api/buildings";

/** The phone link a QR code carries. The phone loads the route itself, so no server session is needed. */
export function guideLink(origin: string, buildingId: string, request: Partial<RouteRequest>): string {
  return new URL(guidePath(buildingId, request), origin).toString();
}

/** The path and query of a phone link. An empty first stop means the start is not known yet. */
export function guidePath(buildingId: string, request: Partial<RouteRequest>): string {
  const params = new URLSearchParams();
  const [from, ...rest] = request.stops ?? [];
  if (from) params.set("from", from);
  for (const stop of rest) params.append("to", stop);
  if (request.stepFree) params.set("step_free", "1");
  const query = params.toString();
  return `/b/${encodeURIComponent(buildingId)}${query ? `?${query}` : ""}`;
}

/** Start, stops and rules from a phone link. The last `to` is the destination. */
export function readGuideLink(query: URLSearchParams): { from?: string; to: string[]; stepFree: boolean } {
  return { from: query.get("from") ?? undefined, to: query.getAll("to"), stepFree: query.get("step_free") === "1" };
}
