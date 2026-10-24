/** Capability probes only. This module never records, stores, or uploads media. */
export type GateSession = {
  end(): Promise<void>
  requestReferenceSpace(type: 'local' | 'local-floor'): Promise<unknown>
  addEventListener(type: 'end', listener: () => void, options?: AddEventListenerOptions): void
}
export type GateXr = {
  isSessionSupported(mode: 'immersive-ar'): Promise<boolean>
  requestSession(mode: 'immersive-ar', options: {
    requiredFeatures: string[]
    optionalFeatures: string[]
    domOverlay: { root: HTMLElement }
  }): Promise<GateSession>
}
export type GateMedia = { getUserMedia(constraints: MediaStreamConstraints): Promise<MediaStream> }
export type MotionPermission = { requestPermission?: () => Promise<'granted' | 'denied'> }

export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach(track => track.stop())
}

export function getXr(): GateXr | undefined {
  return (navigator as unknown as { xr?: GateXr }).xr
}

export class DeviceGate {
  private stream: MediaStream | null = null
  private session: GateSession | null = null
  private mediaGeneration = 0
  private xrGeneration = 0
  private xrPending = false

  constructor(private readonly media: GateMedia | undefined, private readonly xr: GateXr | undefined) {}

  /** Call from a click; the combined mode tests simultaneous rear camera + microphone. */
  async startMedia(camera: boolean, microphone: boolean): Promise<MediaStream> {
    if (!this.media) throw new Error('Camera and microphone need HTTPS or localhost and a supported browser.')
    if (!camera && !microphone) throw new Error('Choose a camera or microphone test.')
    if (this.session || this.xrPending) throw new Error('End the XR test before starting camera or microphone.')
    this.stopMedia()
    const generation = this.mediaGeneration
    const stream = await this.media.getUserMedia({
      video: camera ? { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } } : false,
      audio: microphone,
    })
    if (generation !== this.mediaGeneration) {
      stopStream(stream)
      throw new Error('Media request cancelled.')
    }
    this.stream = stream
    return stream
  }

  stopMedia(): void {
    this.mediaGeneration += 1
    stopStream(this.stream)
    this.stream = null
  }

  async supportsAr(): Promise<boolean> {
    return this.xr ? this.xr.isSessionSupported('immersive-ar') : false
  }

  /** No await before requestSession: preserve the button's transient user activation. */
  async requestAr(overlay: HTMLElement): Promise<{ local: boolean; localFloor: boolean }> {
    this.stopMedia()
    if (!this.xr) throw new Error('Immersive AR is unavailable. Keep using the 2D map.')
    if (this.session || this.xrPending) throw new Error('An XR test is already running.')
    const generation = ++this.xrGeneration
    this.xrPending = true
    let session: GateSession | null = null
    try {
      session = await this.xr.requestSession('immersive-ar', {
        requiredFeatures: ['local'], optionalFeatures: ['hit-test', 'dom-overlay', 'local-floor'], domOverlay: { root: overlay },
      })
      if (generation !== this.xrGeneration) {
        await session.end()
        throw new Error('XR request cancelled.')
      }
      this.session = session
      session.addEventListener('end', () => { if (this.session === session) this.session = null }, { once: true })
      await session.requestReferenceSpace('local')
      let localFloor = false
      try { await session.requestReferenceSpace('local-floor'); localFloor = true } catch { /* Optional. */ }
      if (generation !== this.xrGeneration) throw new Error('XR request cancelled.')
      return { local: true, localFloor }
    } catch (error) {
      if (session && this.session === session) { this.session = null; await session.end() }
      throw error
    } finally {
      if (generation === this.xrGeneration) this.xrPending = false
    }
  }

  async stopAll(): Promise<void> {
    this.xrGeneration += 1
    this.xrPending = false
    this.stopMedia()
    const session = this.session
    this.session = null
    if (session) await session.end()
  }
}

/** iOS requires the call itself to happen inside the click handler. */
export function requestMotionPermission(motion: MotionPermission | undefined): Promise<'granted' | 'denied' | 'unsupported'> {
  if (!motion) return Promise.resolve('unsupported')
  return motion.requestPermission ? motion.requestPermission() : Promise.resolve('granted')
}
