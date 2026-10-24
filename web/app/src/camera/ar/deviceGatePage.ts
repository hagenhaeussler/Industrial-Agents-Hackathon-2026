import jsQR from 'jsqr'
import { DeviceGate, getXr, requestMotionPermission } from './deviceGate'
import type { MotionPermission } from './deviceGate'

const element = <T extends HTMLElement>(id: string) => {
  const node = document.getElementById(id)
  if (!node) throw new Error(`Device gate element ${id} is missing.`)
  return node as T
}
const video = element<HTMLVideoElement>('preview')
const canvas = document.createElement('canvas')
const context = canvas.getContext('2d', { willReadFrequently: true })
const output = element<HTMLTextAreaElement>('results')
const gate = new DeviceGate(navigator.mediaDevices, getXr())
let scanFrame = 0
let lastScan = 0
let previousCode: string | null = null
const rows: string[] = []

function log(test: string, result: string) {
  rows.push(`${new Date().toISOString()} | ${test} | ${result}`)
  const model = element<HTMLInputElement>('model').value || 'not supplied'
  output.value = [`Device model: ${model}`, `Browser: ${navigator.userAgent}`, `Secure context: ${window.isSecureContext}`, 'Real-device operator log (no media saved)', ...rows].join('\n')
  output.scrollTop = output.scrollHeight
  element<HTMLOutputElement>('status').textContent = `${test}: ${result}`
}

async function test(name: string, action: () => Promise<unknown>) {
  try { log(name, JSON.stringify(await action())) } catch (error) {
    log(name, `FAILED — ${error instanceof Error ? error.message : 'Permission or capability unavailable'}`)
  }
}

function stopScan() {
  cancelAnimationFrame(scanFrame)
  scanFrame = 0
  previousCode = null
  context?.clearRect(0, 0, canvas.width, canvas.height)
  canvas.width = canvas.height = 0
}

function scan(now: number) {
  scanFrame = requestAnimationFrame(scan)
  if (now - lastScan < 150 || !context || !video.videoWidth || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return
  lastScan = now
  const scale = Math.min(1, 640 / video.videoWidth)
  canvas.width = Math.round(video.videoWidth * scale)
  canvas.height = Math.round(video.videoHeight * scale)
  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  const image = context.getImageData(0, 0, canvas.width, canvas.height)
  const code = jsQR(image.data, image.width, image.height, { inversionAttempts: 'dontInvert' })
  image.data.fill(0)
  context.clearRect(0, 0, canvas.width, canvas.height)
  if (code && code.data !== previousCode) {
    previousCode = code.data
    // A QR is data: display it as text; never navigate or execute its contents.
    log('jsQR scan', `PASS — decoded ${code.data.slice(0, 200)}`)
  }
}

function startMedia(camera: boolean, microphone: boolean) {
  stopScan()
  void test(camera && microphone ? 'Camera + microphone' : camera ? 'Rear camera' : 'Microphone', async () => {
    const stream = await gate.startMedia(camera, microphone)
    video.srcObject = stream
    if (camera) {
      try { await video.play() } catch (error) { gate.stopMedia(); video.srcObject = null; throw error }
    }
    return { video: stream.getVideoTracks().length, audio: stream.getAudioTracks().length }
  })
}

element('camera').addEventListener('click', () => startMedia(true, false))
element('microphone').addEventListener('click', () => startMedia(false, true))
element('both').addEventListener('click', () => startMedia(true, true))
element('scan').addEventListener('click', () => {
  if (!video.srcObject || !video.videoWidth) { log('jsQR scan', 'Start the rear camera first.'); return }
  stopScan()
  scanFrame = requestAnimationFrame(scan)
  log('jsQR scan', 'Scanning in memory. Point the camera at a printed position QR.')
})
element('xr-support').addEventListener('click', () => { void test('Immersive AR supported', () => gate.supportsAr()) })
element('xr-start').addEventListener('click', () => {
  stopScan()
  video.srcObject = null
  void test('XR session + reference spaces', () => gate.requestAr(element('xr-overlay')))
})
element('stop').addEventListener('click', () => {
  stopScan()
  video.srcObject = null
  void test('Stop all media/XR', async () => { await gate.stopAll(); return 'Stopped' })
})
element('xr-stop').addEventListener('click', () => { void test('End XR', async () => { await gate.stopAll(); return 'Stopped' }) })

element('motion').addEventListener('click', () => {
  const motion = (window as unknown as { DeviceOrientationEvent?: MotionPermission }).DeviceOrientationEvent
  // Invoke before any await so Safari sees the click's transient activation.
  const permission = requestMotionPermission(motion)
  void test('Motion permission', async () => {
    const result = await permission
    if (result === 'granted') log('Motion data', 'Waiting for a sensor event; rotate the phone gently.')
    return result
  })
})
let motionLogged = false
window.addEventListener('deviceorientation', event => {
  if (event.alpha === null) return
  element('orientation').textContent = `Relative alpha: ${event.alpha.toFixed(1)}° (not a compass heading)`
  if (!motionLogged) { motionLogged = true; log('Motion sensor event', 'PASS — relative alpha received') }
})

element('tone').addEventListener('click', () => {
  void test('Speaker tone', async () => {
    const audio = new AudioContext()
    try {
      await audio.resume()
      const oscillator = audio.createOscillator()
      const gain = audio.createGain()
      gain.gain.value = 0.08
      oscillator.frequency.value = 660
      oscillator.connect(gain).connect(audio.destination)
      oscillator.start()
      oscillator.stop(audio.currentTime + 0.3)
      await new Promise<void>(resolve => { oscillator.onended = () => resolve() })
      return 'Tone sent to output. Record whether you heard it while camera + microphone were active.'
    } finally { await audio.close() }
  })
})
element('tone-yes').addEventListener('click', () => log('Operator audio check with camera + mic', 'PASS — heard tone'))
element('tone-no').addEventListener('click', () => log('Operator audio check with camera + mic', 'FAILED — no sound; try headphones'))
element('copy').addEventListener('click', () => {
  if (!navigator.clipboard) { output.focus(); output.select(); return }
  void navigator.clipboard.writeText(output.value).catch(() => { output.focus(); output.select() })
})
element('model').addEventListener('change', () => log('Device identified', 'Operator supplied model; browser version is recorded above.'))

function cleanup() {
  stopScan()
  video.srcObject = null
  void gate.stopAll().catch(() => {})
}
window.addEventListener('pagehide', cleanup)
document.addEventListener('visibilitychange', () => { if (document.hidden) cleanup() })
log('Ready', 'No permissions requested. Tests run only when you press their buttons.')
