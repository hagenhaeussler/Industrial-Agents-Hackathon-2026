import polylabel from "polylabel";

import { OUTSIDE, type Asset, type Building, type Opening, type Space } from "../building";
import { boundsOf, byId, round, roundPoint } from "./geometry";
import type { AssetShape, BuildingScene, ConnectorShape, FloorScene, Point, SpaceShape } from "./types";
import { spaceWalls } from "./walls";

/** The building references something that does not exist. Lists every problem found. */
export class SceneError extends Error {
  constructor(readonly problems: string[]) {
    super(`building cannot be drawn: ${problems.join("; ")}`);
    this.name = "SceneError";
  }
}

/**
 * Derive the scene that the views draw. The result depends only on the building content, not on the
 * order of its lists, and the function has no side effects.
 */
export function compileScene(building: Building): BuildingScene {
  checkReferences(building);

  const spaces = new Map(building.spaces.map((space) => [space.id, spaceShape(space)]));
  const openingsBySpace = new Map<string, Opening[]>();
  for (const opening of building.openings) {
    for (const spaceId of opening.space_ids) {
      if (spaceId !== OUTSIDE) openingsBySpace.set(spaceId, [...(openingsBySpace.get(spaceId) ?? []), opening]);
    }
  }

  const floors = [...building.floors]
    .sort((a, b) => a.level - b.level)
    .map((floor): FloorScene => {
      const floorSpaces = building.spaces
        .filter((space) => space.floor_id === floor.id)
        .map((space) => spaces.get(space.id)!)
        .sort(byId);
      const floorOpenings = building.openings.filter((opening) => opening.floor_id === floor.id).sort(byId);
      const floorAssets = building.assets.filter((asset) => asset.floor_id === floor.id).sort(byId);

      const walls = [];
      const directions = new Map<string, Point>();
      for (const space of floorSpaces) {
        const openings = [...(openingsBySpace.get(space.id) ?? [])].sort(byId).map((opening) => ({
          id: opening.id,
          position: opening.position,
          width: opening.width_m,
        }));
        const result = spaceWalls(space.id, space.outline, openings);
        walls.push(...result.walls);
        // The first space in id order decides the direction, so the result is stable.
        for (const [id, direction] of result.directions) if (!directions.has(id)) directions.set(id, direction);
      }

      return {
        id: floor.id,
        level: floor.level,
        name: floor.name,
        elevation: floor.elevation_m,
        height: floor.height_m,
        spaces: floorSpaces,
        walls,
        openings: floorOpenings.map((opening) => ({
          id: opening.id,
          kind: opening.kind,
          spaceIds: opening.space_ids,
          position: opening.position,
          width: opening.width_m,
          direction: directions.get(opening.id) ?? null,
          stepFree: opening.step_free,
        })),
        assets: floorAssets.map(assetShape),
        bounds: boundsOf(floorSpaces.flatMap((space) => space.outline)),
      };
    });

  const connectors = [...building.vertical_connectors].sort(byId).map(
    (connector): ConnectorShape => ({
      id: connector.id,
      kind: connector.kind,
      name: connector.name,
      stepFree: connector.step_free,
      stops: connector.space_ids.map((spaceId, index) => ({
        floorId: connector.floor_ids[index]!,
        spaceId,
        point: spaces.get(spaceId)!.labelPoint,
      })),
    }),
  );

  return {
    id: building.building.id,
    name: building.building.name,
    floors,
    connectors,
    bounds: boundsOf([...spaces.values()].flatMap((space) => space.outline)),
  };
}

function spaceShape(space: Space): SpaceShape {
  const label = polylabel([space.polygon.map(([x, y]): [number, number] => [x, y])], 0.05);
  return {
    id: space.id,
    type: space.type,
    roomType: space.room_type,
    name: space.name,
    ref: space.ref,
    outline: space.polygon,
    labelPoint: roundPoint(label[0], label[1]),
    labelRadius: round(label.distance),
  };
}

function assetShape(asset: Asset): AssetShape {
  const { width_m: width, depth_m: depth, rotation_deg: rotationDeg } = asset.footprint;
  const [x, y] = asset.position;
  // The footprint's width lies along x before it turns counterclockwise by rotation_deg.
  const angle = (rotationDeg * Math.PI) / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const corner = (u: number, v: number) => roundPoint(x + u * cos - v * sin, y + u * sin + v * cos);
  return {
    id: asset.id,
    name: asset.name,
    category: asset.category,
    type: asset.type,
    spaceId: asset.space_id,
    position: asset.position,
    width,
    depth,
    rotationDeg,
    corners: [
      corner(-width / 2, -depth / 2),
      corner(width / 2, -depth / 2),
      corner(width / 2, depth / 2),
      corner(-width / 2, depth / 2),
    ],
  };
}

function checkReferences(building: Building): void {
  const problems: string[] = [];
  const floorIds = new Set(building.floors.map((floor) => floor.id));
  const spaceFloor = new Map(building.spaces.map((space) => [space.id, space.floor_id]));

  const requireFloor = (owner: string, floorId: string) => {
    if (!floorIds.has(floorId)) problems.push(`${owner} is on unknown floor ${floorId}`);
  };
  const requireSpace = (owner: string, spaceId: string, floorId: string) => {
    const actual = spaceFloor.get(spaceId);
    if (actual === undefined) problems.push(`${owner} refers to unknown space ${spaceId}`);
    else if (actual !== floorId) problems.push(`${owner} refers to space ${spaceId} on another floor`);
  };

  for (const space of building.spaces) requireFloor(`space ${space.id}`, space.floor_id);
  for (const opening of building.openings) {
    requireFloor(`opening ${opening.id}`, opening.floor_id);
    for (const spaceId of opening.space_ids) {
      if (spaceId !== OUTSIDE) requireSpace(`opening ${opening.id}`, spaceId, opening.floor_id);
    }
  }
  for (const asset of building.assets) {
    requireFloor(`asset ${asset.id}`, asset.floor_id);
    requireSpace(`asset ${asset.id}`, asset.space_id, asset.floor_id);
  }
  for (const connector of building.vertical_connectors) {
    if (connector.floor_ids.length !== connector.space_ids.length) {
      problems.push(`connector ${connector.id} has ${connector.floor_ids.length} floors but ${connector.space_ids.length} spaces`);
    }
    connector.space_ids.forEach((spaceId, index) => {
      const floorId = connector.floor_ids[index] ?? "";
      requireSpace(`connector ${connector.id}`, spaceId, floorId);
    });
  }
  if (problems.length > 0) throw new SceneError(problems);
}
