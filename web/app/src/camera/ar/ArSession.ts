import type { Marker, ReachableRoute } from '../../api/types'
import { buildingToXr, DEFAULT_FLOOR_Y } from './frames'

export type ArMarker = Pick<Marker, 'building_id' | 'floor_id' | 'point' | 'heading_deg'>
export type ArOptions = {
  route: ReachableRoute
  marker: ArMarker
  container: HTMLElement
  overlay: HTMLElement
  /** Stop the camera hook synchronously; WebXR owns its own camera. */
  stopCamera: () => void
  onLost: (message: string) => void
  signal?: AbortSignal
  /** Camera-relative floor height measured while standing on the marker. */
  floorY?: number
}
export type ArHandle = { stopAr(): Promise<void> }
type Renderer = { dispose(): void }
type Xr = Pick<XRSystem, 'requestSession'>
type LoadRenderer = (session: XRSession, vertices: number[], container: HTMLElement,
  trackingLost: () => void) => Promise<Renderer>
/** Injectable browser seams for offline lifecycle tests. Production uses WebXR and Three.js. */
export type ArRuntime = { xr?: Xr; loadRenderer?: LoadRenderer }

const LOST = 'AR tracking stopped. Return to the map and scan a position code to re-anchor.'
const CANCELLED = 'AR start cancelled.'

/** Exact current-floor walk segments only; never bridge a lift, stair, or missing segment. */
export function routeRibbon(route: ReachableRoute, marker: ArMarker,
  floorY = DEFAULT_FLOOR_Y, width = 0.16): number[] {
  if (route.geometry === 'provisional') throw new Error('AR needs a computed route. Use the 2D map.')
  if (route.building_id !== marker.building_id) throw new Error('Scan a position code for this building.')
  if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(floorY)) throw new Error('AR dimensions must be finite, with a positive ribbon width.')
  // Validate even an empty route's marker before starting any permissions.
  buildingToXr(marker.point, marker, floorY)
  const vertices: number[] = []
  for (const segment of route.segments) {
    if (segment.floor_id !== marker.floor_id || segment.kind !== 'walk') break
    for (let i = 1; i < segment.points.length; i += 1) {
      const a = buildingToXr(segment.points[i - 1]!, marker, floorY + 0.02)
      const b = buildingToXr(segment.points[i]!, marker, floorY + 0.02)
      const dx = b.x - a.x, dz = b.z - a.z
      const length = Math.hypot(dx, dz)
      if (length < 1e-6) continue
      const rx = -dz / length * width / 2, rz = dx / length * width / 2
      const leftA = [a.x - rx, a.y, a.z - rz], rightA = [a.x + rx, a.y, a.z + rz]
      const leftB = [b.x - rx, b.y, b.z - rz], rightB = [b.x + rx, b.y, b.z + rz]
      vertices.push(...leftA, ...rightA, ...leftB, ...rightA, ...rightB, ...leftB)
    }
  }
  if (!vertices.length) throw new Error('No walking line is available on this marker’s floor. Use the map or scan the next position code.')
  return vertices
}

/**
 * Call directly from the user's tap after they confirm standing on the marker,
 * facing its heading. The request happens before importing Three.js or awaiting.
 * A decoded QR is a declared standing point, never a measured camera pose.
 */
export async function startAr(options: ArOptions, runtime: ArRuntime = {}): Promise<ArHandle> {
  const { container, overlay, signal } = options
  if (signal?.aborted) throw new Error(CANCELLED)
  const vertices = routeRibbon(options.route, options.marker, options.floorY)
  const xr = runtime.xr ?? (navigator as Navigator & { xr?: XRSystem }).xr
  if (!xr) throw new Error('Immersive AR is unavailable. Keep using the 2D map.')
  let session: XRSession | null = null
  let renderer: Renderer | null = null
  let stopped = false
  let ended = false
  let endPromise: Promise<void> | undefined
  const cleanup = () => {
    renderer?.dispose()
    renderer = null
    signal?.removeEventListener('abort', abort)
    document.removeEventListener('visibilitychange', hidden)
    window.removeEventListener('pagehide', abort)
  }
  const stopAr = async () => {
    stopped = true
    cleanup()
    if (session && !ended && !endPromise) {
      endPromise = session.end().catch(() => { /* Browser may already have ended it. */ })
    }
    await endPromise
  }
  const abort = () => { void stopAr() }
  const hidden = () => { if (document.hidden) abort() }
  const loseTracking = () => {
    if (stopped) return
    void stopAr()
    options.onLost(LOST)
  }
  signal?.addEventListener('abort', abort, { once: true })
  document.addEventListener('visibilitychange', hidden)
  window.addEventListener('pagehide', abort)
  try {
    options.stopCamera()
    // Keep this call before the first await: immersive XR needs transient activation.
    const requested = xr.requestSession('immersive-ar', {
      requiredFeatures: ['local'], optionalFeatures: ['hit-test', 'dom-overlay', 'local-floor'],
      domOverlay: { root: overlay },
    })
    session = await requested
    session.addEventListener('end', () => {
      ended = true
      const unexpected = !stopped
      stopped = true
      cleanup()
      if (unexpected) options.onLost(LOST)
    }, { once: true })
    if (stopped || signal?.aborted) { await stopAr(); throw new Error(CANCELLED) }
    const created = await (runtime.loadRenderer ?? loadThreeRenderer)(session, vertices, container, loseTracking)
    if (stopped || signal?.aborted) { created.dispose(); await stopAr(); throw new Error(CANCELLED) }
    renderer = created
    return { stopAr }
  } catch (error) {
    await stopAr()
    throw error
  }
}

async function loadThreeRenderer(session: XRSession, vertices: number[], container: HTMLElement,
  trackingLost: () => void): Promise<Renderer> {
  // Camera mode only; no Three.js runtime is added to the desk/2D entry chunk.
  const THREE = await import('three')
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  const geometry = new THREE.BufferGeometry()
  const material = new THREE.MeshBasicMaterial({ color: 0xdcff58, side: THREE.DoubleSide })
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera()
  const anchor = new THREE.Group()
  let disposed = false
  const dispose = () => {
    if (disposed) return
    disposed = true
    renderer.setAnimationLoop(null)
    geometry.dispose()
    material.dispose()
    renderer.dispose()
    renderer.domElement.remove()
  }
  try {
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    anchor.add(new THREE.Mesh(geometry, material))
    scene.add(anchor)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setSize(container.clientWidth || window.innerWidth, container.clientHeight || window.innerHeight)
    renderer.setClearColor(0x000000, 0)
    renderer.domElement.setAttribute('aria-label', 'Experimental marker-anchored AR walking line')
    renderer.xr.enabled = true
    renderer.xr.setReferenceSpaceType('local')
    await renderer.xr.setSession(session)
    container.appendChild(renderer.domElement)
    let anchored = false, missingFrames = 0
    const orientation = new THREE.Quaternion()
    const euler = new THREE.Euler(0, 0, 0, 'YXZ')
    renderer.setAnimationLoop((_time, frame) => {
      if (disposed || !frame) return
      const reference = renderer.xr.getReferenceSpace()
      const pose = reference ? frame.getViewerPose(reference) : null
      if (!pose) {
        if (++missingFrames >= 60) trackingLost()
        return
      }
      missingFrames = 0
      if (!anchored) {
        // Local reference origins/yaw vary by runtime. Align the declared marker
        // with the first real viewer pose rather than assuming an XR camera pose.
        const { position, orientation: rotation } = pose.transform
        anchor.position.set(position.x, position.y, position.z)
        orientation.set(rotation.x, rotation.y, rotation.z, rotation.w)
        euler.setFromQuaternion(orientation, 'YXZ')
        anchor.rotation.y = euler.y
        anchored = true
      }
      renderer.render(scene, camera)
    })
    return { dispose }
  } catch (error) {
    dispose()
    throw error
  }
}
