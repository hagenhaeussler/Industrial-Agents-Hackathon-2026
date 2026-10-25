import { compileScene, type Building, type BuildingScene, type BuildingSummary, type RouteView } from "@locora/view";
import { useQuery } from "@tanstack/react-query";

/** What a route must follow. The same flat rules the voice agent's route tool takes. */
export interface RouteRequest {
  stops: string[];
  stepFree?: boolean;
  closed?: string[];
  minDoorWidthM?: number;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    const body: { detail?: unknown } = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json();
}

export function routeQuery(buildingId: string, request: RouteRequest): string {
  const params = new URLSearchParams();
  for (const stop of request.stops) params.append("stops", stop);
  if (request.stepFree) params.set("step_free", "true");
  if (request.minDoorWidthM) params.set("min_door_width_m", String(request.minDoorWidthM));
  for (const id of request.closed ?? []) params.append("closed", id);
  return `/api/buildings/${encodeURIComponent(buildingId)}/route?${params}`;
}

export function useBuildings() {
  return useQuery({
    queryKey: ["buildings"],
    queryFn: ({ signal }) => getJson<BuildingSummary[]>("/api/buildings", signal),
    staleTime: Infinity,
  });
}

export interface LoadedBuilding {
  document: Building;
  scene: BuildingScene;
}

/** The building document and the scene both views draw. */
export function useBuilding(buildingId: string, enabled = true) {
  return useQuery({
    queryKey: ["building", buildingId],
    queryFn: async ({ signal }): Promise<LoadedBuilding> => {
      const document = await getJson<Building>(`/api/buildings/${encodeURIComponent(buildingId)}`, signal);
      return { document, scene: compileScene(document) };
    },
    staleTime: Infinity,
    enabled,
  });
}

/** The route from the building tools, or nothing while fewer than two stops are known. */
export function useRoute(buildingId: string, request: RouteRequest | undefined) {
  return useQuery({
    queryKey: ["route", buildingId, request],
    queryFn: ({ signal }) => getJson<RouteView>(routeQuery(buildingId, request!), signal),
    enabled: request !== undefined && request.stops.length >= 2,
    staleTime: Infinity,
  });
}
