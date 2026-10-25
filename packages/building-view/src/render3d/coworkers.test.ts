// @vitest-environment happy-dom
import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { afterEach, describe, expect, it } from "vitest";

import type { CoworkerMarker, PickResult } from "../overlay";
import { CoworkerMarkers3D } from "./coworkers";

const coworker: CoworkerMarker = { id: "person", name: "Test Person", color: "#397a91", floorId: "F0", x: 2, y: 1 };
const layout = { offsets: new Map([["F0", 0], ["F1", 9]]), focusFloorId: null };
const layers: CoworkerMarkers3D[] = [];

function create(onPick: (pick: PickResult) => void = () => {}): CoworkerMarkers3D {
  const markers = new CoworkerMarkers3D(onPick);
  layers.push(markers);
  markers.update([coworker], layout);
  return markers;
}

function button(markers: CoworkerMarkers3D): HTMLButtonElement {
  for (const marker of markers.group.children) {
    for (const child of marker.children) {
      if (child instanceof CSS2DObject && child.element instanceof HTMLButtonElement) return child.element;
    }
  }
  throw new Error("Expected a coworker label button");
}

function meshes(markers: CoworkerMarkers3D): THREE.Mesh[] {
  const result: THREE.Mesh[] = [];
  markers.group.traverse((object) => {
    if (object instanceof THREE.Mesh) result.push(object);
  });
  return result;
}

afterEach(() => {
  for (const layer of layers.splice(0)) layer.clear();
  document.body.replaceChildren();
});

describe("3D coworker objects", () => {
  it("uses the supplied floor offset and updates positions without replacing meshes", () => {
    const markers = create();
    const before = meshes(markers);
    markers.update([{ ...coworker, x: 4, floorId: "F1" }], layout);
    expect({ position: markers.group.children[0]?.position.toArray(), sameMeshes: meshes(markers).every((mesh, i) => mesh === before[i]) })
      .toEqual({ position: [4, 1, 9], sameMeshes: true });
  });

  it("returns the person from a real geometry raycast", () => {
    const markers = create();
    const ray = new THREE.Raycaster(new THREE.Vector3(2, -3, 1.42), new THREE.Vector3(0, 1, 0));
    expect(markers.pick(ray)).toEqual({ kind: "coworker", ...coworker });
  });

  it("picks a moved person on a new floor before the next render", () => {
    const markers = create();
    const moved = { ...coworker, floorId: "F1", x: 4 };
    markers.update([moved], layout);
    const ray = new THREE.Raycaster(new THREE.Vector3(4, -3, 10.42), new THREE.Vector3(0, 1, 0));
    expect(markers.pick(ray)).toEqual({ kind: "coworker", ...moved });
  });

  it("hides other floors from picking and keyboard access", () => {
    const markers = create();
    markers.update([coworker], { ...layout, focusFloorId: "F1" });
    const ray = new THREE.Raycaster(new THREE.Vector3(2, -3, 1.42), new THREE.Vector3(0, 1, 0));
    expect({ pick: markers.pick(ray), hidden: button(markers).hidden, tabIndex: button(markers).tabIndex })
      .toEqual({ pick: null, hidden: true, tabIndex: -1 });
  });

  it("keeps a named label button with the latest selection data and color", () => {
    const picks: PickResult[] = [];
    const markers = create((pick) => picks.push(pick));
    const label = button(markers);
    const moved = { ...coworker, name: "Renamed Person", x: 4, color: "#b56843" };
    markers.update([moved], layout);
    label.click();
    expect({ label: label.textContent, accessibleName: label.getAttribute("aria-label"), picks })
      .toEqual({ label: moved.name, accessibleName: "Chat with Renamed Person, AI coworker", picks: [{ kind: "coworker", ...moved }] });
  });

  it("disposes geometry, material and button handlers when markers are hidden", () => {
    const picks: PickResult[] = [];
    const markers = create((pick) => picks.push(pick));
    const label = button(markers);
    document.body.append(label);
    const objects = meshes(markers);
    const disposedGeometry: THREE.BufferGeometry[] = [];
    const disposedMaterials = new Set<THREE.Material>();
    for (const mesh of objects) {
      mesh.geometry.addEventListener("dispose", () => disposedGeometry.push(mesh.geometry));
      for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
        material.addEventListener("dispose", () => disposedMaterials.add(material));
      }
    }
    markers.update([], layout);
    label.click();
    expect({ children: markers.group.children.length, labelConnected: label.isConnected, geometries: disposedGeometry.length, materials: disposedMaterials.size, picks })
      .toEqual({ children: 0, labelConnected: false, geometries: objects.length, materials: 1, picks: [] });
  });

  it("rejects positions on floors absent from the building", () => {
    const markers = create();
    markers.update([{ ...coworker, floorId: "missing" }], layout);
    expect(markers.group.children).toHaveLength(0);
  });

  it("can clear a scene and draw it again", () => {
    const markers = create();
    const previous = markers.group.children[0];
    markers.clear();
    markers.update([coworker], layout);
    expect({ count: markers.group.children.length, reused: markers.group.children[0] === previous })
      .toEqual({ count: 1, reused: false });
  });
});
