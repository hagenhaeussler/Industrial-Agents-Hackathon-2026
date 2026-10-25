// The building.json format, as served by the building API. The types are generated from the Pydantic models.
import type { components } from "./api.gen";

type Schemas = components["schemas"];

export type Building = Schemas["BuildingDocument"];
export type BuildingSummary = Schemas["BuildingSummary"];
export type BuildingImport = Schemas["BuildingImport"];
export type Floor = Schemas["Floor"];
export type Space = Schemas["Space"];
export type Opening = Schemas["Opening"];
export type VerticalConnector = Schemas["VerticalConnector"];
export type Asset = Schemas["Asset"];

/** A route from the building tools with the points to draw it (`GET /api/buildings/{id}/route`). */
export type RouteView = Schemas["RouteView"];
export type Route = Schemas["Route"];
export type RouteLeg = Schemas["RouteLeg"];
export type ElementStep = Schemas["ElementStep"];
export type PathPoint = Schemas["PathPoint"];

/** The space reference an entrance uses for the area outside the building. */
export const OUTSIDE = "outside";
