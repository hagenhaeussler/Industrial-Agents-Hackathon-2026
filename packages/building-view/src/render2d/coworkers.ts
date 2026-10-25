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
  const target = element("rect", { x: -0.5, y: -1.2, width: 1, height: 1.5, fill: "transparent" });
  const head = element("circle", { cy: -0.95, r: 0.19, fill: "currentColor", stroke: "white", "stroke-width": 0.05 });
  const body = element("path", {
    d: "M-.31 -.34 L-.23 -.68 Q0 -.82 .23 -.68 L.31 -.34 M-.13 -.58 L-.13 -.3 L-.18 0 M.13 -.58 L.13 -.3 L.18 0",
    fill: "none", stroke: "currentColor", "stroke-width": 0.15, "stroke-linecap": "round", "stroke-linejoin": "round",
  });
  const label = element("text", {
    y: 0.42, "text-anchor": "middle", "font-family": "system-ui, sans-serif", "font-size": 0.32,
    "font-weight": 600, fill: "#302e2b", stroke: "white", "stroke-width": 0.08, "paint-order": "stroke",
  });
  node.append(target, head, body, label);
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
