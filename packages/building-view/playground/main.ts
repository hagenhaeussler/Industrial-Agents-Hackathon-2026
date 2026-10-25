// Development page: one building from the API in the 2D plan and the 3D view side by side.
// Run `uv run python -m building_api serve buildings.sqlite3` in the repository, then `pnpm dev` here.
import {
  BuildingView3D,
  compileScene,
  FloorPlan,
  type Building,
  type BuildingScene,
  type BuildingSummary,
  type FloorPoint,
  type Overlay,
  type PickResult,
} from "../src";

const buildingSelect = document.querySelector<HTMLSelectElement>("#building")!;
const floorSelect = document.querySelector<HTMLSelectElement>("#floor")!;
const focus = document.querySelector<HTMLInputElement>("#focus")!;
const gap = document.querySelector<HTMLInputElement>("#gap")!;
const walls = document.querySelector<HTMLSelectElement>("#walls")!;
const labels = document.querySelector<HTMLInputElement>("#labels")!;
const assets = document.querySelector<HTMLInputElement>("#assets")!;
const status = document.querySelector<HTMLElement>("#status")!;

const plan = new FloorPlan(document.querySelector<HTMLElement>("#plan")!);
const model = new BuildingView3D(document.querySelector<HTMLElement>("#model")!);
let scene: BuildingScene | undefined;
let testPath: FloorPoint[] = [];
let picked: PickResult | null = null;

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return response.json();
}

async function loadBuilding(id: string): Promise<void> {
  const building = await getJson<Building>(`/api/buildings/${encodeURIComponent(id)}`);
  const started = performance.now();
  scene = compileScene(building);
  const compiled = performance.now() - started;
  floorSelect.replaceChildren(...scene.floors.map((floor) => new Option(`${floor.level}: ${floor.name}`, floor.id)));
  const ground = scene.floors.find((floor) => floor.level === 0) ?? scene.floors[0]!;
  floorSelect.value = ground.id;
  testPath = [];
  picked = null;
  model.show(scene);
  showFloor();
  status.textContent = `${scene.name}: ${scene.floors.length} floors, scene compiled in ${compiled.toFixed(0)} ms`;
}

function showFloor(): void {
  if (!scene) return;
  plan.show(scene, floorSelect.value);
  model.setFocusFloor(focus.checked ? floorSelect.value : null);
  updateOverlay();
}

function updateOverlay(): void {
  const overlay: Overlay = {
    route: testPath,
    highlightIds: picked ? [picked.id] : [],
    position: picked ? { floorId: picked.floorId, x: picked.x, y: picked.y } : undefined,
  };
  plan.setOverlay(overlay);
  model.setOverlay(overlay);
}

function onPick(pick: PickResult | null): void {
  picked = pick;
  status.textContent = pick ? `${pick.kind} ${pick.id} at ${pick.x.toFixed(2)}, ${pick.y.toFixed(2)}` : "Nothing selected";
  updateOverlay();
}

plan.onPick(onPick);
model.onPick(onPick);
plan.svg.addEventListener("click", (event) => {
  if (!event.shiftKey || !picked) return;
  testPath = [...testPath, { floorId: picked.floorId, x: picked.x, y: picked.y }];
  updateOverlay();
});
window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  testPath = [];
  updateOverlay();
});

buildingSelect.addEventListener("change", () => void loadBuilding(buildingSelect.value).catch(showError));
floorSelect.addEventListener("change", showFloor);
focus.addEventListener("change", showFloor);
gap.addEventListener("input", () => model.setOptions({ floorGap: Number(gap.value) }));
walls.addEventListener("change", () => model.setOptions({ wallHeight: walls.value === "full" ? "full" : Number(walls.value) }));
labels.addEventListener("change", () => {
  plan.setOptions({ labels: labels.checked });
  model.setOptions({ labels: labels.checked });
});
assets.addEventListener("change", () => {
  plan.setOptions({ assets: assets.checked });
  model.setOptions({ assets: assets.checked });
});

function showError(error: unknown): void {
  status.textContent = String(error);
}

const buildings = await getJson<BuildingSummary[]>("/api/buildings");
buildingSelect.replaceChildren(
  ...buildings.map((building) => new Option(`${building.id} (${building.floors} floors) ${building.name}`, building.id)),
);
const requested = new URLSearchParams(location.search).get("building");
buildingSelect.value = buildings.some((building) => building.id === requested) ? requested! : buildings[0]?.id ?? "";
if (buildingSelect.value) await loadBuilding(buildingSelect.value).catch(showError);
