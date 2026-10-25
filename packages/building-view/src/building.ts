// The building.json format, as served by the building API. The types are generated from the Pydantic models.
import type { components } from "./api.gen";

type Schemas = components["schemas"];

export type Building = Schemas["BuildingDocument"];
export type BuildingSummary = Schemas["BuildingSummary"];
export type Floor = Schemas["Floor"];
export type Space = Schemas["Space"];
export type Opening = Schemas["Opening"];
export type VerticalConnector = Schemas["VerticalConnector"];
export type Asset = Schemas["Asset"];

/** The space reference an entrance uses for the area outside the building. */
export const OUTSIDE = "outside";
