import type { Polygon } from "geojson";
import buildings from "./buildings.json";

export interface ArrivalBuilding {
  id: string;
  label: string;
  center: [number, number];
  bounds: [number, number, number, number];
  outline: Polygon;
  height: number;
}

// Geographic metadata from feature/campus-explorer's OSM catalogue. No indoor models are needed.
export const arrivalBuildings = buildings as ArrivalBuilding[];
