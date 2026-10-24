import { describe, expect, it } from 'bun:test'
import { buildingToXr } from './frames'
import { arrowBearing, orientationDelta } from './OverlayArrow'

describe('marker frame (metres, building +y up)', () => {
  const cases = [
    [0, -2, -4], [90, 4, -2], [180, 2, 4], [270, -4, 2],
  ] as const
  for (const [heading, x, z] of cases) {
    it(`transforms a known point with heading ${heading}°`, () => {
      const result = buildingToXr([14, 22], { point: [10, 20], heading_deg: heading })
      expect(result.x).toBeCloseTo(x, 9)
      expect(result.y).toBe(-1.4)
      expect(result.z).toBeCloseTo(z, 9)
    })
  }
  it('places the marker at the XR origin with a measured floor height', () => {
    expect(buildingToXr([10, 20], { point: [10, 20], heading_deg: 47 }, -1.62)).toEqual({ x: 0, y: -1.62, z: -0 })
  })
  it('rejects invalid geometry before rendering', () => {
    expect(() => buildingToXr([Infinity, 0], { point: [0, 0], heading_deg: 0 })).toThrow(RangeError)
  })
})

describe('direction-only arrow', () => {
  it('points straight ahead, right, and left relative to the marker', () => {
    expect(arrowBearing({ position: [0, 0], headingDeg: 90, deviceAlpha: null, nextWaypoint: [0, 10] })).toBe(0)
    expect(arrowBearing({ position: [0, 0], headingDeg: 90, deviceAlpha: null, nextWaypoint: [10, 0] })).toBe(90)
    expect(arrowBearing({ position: [0, 0], headingDeg: 90, deviceAlpha: null, nextWaypoint: [-10, 0] })).toBe(-90)
  })
  it('uses alpha change since anchoring and wraps through north', () => {
    expect(orientationDelta(5, 355)).toBe(10)
    expect(orientationDelta(355, 5)).toBe(-10)
    expect(arrowBearing({ position: [0, 0], headingDeg: 0, deviceAlpha: 90, nextWaypoint: [0, 10] })).toBe(0)
  })
  it('does not claim a direction when already at the waypoint or data is invalid', () => {
    expect(arrowBearing({ position: [1, 2], headingDeg: 0, deviceAlpha: 0, nextWaypoint: [1, 2] })).toBeNull()
    expect(arrowBearing({ position: [0, 0], headingDeg: NaN, deviceAlpha: 0, nextWaypoint: [1, 2] })).toBeNull()
  })
})
