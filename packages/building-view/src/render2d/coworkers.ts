import { BOT_BODY_PATH, BOT_EYE_COLOR } from "../avatar";
import type { CoworkerMarker, PickResult } from "../overlay";

const SVG = "http://www.w3.org/2000/svg";

interface Marker {
  node: SVGGElement;
  label: SVGTextElement;
  coworker: CoworkerMarker;
}

/** Keeps each person's SVG nodes while their position changes. Events belong to the floor plan. */
export class CoworkerMarkers2D {
  readonly layer = element("g", { "data-layer": "coworkers" });
  private readonly markers = new Map<string, Marker>();

  update(coworkers: readonly CoworkerMarker[], floorId: string): void {
    const visible = coworkers.filter((coworker) => coworker.floorId === floorId);
    const ids = new Set(visible.map((coworker) => coworker.id));
    for (const [id, marker] of this.markers) {
      if (ids.has(id)) continue;
      marker.node.remove();
      this.markers.delete(id);
    }
    for (const coworker of visible) {
      let marker = this.markers.get(coworker.id);
      if (!marker) {
        marker = createMarker(coworker);
        this.markers.set(coworker.id, marker);
        this.layer.append(marker.node);
      }
      marker.coworker = coworker;
      marker.node.setAttribute("transform", `translate(${coworker.x} ${-coworker.y})`);
      marker.node.style.color = coworker.color;
      marker.node.setAttribute("aria-label", `Chat with ${coworker.name}, AI coworker`);
      marker.label.textContent = coworker.name;
    }
  }

  pick(target: EventTarget | null): Extract<PickResult, { kind: "coworker" }> | null {
    const node = target instanceof Element ? target.closest('[data-kind="coworker"]') : null;
    const id = node?.getAttribute("data-id");
    const marker = id ? this.markers.get(id) : undefined;
    return marker && marker.node === node ? { kind: "coworker", ...marker.coworker } : null;
  }

  clear(): void {
    this.layer.replaceChildren();
    this.markers.clear();
  }
}

function createMarker(coworker: CoworkerMarker): Marker {
  const node = element("g", { "data-kind": "coworker", "data-id": coworker.id, role: "button", tabindex: 0 });
  node.style.cursor = "pointer";
  const target = element("rect", { x: -1.5, y: -3.2, width: 3, height: 3.8, fill: "transparent" });
  const face = element("g", { transform: "translate(-1.6 -3.2) scale(.05)" });
  face.append(element("path", { d: BOT_BODY_PATH, fill: "currentColor", stroke: "white", "stroke-width": 2 }));
  for (const x of [21, 37]) face.append(element("rect", { x, y: 23, width: 6, height: 15, rx: 3, fill: BOT_EYE_COLOR }));
  const label = element("text", {
    y: 0.42, "text-anchor": "middle", "font-family": "system-ui, sans-serif", "font-size": 0.32,
    "font-weight": 600, fill: "#302e2b", stroke: "white", "stroke-width": 0.08, "paint-order": "stroke",
  });
  node.append(target, face, label);
  return { node, label, coworker };
}

function element<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attributes: Record<string, string | number>,
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}
