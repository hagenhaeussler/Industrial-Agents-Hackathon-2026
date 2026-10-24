import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { Window } from 'happy-dom'
import type { ReachableRoute, Segment } from '../../api/types'
import { routeRibbon, startAr } from './ArSession'
import type { ArMarker, ArOptions, ArRuntime } from './ArSession'

const marker: ArMarker = { building_id: 'test-building', floor_id: 'ground', point: [10, 20], heading_deg: 0 }
const walk = (points: [number, number][], floor_id = 'ground'): Segment => ({ kind: 'walk', floor_id, space_id: 'hall', points, length_m: 10 })
const route = (segments: Segment[]): ReachableRoute => ({
  reachable: true, from_space_id: 'hall', to_space_id: 'room', length_m: 10,
  space_path: [], element_path: [], node_path: [], maneuvers: [], segments,
  constraints: { step_free: false, min_door_width_m: 0, closed: [], no_transit_room_types: [] },
  profile: 'kit_1_1_0', building_id: marker.building_id, building_version: 0, content_hash: 'test',
})

describe('exact current-floor route ribbon', () => {
  test('is a flat 16cm ribbon 2cm above the camera-relative floor', () => {
    const vertices = routeRibbon(route([walk([[10, 20], [20, 20]])]), marker)
    expect(vertices.length).toBe(18)
    for (let i = 0; i < vertices.length; i += 3) {
      expect(Math.abs(vertices[i]!)).toBeCloseTo(0.08)
      expect(vertices[i + 1]).toBeCloseTo(-1.38)
      expect([0, -10]).toContain(vertices[i + 2]!)
    }
  })
  test('stops at the first vertical connector, including a return to the same floor', () => {
    const first = walk([[10, 20], [20, 20]])
    const vertical: Segment = { kind: 'lift', floor_id: 'ground', to_floor_id: 'up', element_id: 'lift', points: [[20, 20], [20, 20]], length_m: 4 }
    expect(routeRibbon(route([first, vertical, walk([[20, 20], [30, 20]]), walk([[30, 20], [40, 20]], 'up')]), marker))
      .toEqual(routeRibbon(route([first]), marker))
  })
  test('never connects discontinuous supplied walk segments', () => {
    const vertices = routeRibbon(route([walk([[10, 20], [11, 20]]), walk([[19, 20], [20, 20]])]), marker)
    const distances = vertices.filter((_value, index) => index % 3 === 2)
    expect(distances.every(value => [0, -1, -9, -10].includes(value))).toBe(true)
    expect(vertices.length).toBe(36)
  })
  test('refuses provisional, other-building, wrong-floor and nonfinite paths', () => {
    const current = route([walk([[10, 20], [20, 20]])])
    expect(() => routeRibbon({ ...current, geometry: 'provisional' }, marker)).toThrow('computed route')
    expect(() => routeRibbon({ ...current, building_id: 'other' }, marker)).toThrow('this building')
    expect(() => routeRibbon(route([walk([[10, 20], [20, 20]], 'up')]), marker)).toThrow('marker’s floor')
    expect(() => routeRibbon(current, { ...marker, heading_deg: NaN })).toThrow('finite')
    expect(() => routeRibbon(route([walk([[10, 20], [Infinity, 20]])]), marker)).toThrow('finite')
  })
})

describe('WebXR session lifecycle (offline browser/renderer doubles)', () => {
  let dom: Window
  let events: string[]
  let options: ArOptions
  let session: XRSession
  let emitEnd: () => void
  let trackingLost: () => void
  let runtime: ArRuntime
  beforeEach(() => {
    dom = new Window()
    Object.defineProperties(globalThis, {
      window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
      navigator: { value: dom.navigator, configurable: true },
    })
    events = []
    options = {
      route: route([walk([[10, 20], [20, 20]])]), marker,
      container: dom.document.createElement('div') as unknown as HTMLElement,
      overlay: dom.document.createElement('div') as unknown as HTMLElement,
      stopCamera: () => { events.push('camera stopped') },
      onLost: () => { events.push('lost') },
    }
    session = {
      end: async () => { events.push('session ended'); emitEnd() },
      addEventListener: (_kind: string, callback: () => void) => { emitEnd = callback },
    } as unknown as XRSession
    runtime = {
      xr: { requestSession: async (mode, init) => {
        events.push('requested')
        expect(mode).toBe('immersive-ar')
        expect(init).toEqual({ requiredFeatures: ['local'], optionalFeatures: ['hit-test', 'dom-overlay', 'local-floor'], domOverlay: { root: options.overlay } })
        return session
      } },
      loadRenderer: async (_session, _vertices, _container, lost) => {
        trackingLost = lost
        events.push('renderer loaded')
        return { dispose: () => { events.push('renderer disposed') } }
      },
    }
  })
  afterEach(() => { void dom.happyDOM.abort() })

  test('stops camera and requests XR immediately before loading any renderer', async () => {
    const started = startAr(options, runtime)
    expect(events).toEqual(['camera stopped', 'requested'])
    const handle = await started
    expect(events).toEqual(['camera stopped', 'requested', 'renderer loaded'])
    await handle.stopAr()
    await handle.stopAr()
    expect(events).toEqual(['camera stopped', 'requested', 'renderer loaded', 'renderer disposed', 'session ended'])
  })
  test('closes a delayed XR session after cancellation without loading Three.js', async () => {
    let resolve!: (session: XRSession) => void
    runtime.xr = { requestSession: () => new Promise(value => { resolve = value }) }
    const abort = new AbortController()
    const started = startAr({ ...options, signal: abort.signal }, runtime)
    abort.abort()
    resolve(session)
    await expect(started).rejects.toThrow('cancelled')
    expect(events).toEqual(['camera stopped', 'session ended'])
  })
  test('disposes a delayed renderer after cancellation', async () => {
    let resolve!: (value: { dispose(): void }) => void
    runtime.loadRenderer = () => new Promise(value => { resolve = value })
    const abort = new AbortController()
    const started = startAr({ ...options, signal: abort.signal }, runtime)
    await Promise.resolve()
    abort.abort()
    resolve({ dispose: () => { events.push('delayed renderer disposed') } })
    await expect(started).rejects.toThrow('cancelled')
    expect(events).toEqual(['camera stopped', 'requested', 'session ended', 'delayed renderer disposed'])
  })
  test('ends the session and releases its renderer on lost tracking', async () => {
    await startAr(options, runtime)
    trackingLost()
    trackingLost()
    expect(events.filter(event => event === 'lost').length).toBe(1)
    expect(events).toContain('renderer disposed')
    expect(events).toContain('session ended')
  })
  test('cleans up when the native XR exit button ends the session', async () => {
    const handle = await startAr(options, runtime)
    emitEnd()
    await handle.stopAr()
    expect(events).toEqual(['camera stopped', 'requested', 'renderer loaded', 'renderer disposed', 'lost'])
  })
  test('releases the XR session after renderer setup fails', async () => {
    runtime.loadRenderer = async () => { throw new Error('WebGL unavailable') }
    await expect(startAr(options, runtime)).rejects.toThrow('WebGL unavailable')
    expect(events).toContain('session ended')
    expect(events).not.toContain('lost')
  })
  test('ends AR on page hide without invoking a retired component callback', async () => {
    await startAr(options, runtime)
    dom.dispatchEvent(new dom.Event('pagehide'))
    expect(events).toContain('renderer disposed')
    expect(events).toContain('session ended')
    expect(events).not.toContain('lost')
  })
  test('does not ask for media permissions for a cancelled or unusable route', async () => {
    const abort = new AbortController()
    abort.abort()
    await expect(startAr({ ...options, signal: abort.signal }, runtime)).rejects.toThrow('cancelled')
    await expect(startAr({ ...options, route: { ...options.route, geometry: 'provisional' } }, runtime)).rejects.toThrow('computed route')
    expect(events).toEqual([])
  })
})
