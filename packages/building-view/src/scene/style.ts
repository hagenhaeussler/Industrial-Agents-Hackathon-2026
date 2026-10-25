// Colours shared by the 2D and 3D views, so a space or asset looks the same in both.
import type { SpaceShape } from "./types";

export const spaceColors: Record<SpaceShape["type"], string> = {
  room: "#f4f1ea",
  corridor: "#e3e1dc",
  hall: "#ece5d5",
  stair: "#f1d29a",
  lift: "#bfd4ef",
  outdoor: "#d7e7cf",
};

const assetColors: Record<string, string> = {
  furniture: "#a5998a",
  fixture: "#7f9bb3",
  machine: "#c26f3d",
  equipment: "#6e8f5d",
};

export function assetColor(category: string): string {
  return assetColors[category] ?? "#9a9a9a";
}

export const colors = {
  wall: "#3b3833",
  door: "#8d867b",
  entrance: "#2f7d4f",
  label: "#2b2925",
  route: "#2563eb",
  position: "#2563eb",
  highlight: "#f59e0b",
  closed: "#dc2626",
};
