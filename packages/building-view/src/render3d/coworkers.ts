import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

import type { CoworkerMarker, PickResult } from "../overlay";

type CoworkerPick = Extract<PickResult, { kind: "coworker" }>;

interface Marker {
  group: THREE.Group;
  material: THREE.MeshLambertMaterial;
  button: HTMLButtonElement;
  coworker: CoworkerMarker;
  dispose: () => void;
}

/** Owns only dynamic people and their labels. Building and route objects remain untouched. */
export class CoworkerMarkers3D {
  readonly group = new THREE.Group();
  private readonly markers = new Map<string, Marker>();

  constructor(private readonly onPick: (pick: CoworkerPick) => void) {}

  update(
    coworkers: readonly CoworkerMarker[],
    layout: { offsets: ReadonlyMap<string, number>; focusFloorId: string | null },
  ): void {
    const valid = coworkers.filter((coworker) => layout.offsets.has(coworker.floorId));
    const ids = new Set(valid.map((coworker) => coworker.id));
    for (const [id, marker] of this.markers) {
      if (ids.has(id)) continue;
      marker.dispose();
      this.markers.delete(id);
    }
    for (const coworker of valid) {
      let marker = this.markers.get(coworker.id);
      if (!marker) {
        marker = createMarker(coworker, this.onPick);
        this.markers.set(coworker.id, marker);
        this.group.add(marker.group);
      }
      marker.coworker = coworker;
      marker.material.color.set(coworker.color);
      marker.group.position.set(coworker.x, coworker.y, layout.offsets.get(coworker.floorId)!);
      const visible = layout.focusFloorId === null || layout.focusFloorId === coworker.floorId;
      marker.group.visible = visible;
      marker.button.hidden = !visible;
      marker.button.tabIndex = visible ? 0 : -1;
      marker.button.textContent = coworker.name;
      marker.button.style.borderLeftColor = coworker.color;
      marker.button.setAttribute("aria-label", `Chat with ${coworker.name}, AI coworker`);
    }
  }

  pick(raycaster: THREE.Raycaster): CoworkerPick | null {
    this.group.updateWorldMatrix(true, true);
    const visible = [...this.markers.values()].filter((marker) => marker.group.visible);
    const hit = raycaster.intersectObjects(visible.map((marker) => marker.group), true)[0];
    const marker = hit && visible.find((candidate) => candidate.group === hit.object.parent);
    return marker ? { kind: "coworker", ...marker.coworker } : null;
  }

  clear(): void {
    for (const marker of this.markers.values()) marker.dispose();
    this.markers.clear();
  }
}

function createMarker(coworker: CoworkerMarker, onPick: (pick: CoworkerPick) => void): Marker {
  const group = new THREE.Group();
  const material = new THREE.MeshLambertMaterial({ color: coworker.color });
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 8), material);
  head.position.z = 1.42;
  group.add(head);
  group.add(limb({ radius: 0.22, length: 0.55, x: 0, z: 1.02 }, material));
  for (const side of [-1, 1]) {
    group.add(limb({ radius: 0.08, length: 0.6, x: side * 0.12, z: 0.42 }, material));
    const arm = limb({ radius: 0.065, length: 0.55, x: side * 0.29, z: 0.98 }, material);
    arm.rotation.y = side * 0.15;
    group.add(arm);
  }

  const button = document.createElement("button");
  button.type = "button";
  Object.assign(button.style, {
    pointerEvents: "auto", cursor: "pointer", font: "600 12px system-ui, sans-serif",
    color: "#302e2b", background: "#fff", border: "1px solid #d9d3c7",
    borderLeft: `4px solid ${coworker.color}`, borderRadius: "3px", padding: "4px 7px", whiteSpace: "nowrap",
  });
  const label = new CSS2DObject(button);
  label.position.z = 1.95;
  group.add(label);

  const marker: Marker = { group, material, button, coworker, dispose };
  const select = (event: MouseEvent) => {
    event.stopPropagation();
    if (group.visible && !button.hidden) onPick({ kind: "coworker", ...marker.coworker });
  };
  button.addEventListener("click", select);
  return marker;

  function dispose(): void {
    button.removeEventListener("click", select);
    button.remove();
    group.removeFromParent();
    group.traverse((object) => {
      if (object instanceof THREE.Mesh) object.geometry.dispose();
    });
    material.dispose();
  }
}

function limb(
  shape: { radius: number; length: number; x: number; z: number },
  material: THREE.Material,
): THREE.Mesh {
  const geometry = new THREE.CylinderGeometry(shape.radius, shape.radius, shape.length, 10);
  geometry.rotateX(Math.PI / 2);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(shape.x, 0, shape.z);
  return mesh;
}
