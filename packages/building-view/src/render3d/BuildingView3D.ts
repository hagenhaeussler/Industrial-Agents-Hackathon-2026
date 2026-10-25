// The whole building in 3D as an exploded view: floors float apart, walls are cut to a low height so rooms
// and assets stay visible, and the camera orbits freely. It renders only when something changes.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

import type { Overlay, PickResult } from "../overlay";
import { fitLabel } from "../scene/labels";
import { assetColor, colors, spaceColors } from "../scene/style";
import type { BuildingScene, FloorScene, Point } from "../scene/types";
import { placeLabels, type LabelCandidate } from "./labelPlacement";
import { assetHeight, floorOffsets } from "./layout";
import { CoworkerMarkers3D } from "./coworkers";

const SLAB_M = 0.12;
const WALL_M = 0.12;
const GHOST_COLOR = "#8f8a80";
const LABEL_FONT_PX = 11;

export interface BuildingView3DOptions {
  /** Extra metres between floors, on top of their real elevation difference. */
  floorGap: number;
  /** Wall height in metres, or "full" for each floor's height. */
  wallHeight: number | "full";
  labels: boolean;
  assets: boolean;
}

const DEFAULTS: BuildingView3DOptions = { floorGap: 6, wallHeight: 1.2, labels: true, assets: true };

interface FloorObjects {
  floor: FloorScene;
  group: THREE.Group;
  /** The full floor: slabs, walls, entrances, assets and labels. */
  detail: THREE.Group;
  /** A flat outline shown instead of the detail while another floor has focus. */
  ghost: THREE.Group;
  walls: THREE.Mesh;
  assets: THREE.InstancedMesh | undefined;
  labels: THREE.Group;
  pickables: THREE.Object3D[];
}

export class BuildingView3D {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly labelRenderer: CSS2DRenderer;
  private readonly world = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(40, 1, 0.1, 10000);
  private readonly controls: OrbitControls;
  /** Holds everything in plan coordinates: x right, y up the plan, z up. */
  private readonly plan = new THREE.Group();
  private readonly connectorGroup = new THREE.Group();
  private readonly overlayGroup = new THREE.Group();
  private readonly coworkers = new CoworkerMarkers3D((pick) => {
    for (const listener of this.pickListeners) listener(pick);
  });
  private overlayKey = "";
  private options: BuildingView3DOptions;
  private scene: BuildingScene | undefined;
  private floors: FloorObjects[] = [];
  private focusFloorId: string | null = null;
  private overlay: Overlay = {};
  private frame: number | undefined;
  private destroyed = false;
  private readonly connectorMaterials = {
    stairs: new THREE.MeshLambertMaterial({ color: "#d9a441" }),
    lift: new THREE.MeshLambertMaterial({ color: "#5b8fd6" }),
  };
  private readonly pickListeners = new Set<(pick: PickResult | null) => void>();
  private readonly cleanup: (() => void)[] = [];

  constructor(
    private readonly container: HTMLElement,
    options: Partial<BuildingView3DOptions> = {},
  ) {
    this.options = { ...DEFAULTS, ...options };
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.domElement.style.display = "block";
    this.labelRenderer = new CSS2DRenderer();
    Object.assign(this.labelRenderer.domElement.style, { position: "absolute", inset: "0", pointerEvents: "none" });
    if (getComputedStyle(container).position === "static") container.style.position = "relative";
    container.append(this.renderer.domElement, this.labelRenderer.domElement);

    this.world.background = new THREE.Color("#f6f5f2");
    this.world.add(new THREE.HemisphereLight("#ffffff", "#b8b2a7", 2.2));
    const sun = new THREE.DirectionalLight("#ffffff", 1.4);
    sun.position.set(-0.6, 1, 0.4);
    this.world.add(sun);
    this.plan.rotation.x = -Math.PI / 2;
    this.plan.add(this.connectorGroup, this.overlayGroup, this.coworkers.group);
    this.world.add(this.plan);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    // Zoom toward the pointer, so an off-centre part of the building can be reached without moving the centre
    // first. Panning moves in the screen plane, and the camera never goes below the ground.
    this.controls.zoomToCursor = true;
    this.controls.screenSpacePanning = true;
    this.controls.maxPolarAngle = Math.PI * 0.495;
    this.renderer.domElement.tabIndex = 0;
    this.controls.listenToKeyEvents(this.renderer.domElement);
    this.controls.addEventListener("change", () => this.requestRender());
    this.listen();
    this.resize();
  }

  /** Build the view for `scene`. Keeps the camera if the same building is shown again. */
  show(scene: BuildingScene): void {
    const sameBuilding = this.scene?.id === scene.id;
    this.coworkers.clear();
    if (this.scene && !sameBuilding) this.overlay = { ...this.overlay, coworkers: [] };
    this.scene = scene;
    for (const objects of this.floors) {
      this.plan.remove(objects.group);
      dispose(objects.group);
    }
    this.floors = scene.floors.map((floor) => this.buildFloor(floor));
    for (const objects of this.floors) this.plan.add(objects.group);
    if (this.focusFloorId && !scene.floors.some((floor) => floor.id === this.focusFloorId)) this.focusFloorId = null;
    this.layout();
    if (!sameBuilding) this.resetCamera();
  }

  setOptions(options: Partial<BuildingView3DOptions>): void {
    const previous = this.options;
    this.options = { ...previous, ...options };
    if (options.wallHeight !== undefined && options.wallHeight !== previous.wallHeight) {
      for (const objects of this.floors) {
        objects.walls.geometry.dispose();
        objects.walls.geometry = wallGeometry(objects.floor, this.wallHeight(objects.floor));
      }
    }
    this.layout();
  }

  /** Show one floor in full and the others as flat outlines, or all floors in full with null. */
  setFocusFloor(floorId: string | null): void {
    this.focusFloorId = floorId;
    this.layout();
  }

  setOverlay(overlay: Overlay): void {
    this.overlay = overlay;
    const key = JSON.stringify([overlay.route, overlay.position, overlay.highlightIds, overlay.closedIds]);
    if (key !== this.overlayKey) {
      this.overlayKey = key;
      this.drawOverlay();
    }
    this.drawCoworkers();
    this.requestRender();
  }

  onPick(listener: (pick: PickResult | null) => void): () => void {
    this.pickListeners.add(listener);
    return () => this.pickListeners.delete(listener);
  }

  /** Look at the whole building from the south-east, slightly from above. */
  resetCamera(): void {
    const box = new THREE.Box3().setFromObject(this.plan);
    if (box.isEmpty()) return;
    const centre = box.getCenter(new THREE.Vector3());
    const radius = box.getSize(new THREE.Vector3()).length() / 2;
    const distance = radius / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2));
    this.camera.position.copy(centre).add(new THREE.Vector3(0.55, 0.6, 0.6).normalize().multiplyScalar(distance));
    this.camera.near = distance / 100;
    this.camera.far = distance * 10;
    this.camera.updateProjectionMatrix();
    this.controls.target.copy(centre);
    this.controls.update();
    this.requestRender();
  }

  /** Turn around a point of a floor from now on, keeping the current viewing angle and distance. */
  centerOn(floorId: string, x: number, y: number): void {
    const objects = this.floors.find((candidate) => candidate.floor.id === floorId);
    if (!objects) return;
    this.plan.updateMatrixWorld(true);
    this.orbitAround(objects.group.localToWorld(new THREE.Vector3(x, y, 0)));
  }

  destroy(): void {
    this.destroyed = true;
    if (this.frame !== undefined) cancelAnimationFrame(this.frame);
    for (const dispose of this.cleanup) dispose();
    this.controls.dispose();
    this.coworkers.clear();
    this.pickListeners.clear();
    dispose(this.plan);
    for (const material of Object.values(this.connectorMaterials)) material.dispose();
    this.renderer.dispose();
    // Browsers allow only a few live WebGL contexts. Free this one now instead of at garbage collection.
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
    this.labelRenderer.domElement.remove();
  }

  private wallHeight(floor: FloorScene): number {
    return this.options.wallHeight === "full" ? floor.height : Math.min(this.options.wallHeight, floor.height);
  }

  private buildFloor(floor: FloorScene): FloorObjects {
    const group = new THREE.Group();
    group.name = floor.id;
    const detail = new THREE.Group();
    const material = (color: string) => new THREE.MeshLambertMaterial({ color });
    const pickables: THREE.Object3D[] = [];

    // Spaces are thin slabs, one mesh each, so a click can name the space.
    const spaceMaterials = new Map<string, THREE.Material>();
    for (const space of floor.spaces) {
      const color = spaceColors[space.type];
      if (!spaceMaterials.has(color)) spaceMaterials.set(color, material(color));
      const geometry = new THREE.ExtrudeGeometry(shapeOf(space.outline), { depth: SLAB_M, bevelEnabled: false });
      geometry.translate(0, 0, -SLAB_M);
      const mesh = new THREE.Mesh(geometry, spaceMaterials.get(color));
      mesh.userData = { kind: "space", id: space.id };
      detail.add(mesh);
      pickables.push(mesh);
    }

    const walls = new THREE.Mesh(wallGeometry(floor, this.wallHeight(floor)), material("#d9d3c7"));
    detail.add(walls);

    const entrances = floor.openings.filter((opening) => opening.kind === "entrance");
    if (entrances.length > 0) {
      const entranceMaterial = material(colors.entrance);
      for (const entrance of entrances) {
        const mark = new THREE.Mesh(new THREE.BoxGeometry(entrance.width, 0.3, 0.05), entranceMaterial);
        mark.position.set(entrance.position[0], entrance.position[1], 0.03);
        if (entrance.direction) mark.rotation.z = Math.atan2(entrance.direction[1], entrance.direction[0]);
        detail.add(mark);
      }
    }

    let assets: THREE.InstancedMesh | undefined;
    if (floor.assets.length > 0) {
      const unit = new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5);
      assets = new THREE.InstancedMesh(unit, material("#ffffff"), floor.assets.length);
      const matrix = new THREE.Matrix4();
      const turn = new THREE.Quaternion();
      const zAxis = new THREE.Vector3(0, 0, 1);
      floor.assets.forEach((asset, index) => {
        turn.setFromAxisAngle(zAxis, THREE.MathUtils.degToRad(asset.rotationDeg));
        matrix.compose(
          new THREE.Vector3(asset.position[0], asset.position[1], 0),
          turn,
          new THREE.Vector3(asset.width, asset.depth, assetHeight(asset.category)),
        );
        assets!.setMatrixAt(index, matrix);
        assets!.setColorAt(index, new THREE.Color(assetColor(asset.category)));
      });
      assets.userData = { kind: "asset", ids: floor.assets.map((asset) => asset.id) };
      detail.add(assets);
      pickables.push(assets);
    }

    const labels = new THREE.Group();
    for (const space of floor.spaces) {
      const label = fitLabel(space.name, space.ref, space.labelRadius);
      if (!label) continue;
      const node = document.createElement("div");
      node.textContent = label.text;
      Object.assign(node.style, {
        font: `500 ${LABEL_FONT_PX}px system-ui, sans-serif`,
        color: colors.label,
        textShadow: "0 0 3px #fff, 0 0 3px #fff",
        whiteSpace: "nowrap",
      });
      const object = new CSS2DObject(node);
      object.position.set(space.labelPoint[0], space.labelPoint[1], 0.2);
      // Larger rooms win when labels collide. The width is an estimate, so placement needs no DOM layout.
      object.userData = { key: space.id, priority: space.labelRadius, width: label.text.length * LABEL_FONT_PX * 0.58 + 6 };
      labels.add(object);
    }
    detail.add(labels);

    const ghost = ghostOf(floor);
    group.add(detail, ghost);
    return { floor, group, detail, ghost, walls, assets, labels, pickables };
  }

  /** Apply floor offsets, focus, visibility and connectors. Cheap: no geometry is rebuilt. */
  private layout(): void {
    if (!this.scene) return;
    const offsets = floorOffsets(this.scene.floors, this.options.floorGap);
    for (const objects of this.floors) {
      const { floor, group } = objects;
      group.position.z = offsets.get(floor.id)!;
      const faded = this.focusFloorId !== null && this.focusFloorId !== floor.id;
      objects.detail.visible = !faded;
      objects.ghost.visible = faded;
      if (objects.assets) objects.assets.visible = this.options.assets;
      const focused = this.focusFloorId === floor.id;
      objects.labels.visible = this.options.labels && (focused || this.focusFloorId === null);
    }
    this.drawConnectors(offsets);
    this.drawOverlay();
    this.drawCoworkers();
    this.requestRender();
  }

  private drawCoworkers(): void {
    this.coworkers.update(this.overlay.coworkers ?? [], {
      offsets: this.scene ? floorOffsets(this.scene.floors, this.options.floorGap) : new Map(),
      focusFloorId: this.focusFloorId,
    });
  }

  /** Stairs and lifts as columns between the stop points of consecutive stops. */
  private drawConnectors(offsets: Map<string, number>): void {
    clear(this.connectorGroup, { keepMaterials: true });
    if (!this.scene) return;
    for (const connector of this.scene.connectors) {
      connector.stops.slice(1).forEach((stop, index) => {
        const previous = connector.stops[index]!;
        const from = new THREE.Vector3(previous.point[0], previous.point[1], offsets.get(previous.floorId)!);
        const to = new THREE.Vector3(stop.point[0], stop.point[1], offsets.get(stop.floorId)!);
        this.connectorGroup.add(column(from, to, connector.kind === "lift" ? 0.25 : 0.15, this.connectorMaterials[connector.kind]));
      });
    }
  }

  private drawOverlay(): void {
    clear(this.overlayGroup);
    if (!this.scene) return;
    const offsets = floorOffsets(this.scene.floors, this.options.floorGap);
    const lift = 0.35;
    const { position, highlightIds = [], closedIds = [] } = this.overlay;
    // Points on floors this building does not have are skipped, like in the floor plan.
    const route = (this.overlay.route ?? []).filter((point) => offsets.has(point.floorId));

    if (route.length > 1) {
      const geometry = new LineGeometry();
      geometry.setPositions(route.flatMap((point) => [point.x, point.y, offsets.get(point.floorId)! + lift]));
      // The route is drawn over walls and floors: it matters most when someone follows it.
      const material = new LineMaterial({ color: colors.route, linewidth: 5, worldUnits: false, depthTest: false });
      material.resolution.set(this.container.clientWidth, this.container.clientHeight);
      const line = new Line2(geometry, material);
      line.renderOrder = 1;
      this.overlayGroup.add(line);
    }

    const marked = [
      ...highlightIds.map((id) => [id, colors.highlight] as const),
      ...closedIds.map((id) => [id, colors.closed] as const),
    ];
    for (const [id, color] of marked) {
      for (const { floor } of this.floors) {
        const space = floor.spaces.find((candidate) => candidate.id === id);
        const asset = floor.assets.find((candidate) => candidate.id === id);
        const outline = space?.outline ?? asset?.corners;
        if (!outline) continue;
        const mesh = new THREE.Mesh(
          new THREE.ShapeGeometry(shapeOf(outline)),
          new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.45, depthWrite: false }),
        );
        mesh.position.z = offsets.get(floor.id)! + (asset ? assetHeight(asset.category) + 0.02 : 0.02);
        this.overlayGroup.add(mesh);
      }
    }

    if (position && offsets.has(position.floorId)) {
      const marker = new THREE.Group();
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.45, 24, 16), new THREE.MeshLambertMaterial({ color: colors.position }));
      dot.position.z = 0.6;
      marker.add(dot);
      if (position.headingDeg !== undefined) {
        const cone = new THREE.Mesh(new THREE.ConeGeometry(0.3, 0.9, 16), new THREE.MeshLambertMaterial({ color: colors.position }));
        // The cone points along +y; turn it so it points along the heading (counterclockwise from +x).
        cone.rotation.z = THREE.MathUtils.degToRad(position.headingDeg - 90);
        cone.position.set(Math.cos(THREE.MathUtils.degToRad(position.headingDeg)) * 0.9, Math.sin(THREE.MathUtils.degToRad(position.headingDeg)) * 0.9, 0.6);
        marker.add(cone);
      }
      marker.position.set(position.x, position.y, offsets.get(position.floorId)!);
      this.overlayGroup.add(marker);
    }
  }

  private requestRender(): void {
    if (this.frame !== undefined || this.destroyed) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = undefined;
      this.renderer.render(this.world, this.camera);
      this.declutterLabels();
      this.labelRenderer.render(this.world, this.camera);
    });
  }

  /** Hide labels that would overlap a more important one at the current camera position. */
  private declutterLabels(): void {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    const candidates: LabelCandidate[] = [];
    const objects = new Map<string, THREE.Object3D>();
    const point = new THREE.Vector3();
    for (const floor of this.floors) {
      if (!floor.labels.visible) continue;
      for (const label of floor.labels.children) {
        const data = label.userData as { key: string; priority: number; width: number };
        label.getWorldPosition(point).project(this.camera);
        label.visible = false;
        if (point.z < -1 || point.z > 1) continue;
        objects.set(data.key, label);
        candidates.push({
          key: data.key,
          x: ((point.x + 1) / 2) * width,
          y: ((1 - point.y) / 2) * height,
          width: data.width,
          height: LABEL_FONT_PX + 4,
          priority: data.priority,
        });
      }
    }
    for (const key of placeLabels(candidates, { width, height })) objects.get(key)!.visible = true;
  }

  private resize(): void {
    const width = this.container.clientWidth || 1;
    const height = this.container.clientHeight || 1;
    this.renderer.setSize(width, height);
    this.labelRenderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.overlayGroup.traverse((object) => {
      if (object instanceof Line2) object.material.resolution.set(width, height);
    });
    this.requestRender();
  }

  private orbitAround(point: THREE.Vector3): void {
    this.camera.position.add(point.clone().sub(this.controls.target));
    this.controls.target.copy(point);
    this.controls.update();
    this.requestRender();
  }

  private pick(event: MouseEvent): PickResult | null {
    const rect = this.renderer.domElement.getBoundingClientRect();
    const pointer = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(pointer, this.camera);
    const coworker = this.coworkers.pick(raycaster);
    if (coworker) {
      if (event.type === "dblclick") {
        const offset = this.floors.find((objects) => objects.floor.id === coworker.floorId)?.group.position.z ?? 0;
        this.orbitAround(this.plan.localToWorld(new THREE.Vector3(coworker.x, coworker.y, offset)));
      }
      return coworker;
    }
    // With a focused floor only that floor is clickable; faded floors would otherwise catch clicks.
    const candidates = this.floors.filter((objects) => this.focusFloorId === null || objects.floor.id === this.focusFloorId);
    const hit = raycaster.intersectObjects(candidates.flatMap((objects) => objects.pickables.filter((o) => o.visible)), false)[0];
    if (!hit) return null;
    if (event.type === "dblclick") this.orbitAround(hit.point);
    const floor = this.floors.find((objects) => objects.detail === hit.object.parent)!.floor;
    const local = this.plan.worldToLocal(hit.point.clone());
    const data = hit.object.userData as { kind: "space" | "asset"; id?: string; ids?: string[] };
    const id = data.kind === "asset" ? data.ids![hit.instanceId!]! : data.id!;
    return { kind: data.kind, id, floorId: floor.id, x: local.x, y: local.y };
  }

  private listen(): void {
    const canvas = this.renderer.domElement;
    let down: { x: number; y: number } | undefined;
    const onDown = (event: PointerEvent) => (down = { x: event.clientX, y: event.clientY });
    const onUp = (event: PointerEvent) => {
      if (!down || Math.hypot(event.clientX - down.x, event.clientY - down.y) > 4) return;
      down = undefined;
      const pick = this.pick(event);
      for (const listener of this.pickListeners) listener(pick);
    };
    // A double click makes the point under the pointer the new centre to turn around.
    const onDoubleClick = (event: MouseEvent) => void this.pick(event);
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("dblclick", onDoubleClick);
    const observer = new ResizeObserver(() => this.resize());
    observer.observe(this.container);
    this.cleanup.push(() => {
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("dblclick", onDoubleClick);
      observer.disconnect();
    });
  }
}

/**
 * A floor seen through: one flat, translucent layer of all spaces plus the walls as lines. Transparent 3D
 * walls would stack where floors share a layout and look half solid, so the ghost has no height.
 */
function ghostOf(floor: FloorScene): THREE.Group {
  const ghost = new THREE.Group();
  ghost.visible = false;
  const shapes = floor.spaces.map((space) => new THREE.ShapeGeometry(shapeOf(space.outline)));
  if (shapes.length > 0) {
    const area = new THREE.Mesh(
      mergeGeometries(shapes),
      new THREE.MeshBasicMaterial({ color: GHOST_COLOR, transparent: true, opacity: 0.1, depthWrite: false }),
    );
    ghost.add(area);
  }
  for (const shape of shapes) shape.dispose();
  const lines = new THREE.BufferGeometry().setFromPoints(
    floor.walls.flatMap((wall) => [new THREE.Vector3(...wall.start, 0), new THREE.Vector3(...wall.end, 0)]),
  );
  ghost.add(
    new THREE.LineSegments(
      lines,
      new THREE.LineBasicMaterial({ color: GHOST_COLOR, transparent: true, opacity: 0.45, depthWrite: false }),
    ),
  );
  return ghost;
}

function shapeOf(outline: readonly Point[]): THREE.Shape {
  return new THREE.Shape(outline.map(([x, y]) => new THREE.Vector2(x, y)));
}

/** All walls of a floor merged into one geometry, so a floor costs one draw call for its walls. */
function wallGeometry(floor: FloorScene, height: number): THREE.BufferGeometry {
  const boxes = floor.walls.map((wall) => {
    const dx = wall.end[0] - wall.start[0];
    const dy = wall.end[1] - wall.start[1];
    const box = new THREE.BoxGeometry(Math.hypot(dx, dy) + WALL_M, WALL_M, height);
    box.rotateZ(Math.atan2(dy, dx));
    box.translate((wall.start[0] + wall.end[0]) / 2, (wall.start[1] + wall.end[1]) / 2, height / 2);
    return box;
  });
  const merged = boxes.length > 0 ? mergeGeometries(boxes) : new THREE.BufferGeometry();
  for (const box of boxes) box.dispose();
  return merged;
}

function column(from: THREE.Vector3, to: THREE.Vector3, radius: number, material: THREE.Material): THREE.Mesh {
  const direction = to.clone().sub(from);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, direction.length(), 12), material);
  mesh.position.copy(from).add(direction.clone().multiplyScalar(0.5));
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  return mesh;
}

function clear(group: THREE.Group, options: { keepMaterials?: boolean } = {}): void {
  for (const child of [...group.children]) {
    group.remove(child);
    dispose(child, options);
  }
}

function dispose(root: THREE.Object3D, { keepMaterials = false }: { keepMaterials?: boolean } = {}): void {
  root.traverse((object) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments || object instanceof Line2) {
      object.geometry.dispose();
      if (keepMaterials) return;
      const materials: THREE.Material[] = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materials) material.dispose();
    }
    if (object instanceof CSS2DObject) object.element.remove();
  });
}
