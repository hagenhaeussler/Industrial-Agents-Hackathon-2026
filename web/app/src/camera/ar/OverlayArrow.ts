import type { Point2 } from './frames'

export type ArrowOptions = {
  position: Point2
  headingDeg: number
  /** Alpha change since the marker scan, not a compass heading. Null means no motion permission. */
  deviceAlpha: number | null
  nextWaypoint: Point2
}

/** CSS clockwise degrees from straight ahead; direction only, no position tracking. */
export function arrowBearing({ position, headingDeg, deviceAlpha, nextWaypoint }: ArrowOptions): number | null {
  if ([...position, headingDeg, ...nextWaypoint].some(value => !Number.isFinite(value))) return null
  if (deviceAlpha !== null && !Number.isFinite(deviceAlpha)) return null
  const dx = nextWaypoint[0] - position[0]
  const dy = nextWaypoint[1] - position[1]
  if (Math.hypot(dx, dy) < 1e-6) return null
  const targetHeading = Math.atan2(dy, dx) * 180 / Math.PI
  const heading = headingDeg + (deviceAlpha ?? 0)
  return normalizeDegrees(heading - targetHeading)
}

/** Relative alpha in [-180, 180); pass this to arrowBearing after anchoring. */
export function orientationDelta(alpha: number, alphaAtMarker: number): number {
  return normalizeDegrees(alpha - alphaAtMarker)
}

export function normalizeDegrees(degrees: number): number {
  return ((degrees + 180) % 360 + 360) % 360 - 180
}
