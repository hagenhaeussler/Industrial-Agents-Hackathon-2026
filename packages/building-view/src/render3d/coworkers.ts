import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

import { BOT_OUTLINE, BOT_EYE_COLOR } from "../avatar";
import type { CoworkerMarker, PickResult } from "../overlay";

type CoworkerPick = Extract<PickResult, { kind: "coworker" }>;

interface Marker {
  group: THREE.Group;
  material: THREE.MeshLambertMaterial;
  avatar: THREE.Group;
  label: CSS2DObject;
  button: HTMLButtonElement;
  coworker: CoworkerMarker;
  dispose: () => void;
}

/** Owns moving bot avatars and their labels. */
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
      marker.button.setAttribute("aria-label", `Chat with ${coworker.name}, AI coworker`);
    }
  }

  /** Rotate faces toward the camera without changing their size in the building. */
  faceCamera(camera: THREE.PerspectiveCamera): void {
    this.group.updateWorldMatrix(true, true);
    const parentRotation = this.group.getWorldQuaternion(new THREE.Quaternion()).invert();
    const cameraRotation = camera.getWorldQuaternion(new THREE.Quaternion());
    const facing = parentRotation.multiply(cameraRotation);
    const labelOffset = new THREE.Vector3(0, -1.9, 0).applyQuaternion(facing);
    for (const marker of this.markers.values()) {
      marker.avatar.quaternion.copy(facing);
      marker.label.position.copy(marker.avatar.position).add(labelOffset);
    }
  }

  pick(raycaster: THREE.Raycaster): CoworkerPick | null {
    this.group.updateWorldMatrix(true, true);
    const visible = [...this.markers.values()].filter((marker) => marker.group.visible);
    const hit = raycaster.intersectObjects(visible.map((marker) => marker.group), true)[0];
    const marker = hit && visible.find((candidate) => candidate.group === hit.object.parent || candidate.avatar === hit.object.parent);
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
  const avatar = new THREE.Group();
  avatar.position.z = 2;
  group.add(avatar);
  const shape = new THREE.Shape();
  const unit = (value: number) => (value - 32) / 20;
  shape.moveTo(unit(BOT_OUTLINE.start[0]), -unit(BOT_OUTLINE.start[1]));
  for (const curve of BOT_OUTLINE.curves) {
    shape.bezierCurveTo(unit(curve[0]), -unit(curve[1]), unit(curve[2]), -unit(curve[3]), unit(curve[4]), -unit(curve[5]));
  }
  shape.closePath();
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: 0.4, bevelEnabled: true, bevelSize: 0.13, bevelThickness: 0.16, bevelSegments: 5, steps: 1, curveSegments: 20 });
  geometry.translate(0, 0, -0.2);
  avatar.add(new THREE.Mesh(geometry, material));
  const eyes = new THREE.MeshBasicMaterial({ color: BOT_EYE_COLOR });
  for (const x of [-1 / 3, 1 / 3]) {
    const eye = new THREE.Mesh(new THREE.CapsuleGeometry(0.125, 0.375, 4, 12), eyes);
    eye.position.set(x, 0.06, 0.4);
    avatar.add(eye);
  }

  const button = document.createElement("button");
  button.type = "button";
  Object.assign(button.style, {
    pointerEvents: "auto", cursor: "pointer", font: "600 10px system-ui, sans-serif",
    color: "#302e2b", background: "#fff", border: "1px solid #d9d3c7",
    borderRadius: "4px", padding: "2px 5px", whiteSpace: "nowrap",
  });
  const label = new CSS2DObject(button);
  label.position.z = 2;
  group.add(label);

  const marker: Marker = { group, material, avatar, label, button, coworker, dispose };
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
    eyes.dispose();
  }
}
