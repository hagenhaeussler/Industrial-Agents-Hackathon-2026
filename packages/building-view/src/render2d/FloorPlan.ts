// A floor plan of one floor as SVG. The building layer is drawn once per floor or option change. Overlays
// (route, position, highlights) live in their own layer, so a moving user only updates a few elements.
import type { Overlay, PickResult } from "../overlay";
import { fitLabel } from "../scene/labels";
import { assetColor, colors, spaceColors } from "../scene/style";
import type { Bounds, BuildingScene, FloorScene, Point } from "../scene/types";

const SVG = "http://www.w3.org/2000/svg";
const WALL_M = 0.12;
const DRAG_PX = 4;

export interface FloorPlanOptions {
  labels: boolean;
  assets: boolean;
  openings: boolean;
  /** Wheel zoom and drag pan. A minimap can turn it off and drive the view with setView. */
  interactive: boolean;
}

/** The visible plan area in metres. y is the plan's y, which points up. */
export interface PlanView {
  x: number;
  y: number;
  width: number;
  height: number;
}

const DEFAULTS: FloorPlanOptions = { labels: true, assets: true, openings: true, interactive: true };

export class FloorPlan {
  readonly svg: SVGSVGElement;
  private readonly building: SVGGElement;
  private readonly overlayLayer: SVGGElement;
  private options: FloorPlanOptions;
  private scene: BuildingScene | undefined;
  private floor: FloorScene | undefined;
  private overlay: Overlay = {};
  private view: PlanView = { x: 0, y: 0, width: 1, height: 1 };
  private readonly pickListeners = new Set<(pick: PickResult | null) => void>();
  private readonly viewListeners = new Set<(view: PlanView) => void>();
  private readonly cleanup: (() => void)[] = [];

  constructor(
    private readonly container: HTMLElement,
    options: Partial<FloorPlanOptions> = {},
  ) {
    this.options = { ...DEFAULTS, ...options };
    this.svg = element("svg", { width: "100%", height: "100%", role: "img" });
    this.svg.style.display = "block";
    this.svg.style.touchAction = "none";
    this.svg.style.userSelect = "none";
    this.building = element("g");
    this.overlayLayer = element("g", { "pointer-events": "none" });
    this.svg.append(this.building, this.overlayLayer);
    container.append(this.svg);
    this.listen();
  }

  /** Draw `floorId` of `scene` and fit it into view. */
  show(scene: BuildingScene, floorId: string): void {
    const floor = scene.floors.find((candidate) => candidate.id === floorId);
    if (!floor) throw new Error(`scene ${scene.id} has no floor ${floorId}`);
    const sameFloor = this.scene?.id === scene.id && this.floor?.id === floorId;
    this.scene = scene;
    this.floor = floor;
    this.svg.setAttribute("aria-label", `${scene.name}, ${floor.name}`);
    this.drawBuilding();
    this.drawOverlay();
    // A live update of the same floor keeps the user's zoom.
    if (!sameFloor) this.fit();
  }

  setOptions(options: Partial<FloorPlanOptions>): void {
    this.options = { ...this.options, ...options };
    this.drawBuilding();
  }

  setOverlay(overlay: Overlay): void {
    this.overlay = overlay;
    this.drawOverlay();
  }

  /** Show the whole floor with a small margin. */
  fit(): void {
    if (!this.floor) return;
    const { minX, minY, maxX, maxY } = this.floor.bounds;
    const margin = Math.max(maxX - minX, maxY - minY) * 0.04 + 0.5;
    this.setView(contain({ minX: minX - margin, minY: minY - margin, maxX: maxX + margin, maxY: maxY + margin }, this.aspect()));
  }

  getView(): PlanView {
    return { ...this.view };
  }

  setView(view: PlanView): void {
    this.view = { ...view };
    // SVG y points down, so the plan's top edge (y + height) becomes the viewBox's top.
    this.svg.setAttribute("viewBox", `${view.x} ${-(view.y + view.height)} ${view.width} ${view.height}`);
    for (const listener of this.viewListeners) listener(this.getView());
  }

  /** Called with the entity under a click, or null for a click on empty plan. Returns an unsubscribe function. */
  onPick(listener: (pick: PickResult | null) => void): () => void {
    this.pickListeners.add(listener);
    return () => this.pickListeners.delete(listener);
  }

  onViewChange(listener: (view: PlanView) => void): () => void {
    this.viewListeners.add(listener);
    return () => this.viewListeners.delete(listener);
  }

  destroy(): void {
    for (const dispose of this.cleanup) dispose();
    this.svg.remove();
  }

  private drawBuilding(): void {
    const floor = this.floor;
    if (!floor) return;
    const spaces = element("g");
    for (const space of floor.spaces) {
      spaces.append(
        element("polygon", {
          points: pointList(space.outline),
          fill: spaceColors[space.type],
          stroke: "rgba(0,0,0,0.12)",
          "stroke-width": 0.03,
          "data-kind": "space",
          "data-id": space.id,
        }),
      );
    }

    const walls = element("path", {
      d: floor.walls.map((wall) => `M${svgPoint(wall.start)}L${svgPoint(wall.end)}`).join(""),
      fill: "none",
      stroke: colors.wall,
      "stroke-width": WALL_M,
      "stroke-linecap": "round",
      "pointer-events": "none",
    });

    const layers: SVGElement[] = [spaces, walls];

    if (this.options.openings) {
      const openings = element("g");
      for (const opening of floor.openings) {
        const color = opening.kind === "entrance" ? colors.entrance : colors.door;
        const attributes = { "data-kind": "opening", "data-id": opening.id };
        if (opening.direction) {
          const [dx, dy] = opening.direction;
          const half = opening.width / 2;
          const [x, y] = opening.position;
          openings.append(
            element("line", {
              ...attributes,
              ...lineEnds([x - dx * half, y - dy * half], [x + dx * half, y + dy * half]),
              stroke: color,
              "stroke-width": opening.kind === "opening" ? 0.03 : 0.08,
              "stroke-dasharray": opening.kind === "opening" ? "0.1 0.1" : "none",
            }),
          );
        } else {
          openings.append(element("circle", { ...attributes, ...circleAt(opening.position), r: 0.15, fill: color }));
        }
      }
      layers.push(openings);
    }

    if (this.options.assets) {
      const assets = element("g");
      for (const asset of floor.assets) {
        assets.append(
          element("polygon", {
            points: pointList(asset.corners),
            fill: assetColor(asset.category),
            stroke: "rgba(0,0,0,0.25)",
            "stroke-width": 0.02,
            "data-kind": "asset",
            "data-id": asset.id,
          }),
        );
      }
      layers.push(assets);
    }

    if (this.options.labels) {
      const labels = element("g", {
        "pointer-events": "none",
        "text-anchor": "middle",
        "dominant-baseline": "central",
        "font-family": "system-ui, sans-serif",
        fill: colors.label,
      });
      for (const space of floor.spaces) {
        const label = fitLabel(space.name, space.ref, space.labelRadius);
        if (!label) continue;
        const text = element("text", { ...textAt(space.labelPoint), "font-size": label.size });
        text.textContent = label.text;
        labels.append(text);
      }
      layers.push(labels);
    }

    this.building.replaceChildren(...layers);
  }

  private drawOverlay(): void {
    const floor = this.floor;
    if (!floor) return;
    const { route = [], position, highlightIds = [], closedIds = [] } = this.overlay;
    const parts: SVGElement[] = [];
    const shapes = new Map<string, readonly Point[]>([
      ...floor.spaces.map((space): [string, readonly Point[]] => [space.id, space.outline]),
      ...floor.assets.map((asset): [string, readonly Point[]] => [asset.id, asset.corners]),
    ]);

    for (const [ids, color] of [[highlightIds, colors.highlight], [closedIds, colors.closed]] as const) {
      for (const id of ids) {
        const outline = shapes.get(id);
        if (outline) parts.push(outlineOf(outline, color));
        const opening = floor.openings.find((candidate) => candidate.id === id);
        if (opening && color === colors.closed) parts.push(closedMark(opening.position));
      }
    }

    // Each run of consecutive route points on this floor is one line. A run's ends at a floor change
    // get a marker, so the reader sees where the route leaves or enters the floor.
    for (const run of floorRuns(route, floor.id)) {
      if (run.points.length > 1) {
        parts.push(
          element("polyline", {
            points: pointList(run.points),
            fill: "none",
            stroke: colors.route,
            "stroke-width": 4,
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
            "vector-effect": "non-scaling-stroke",
          }),
        );
      }
      for (const end of run.floorChanges) {
        parts.push(element("circle", { ...circleAt(end), r: 0.35, fill: "white", stroke: colors.route, "stroke-width": 0.12 }));
      }
    }

    if (position && position.floorId === floor.id) {
      const marker = element("g", { transform: `translate(${position.x} ${-position.y})` });
      if (position.headingDeg !== undefined) {
        // Heading is counterclockwise from +x in the plan, so SVG (y down) turns the other way.
        const wedge = element("path", { d: "M0.25 -0.3 L1 0 L0.25 0.3 Z", fill: colors.position, opacity: 0.5 });
        wedge.setAttribute("transform", `rotate(${-position.headingDeg})`);
        marker.append(wedge);
      }
      marker.append(element("circle", { r: 0.35, fill: colors.position, stroke: "white", "stroke-width": 0.12 }));
      parts.push(marker);
    }

    this.overlayLayer.replaceChildren(...parts);
  }

  private aspect(): number {
    const { width, height } = this.container.getBoundingClientRect();
    return width > 0 && height > 0 ? width / height : 1;
  }

  /** The plan point under a pointer event. The view always matches the container's aspect ratio. */
  private planPoint(event: MouseEvent): Point {
    const rect = this.svg.getBoundingClientRect();
    const fx = rect.width ? (event.clientX - rect.left) / rect.width : 0.5;
    const fy = rect.height ? (event.clientY - rect.top) / rect.height : 0.5;
    return [this.view.x + fx * this.view.width, this.view.y + (1 - fy) * this.view.height];
  }

  private listen(): void {
    const on = <K extends keyof SVGSVGElementEventMap>(type: K, handler: (event: SVGSVGElementEventMap[K]) => void) => {
      this.svg.addEventListener(type, handler);
      this.cleanup.push(() => this.svg.removeEventListener(type, handler));
    };

    let drag: { x: number; y: number; view: PlanView; moved: boolean } | undefined;
    let suppressClick = false;

    on("pointerdown", (event) => {
      if (!this.options.interactive) return;
      drag = { x: event.clientX, y: event.clientY, view: this.getView(), moved: false };
    });
    on("pointermove", (event) => {
      if (!drag) return;
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < DRAG_PX) return;
      if (!drag.moved) this.svg.setPointerCapture?.(event.pointerId);
      drag.moved = true;
      const rect = this.svg.getBoundingClientRect();
      const scale = drag.view.width / (rect.width || 1);
      this.setView({ ...drag.view, x: drag.view.x - dx * scale, y: drag.view.y + dy * scale });
    });
    const endDrag = () => {
      suppressClick = drag?.moved ?? false;
      drag = undefined;
    };
    on("pointerup", endDrag);
    on("pointercancel", endDrag);

    on("wheel", (event) => {
      if (!this.options.interactive) return;
      event.preventDefault();
      const [px, py] = this.planPoint(event);
      const factor = Math.exp(event.deltaY * 0.0015);
      const { x, y, width, height } = this.view;
      this.setView({ x: px - (px - x) * factor, y: py - (py - y) * factor, width: width * factor, height: height * factor });
    });

    on("click", (event) => {
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      const floor = this.floor;
      if (!floor) return;
      const target = event.target instanceof Element ? event.target.closest("[data-id]") : null;
      const kind = target?.getAttribute("data-kind");
      const id = target?.getAttribute("data-id");
      const [x, y] = this.planPoint(event);
      const pick: PickResult | null =
        id && (kind === "space" || kind === "asset" || kind === "opening") ? { kind, id, floorId: floor.id, x, y } : null;
      for (const listener of this.pickListeners) listener(pick);
    });

    if (typeof ResizeObserver !== "undefined") {
      // Keep the view's aspect ratio equal to the container's, around the same centre.
      const observer = new ResizeObserver(() => {
        const { x, y, width, height } = this.view;
        const aspect = this.aspect();
        const centre = [x + width / 2, y + height / 2] as const;
        const size = Math.max(width, height * aspect);
        this.setView({ x: centre[0] - size / 2, y: centre[1] - size / aspect / 2, width: size, height: size / aspect });
      });
      observer.observe(this.container);
      this.cleanup.push(() => observer.disconnect());
    }
  }
}

/** The smallest view with the given aspect ratio that contains `bounds`, centred on it. */
function contain(bounds: Bounds, aspect: number): PlanView {
  const width = Math.max(bounds.maxX - bounds.minX, (bounds.maxY - bounds.minY) * aspect);
  const height = width / aspect;
  return {
    x: (bounds.minX + bounds.maxX) / 2 - width / 2,
    y: (bounds.minY + bounds.maxY) / 2 - height / 2,
    width,
    height,
  };
}

function floorRuns(route: NonNullable<Overlay["route"]>, floorId: string): { points: Point[]; floorChanges: Point[] }[] {
  const runs: { points: Point[]; floorChanges: Point[] }[] = [];
  let current: { points: Point[]; floorChanges: Point[] } | undefined;
  route.forEach((point, index) => {
    if (point.floorId !== floorId) {
      if (current) current.floorChanges.push(current.points.at(-1)!);
      current = undefined;
      return;
    }
    const here: Point = [point.x, point.y];
    if (!current) {
      current = { points: [], floorChanges: index > 0 ? [here] : [] };
      runs.push(current);
    }
    current.points.push(here);
  });
  return runs;
}

function outlineOf(outline: readonly Point[], color: string): SVGElement {
  return element("polygon", {
    points: pointList(outline),
    fill: color,
    "fill-opacity": 0.18,
    stroke: color,
    "stroke-width": 3,
    "vector-effect": "non-scaling-stroke",
  });
}

function closedMark([x, y]: Point): SVGElement {
  const size = 0.4;
  return element("path", {
    d: `M${svgPoint([x - size, y - size])}L${svgPoint([x + size, y + size])}M${svgPoint([x - size, y + size])}L${svgPoint([x + size, y - size])}`,
    stroke: colors.closed,
    "stroke-width": 0.15,
    "stroke-linecap": "round",
  });
}

// SVG's y axis points down. These helpers flip the plan's y once, so all drawing code uses plan points.
function svgPoint([x, y]: Point): string {
  return `${x} ${-y}`;
}

function pointList(points: readonly Point[]): string {
  return points.map(([x, y]) => `${x},${-y}`).join(" ");
}

function lineEnds([x1, y1]: Point, [x2, y2]: Point) {
  return { x1, y1: -y1, x2, y2: -y2 };
}

function circleAt([x, y]: Point) {
  return { cx: x, cy: -y };
}

function textAt([x, y]: Point) {
  return { x, y: -y };
}

function element<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attributes: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}
