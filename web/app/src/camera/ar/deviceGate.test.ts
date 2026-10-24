import { describe, expect, it } from 'bun:test'
import { DeviceGate, requestMotionPermission } from './deviceGate'
import type { GateSession, GateXr } from './deviceGate'

function stream() {
  let stopped = 0
  return { value: { getTracks: () => [{ stop: () => { stopped += 1 } }] } as unknown as MediaStream, stopped: () => stopped }
}

describe('device gate lifecycle', () => {
  it('requests rear camera and microphone together and stops every track', async () => {
    const media = stream()
    let constraints: MediaStreamConstraints | undefined
    const gate = new DeviceGate({ getUserMedia: async value => { constraints = value; return media.value } }, undefined)
    await gate.startMedia(true, true)
    expect(constraints).toEqual({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } }, audio: true })
    await gate.stopAll()
    expect(media.stopped()).toBe(1)
  })
  it('stops a delayed stream after cancellation', async () => {
    const media = stream()
    let resolve!: (value: MediaStream) => void
    const gate = new DeviceGate({ getUserMedia: () => new Promise(done => { resolve = done }) }, undefined)
    const pending = gate.startMedia(true, false)
    gate.stopMedia()
    resolve(media.value)
    await expect(pending).rejects.toThrow('cancelled')
    expect(media.stopped()).toBe(1)
  })
  it('cleans up camera before requesting XR and tolerates missing local-floor', async () => {
    const media = stream()
    let ended = 0
    const session: GateSession = {
      end: async () => { ended += 1 }, addEventListener: () => {},
      requestReferenceSpace: async type => { if (type === 'local-floor') throw new Error('not supported'); return {} },
    }
    const xr: GateXr = {
      isSessionSupported: async () => true,
      requestSession: async (mode, options) => {
        expect(media.stopped()).toBe(1)
        expect(mode).toBe('immersive-ar')
        expect(options.requiredFeatures).toEqual(['local'])
        expect(options.optionalFeatures).toEqual(['hit-test', 'dom-overlay', 'local-floor'])
        return session
      },
    }
    const gate = new DeviceGate({ getUserMedia: async () => media.value }, xr)
    expect(await gate.supportsAr()).toBe(true)
    await gate.startMedia(true, false)
    expect(await gate.requestAr({} as HTMLElement)).toEqual({ local: true, localFloor: false })
    await gate.stopAll()
    expect(ended).toBe(1)
  })
  it('ends a late XR permission result after Stop was pressed', async () => {
    let resolve!: (value: GateSession) => void
    let ended = 0
    const session: GateSession = { end: async () => { ended += 1 }, addEventListener: () => {}, requestReferenceSpace: async () => ({}) }
    const gate = new DeviceGate(undefined, { isSessionSupported: async () => true, requestSession: () => new Promise(done => { resolve = done }) })
    const pending = gate.requestAr({} as HTMLElement)
    await gate.stopAll()
    resolve(session)
    await expect(pending).rejects.toThrow('cancelled')
    expect(ended).toBe(1)
  })
  it('returns unsupported AR honestly', async () => {
    const gate = new DeviceGate(undefined, undefined)
    expect(await gate.supportsAr()).toBe(false)
    await expect(gate.requestAr({} as HTMLElement)).rejects.toThrow('unavailable')
    await expect(gate.startMedia(true, false)).rejects.toThrow('HTTPS')
  })
  it('requests motion permission without consuming user activation first', async () => {
    let called = false
    const result = requestMotionPermission({ requestPermission: () => { called = true; return Promise.resolve('denied') } })
    expect(called).toBe(true)
    expect(await result).toBe('denied')
    expect(await requestMotionPermission(undefined)).toBe('unsupported')
  })
})
