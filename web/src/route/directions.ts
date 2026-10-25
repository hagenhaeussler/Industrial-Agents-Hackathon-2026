import type { Building, PathPoint, RouteView } from "@building/view";

/** How a step changes direction, seen from the walker. Computed from the plan, not from a live position. */
export type Turn = "start" | "straight" | "left" | "right" | "up" | "down" | "arrive";

export interface Step {
  instruction: string;
  /** The floor where the step happens. */
  floorName: string;
  turn: Turn;
  /** Where the step happens on the plan. */
  at: PathPoint;
}

/** The parts of the building document that directions read. */
export type BuildingIndex = Pick<Building, "floors" | "spaces" | "openings">;

const STRAIGHT_DEG = 35;

/**
 * Turn-by-turn wording for a route the building tools returned. It only names the spaces and elements of the
 * route in order and reads turns off the drawing points. It never chooses a path.
 */
export function directions(view: RouteView, building: BuildingIndex): Step[] {
  const { route, path } = view;
  const first = route.legs[0];
  const last = route.legs.at(-1);
  if (!route.reachable || !first || !last || path.length === 0) return [];

  const floorName = (floorId: string) => building.floors.find((floor) => floor.id === floorId)?.name ?? "";
  const level = (floorId: string) => building.floors.find((floor) => floor.id === floorId)?.level ?? 0;
  const spaceFloor = (spaceId: string) => building.spaces.find((space) => space.id === spaceId)?.floor_id ?? "";
  const step = (instruction: string, turn: Turn, at: PathPoint): Step => ({
    instruction,
    turn,
    at,
    floorName: floorName(at.floor_id),
  });

  const steps: Step[] = [step(`Start in ${first.start.name}`, "start", path[0]!)];
  let cursor = 0;
  route.legs.forEach((leg, legIndex) => {
    leg.elements.forEach((element, index) => {
      const next = leg.spaces[index + 1] ?? leg.end;
      if (element.kind === "stairs" || element.kind === "lift") {
        const change = path.findIndex((point, i) => i >= cursor && path[i + 1]?.floor_id !== point.floor_id);
        if (change === -1) return;
        const from = path[change]!;
        const to = spaceFloor(next.id);
        const name = element.name ?? (element.kind === "lift" ? "the lift" : "the stairs");
        steps.push(step(`Take ${name} to ${next.floor_name}`, level(to) > level(from.floor_id) ? "up" : "down", from));
        cursor = change + 1;
        return;
      }
      const position = building.openings.find((opening) => opening.id === element.id)?.position;
      const found = position
        ? path.findIndex((point, i) => i >= cursor && point.x === position[0] && point.y === position[1])
        : -1;
      const at = found === -1 ? path[cursor]! : path[found]!;
      if (found !== -1) cursor = found;
      const verb =
        element.kind === "door" ? "Go through the door into" : element.kind === "entrance" ? "Enter" : "Continue into";
      steps.push(step(`${verb} ${next.name}`, found === -1 ? "straight" : turnAt(path, found), at));
    });
    const isLast = legIndex === route.legs.length - 1;
    steps.push(step(`${isLast ? "Arrive at" : "Stop at"} ${leg.end.name}`, "arrive", isLast ? path.at(-1)! : path[cursor]!));
  });
  return steps;
}

/** Left, right or straight at path point `index`, from the walking direction before and after it. */
export function turnAt(path: PathPoint[], index: number): Turn {
  const before = path[index - 1];
  const here = path[index];
  const after = path[index + 1];
  if (!before || !here || !after) return "straight";
  if (before.floor_id !== here.floor_id || after.floor_id !== here.floor_id) return "straight";
  const inX = here.x - before.x;
  const inY = here.y - before.y;
  const outX = after.x - here.x;
  const outY = after.y - here.y;
  // The plan's y axis points up, so a positive cross product is a turn to the left.
  const angle = (Math.atan2(inX * outY - inY * outX, inX * outX + inY * outY) * 180) / Math.PI;
  if (Math.abs(angle) < STRAIGHT_DEG) return "straight";
  return angle > 0 ? "left" : "right";
}
