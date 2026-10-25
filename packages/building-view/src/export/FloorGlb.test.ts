import { afterEach, expect, it, vi } from "vitest";
import { Box3, Matrix4, Quaternion, Vector3 } from "three";
import { compileScene } from "../scene/compile";
import { fixture } from "../testing/fixture";
import { floorGlb } from "./FloorGlb";

afterEach(() => vi.unstubAllGlobals());

it("exports a valid indexed floor lying east/north on Google's Z-up terrain", async () => {
  vi.stubGlobal("FileReader", class {
    result: ArrayBuffer | null = null;
    onloadend: (() => void) | null = null;
    readAsArrayBuffer(blob: Blob) {
      void blob.arrayBuffer().then(bytes => { this.result = bytes; this.onloadend?.(); });
    }
  });
  const floor = compileScene(fixture()).floors[0]!;
  const bytes = await floorGlb(floor, ([x,y]) => [100+x,200+y]);
  const binary = new DataView(bytes);
  expect(binary.getUint32(0,true)).toBe(0x46546c67);
  expect(binary.getUint32(4,true)).toBe(2);
  expect(binary.getUint32(8,true)).toBe(bytes.byteLength);
  const length = binary.getUint32(12,true);
  const gltf = JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,length)));
  expect(gltf.extensionsUsed ?? []).toEqual([]);
  const primitive = gltf.meshes[0].primitives[0];
  expect(primitive.indices).toBeTypeOf("number");
  const accessor = gltf.accessors[primitive.attributes.POSITION];
  const view = gltf.bufferViews[accessor.bufferView];
  const start = 20+length+8+(view.byteOffset ?? 0)+(accessor.byteOffset ?? 0);
  const positions = new Float32Array(bytes,start,accessor.count*3);
  const root = gltf.nodes[gltf.scenes[gltf.scene].nodes[0]];
  const transform = root.matrix ? new Matrix4().fromArray(root.matrix) : new Matrix4().compose(
    new Vector3().fromArray(root.translation ?? [0,0,0]),new Quaternion().fromArray(root.rotation ?? [0,0,0,1]),
    new Vector3().fromArray(root.scale ?? [1,1,1]));
  const bounds = new Box3();
  for (let i=0;i<positions.length;i+=3) bounds.expandByPoint(new Vector3().fromArray(positions,i).applyMatrix4(transform));
  // Independent source footprint: two rooms spanning 8 × 3 m, plus their thin walls.
  expect(bounds.min.x).toBeCloseTo(99.94,3);
  expect(bounds.max.x).toBeCloseTo(108.06,3);
  expect(bounds.min.y).toBeCloseTo(199.94,3);
  expect(bounds.max.y).toBeCloseTo(203.06,3);
  expect(bounds.min.z).toBeCloseTo(0,3);
  expect(bounds.max.z).toBeCloseTo(1.35,3);
});
