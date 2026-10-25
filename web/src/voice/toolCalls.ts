import type { RouteRequest } from "../api/buildings";

const isStrings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

/**
 * The route the voice agent just planned, read from its `route` tool call. The UI loads the same route with
 * drawing points from the building API, so it shows exactly what the agent described.
 */
export function routeFromToolCall(name: string, parameters: Record<string, unknown>): RouteRequest | undefined {
  if (name !== "route" || !isStrings(parameters.stops) || parameters.stops.length < 2) return undefined;
  return {
    stops: parameters.stops,
    stepFree: parameters.step_free === true,
    closed: isStrings(parameters.closed) ? parameters.closed : [],
    minDoorWidthM: typeof parameters.min_door_width_m === "number" ? parameters.min_door_width_m : undefined,
  };
}
