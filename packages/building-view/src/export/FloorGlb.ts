import { BoxGeometry, Color, DoubleSide, ExtrudeGeometry, Float32BufferAttribute, Group, Mesh, MeshStandardMaterial, Shape,
  type BufferGeometry } from "three";
import { mergeGeometries, mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { assetColor, spaceColors } from "../scene/style";
import { assetHeight } from "../render3d/layout";
import type { FloorScene, Point } from "../scene/types";

/** Export exactly the compiled floor geometry. Project returns local east/north metres at the map anchor. */
export async function floorGlb(floor: FloorScene, project: (point: Point) => readonly [number, number],
  options: {spaceColor?:string;lift?:number} = {}): Promise<ArrayBuffer> {
  const parts: BufferGeometry[] = [];
  const add = (geometry: BufferGeometry, color: string) => {
    let piece = geometry;
    if (piece.index) { piece = piece.toNonIndexed(); geometry.dispose(); }
    const positions = piece.getAttribute("position");
    // The input is plan x/y with z vertical. glTF is Y-up: east, up, south.
    for (let i = 0; i < positions.count; i++) {
      const [east, north] = project([positions.getX(i), positions.getY(i)]);
      const up = positions.getZ(i)+(options.lift ?? 0);
      positions.setXYZ(i, east, up, -north);
    }
    piece.computeVertexNormals();
    const rgb = new Color(color), colors = new Float32Array(positions.count * 3);
    for (let i = 0; i < positions.count; i++) rgb.toArray(colors, i * 3);
    piece.setAttribute("color", new Float32BufferAttribute(colors, 3));
    piece.deleteAttribute("uv");
    parts.push(piece);
  };
  for (const space of floor.spaces) {
    if (space.outline.length < 3) continue;
    const shape = new Shape();
    shape.moveTo(space.outline[0]![0], space.outline[0]![1]);
    for (const [x,y] of space.outline.slice(1)) shape.lineTo(x,y);
    shape.closePath();
    add(new ExtrudeGeometry(shape, { depth: .15, bevelEnabled: false }), options.spaceColor ?? spaceColors[space.type]);
  }
  for (const wall of floor.walls) {
    const [x,y] = wall.start, dx = wall.end[0] - x, dy = wall.end[1] - y;
    const length = Math.hypot(dx,dy);
    if (length < .01) continue;
    const h = Math.min(floor.height, 1.2);
    const geometry = new BoxGeometry(length,.12,h);
    geometry.rotateZ(Math.atan2(dy,dx)); geometry.translate(x+dx/2,y+dy/2,.15+h/2);
    add(geometry,"#ddd8cb");
  }
  for (const asset of floor.assets) {
    const h = assetHeight(asset.category);
    const geometry = new BoxGeometry(asset.width,asset.depth,h);
    geometry.rotateZ(asset.rotationDeg*Math.PI/180);
    geometry.translate(asset.position[0],asset.position[1],.15+h/2);
    add(geometry,assetColor(asset.category));
  }
  if (!parts.length) throw new Error("Cannot export an empty floor");
  const merged = mergeGeometries(parts);
  for (const part of parts) part.dispose();
  if (!merged) throw new Error("Floor mesh could not be merged");
  const indexed = mergeVertices(merged, .00001); merged.dispose();
  const material = new MeshStandardMaterial({vertexColors:true,metalness:0,roughness:1,side:DoubleSide});
  const group = new Group(); group.name = floor.id;
  // Google Maps places model coordinates in east/north/up (Z-up). Convert the
  // standard glTF Y-up mesh at the root, so its plan lies on Google's terrain.
  group.rotation.x = Math.PI / 2;
  group.add(new Mesh(indexed,material));
  try {
    const result = await new GLTFExporter().parseAsync(group,{binary:true,onlyVisible:true});
    if (!(result instanceof ArrayBuffer)) throw new Error("Expected a binary glTF model");
    return result;
  } finally { indexed.dispose(); material.dispose(); }
}
