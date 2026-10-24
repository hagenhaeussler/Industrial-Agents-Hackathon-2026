/** CONTRACTS C1 §11: marker-relative building coordinates to XR local metres. */
export type Point2 = readonly [number, number]
export type MarkerFrame = { point: Point2; heading_deg: number }
export type XrPoint = { x: number; y: number; z: number }

export const DEFAULT_FLOOR_Y = -1.4

function finite(...values: number[]): void {
  if (values.some(value => !Number.isFinite(value))) throw new RangeError('Frame coordinates must be finite numbers.')
}

/** Stand on the marker footprint facing its heading before creating the XR local space. */
export function buildingToXr(point: Point2, marker: MarkerFrame, floorY = DEFAULT_FLOOR_Y): XrPoint {
  finite(...point, ...marker.point, marker.heading_deg, floorY)
  const theta = marker.heading_deg * Math.PI / 180
  const dx = point[0] - marker.point[0]
  const dy = point[1] - marker.point[1]
  const forward = dx * Math.cos(theta) + dy * Math.sin(theta)
  const right = dx * Math.sin(theta) - dy * Math.cos(theta)
  return { x: right, y: floorY, z: -forward }
}
