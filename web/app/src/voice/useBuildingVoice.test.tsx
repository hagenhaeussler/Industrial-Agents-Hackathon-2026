import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test'
import { Window } from 'happy-dom'
import { act, cleanup, renderHook } from '@testing-library/react'
import type { MessagePayload } from '@elevenlabs/react'
import type { BuildingVoiceOptions } from './useBuildingVoice'
import type { Fetcher, ToolDisplay } from './clientTools'

const starts: unknown[] = []
const contexts: string[] = []
const lifecycle: string[] = []
const userMessages: string[] = []
const muteChanges: boolean[] = []
let stops = 0
let currentTools: Record<string, (args?: unknown) => Promise<string>>
type Callbacks = {
  clientTools: typeof currentTools
  onError?: (message?: unknown, detail?: unknown) => void
  onConnect?: () => void
  onStatusChange?: (props: { status: string }) => void
  onDisconnect?: (details?: { reason?: string; message?: string; closeReason?: string; closeCode?: number }) => void
  onMessage?: (payload: { role?: string; source?: string; message?: string; event_id?: number; response_id?: string }) => void
}
let currentOnError: Callbacks['onError']
let currentOnConnect: Callbacks['onConnect']
let currentOnStatusChange: Callbacks['onStatusChange']
let currentOnDisconnect: Callbacks['onDisconnect']
let currentOnMessage: Callbacks['onMessage']
let inputVolume = 0, outputVolume = 0, meterReads = 0
let sendFailure = false, muteFailure = false
const conversation = {
  status: 'disconnected', isSpeaking: false, isMuted: false,
  startSession: (options: Callbacks) => {
    lifecycle.push('start'); starts.push(options)
    currentTools = options.clientTools
    currentOnError = options.onError
    currentOnConnect = options.onConnect
    currentOnStatusChange = options.onStatusChange
    currentOnDisconnect = options.onDisconnect
    currentOnMessage = options.onMessage
  },
  endSession: async () => { lifecycle.push('end'); stops++ },
  sendContextualUpdate: (text: string) => { contexts.push(text) },
  sendUserMessage: (text: string) => { if (sendFailure) throw new Error('secret-provider-token'); userMessages.push(text) },
  setMuted: (value: boolean) => { if (muteFailure) throw new Error('secret-provider-token'); conversation.isMuted = value; muteChanges.push(value) },
  getInputVolume: () => { meterReads++; return inputVolume },
  getOutputVolume: () => { meterReads++; return outputVolume },
}
mock.module('@elevenlabs/react', () => ({ useConversation: () => conversation }))

let useBuildingVoice: typeof import('./useBuildingVoice').useBuildingVoice
let dom: Window
const originalFetch = globalThis.fetch
const fetchMock = globalThis as unknown as { fetch: Fetcher }
const options: BuildingVoiceOptions = { agent: 'navigator', sessionId: 'offline-session' }
const token = () => new Response(JSON.stringify({ token: 'offline-test-token', agent_id: 'offline-agent' }), { status: 200 })
const instruction = () => new Response(JSON.stringify({ ok: true, speech: 'Continue to the next room.',
  result: { kind: 'enter' }, display: { kind: 'instruction' } }), { status: 200 })

function deferredToken() {
  let release!: (response: Response) => void
  let signal: AbortSignal | null | undefined
  fetchMock.fetch = async (_input, init) => {
    signal = init?.signal
    // Deliberately ignore abort to exercise the post-await generation check too.
    return new Promise<Response>(resolve => { release = resolve })
  }
  return { release: () => release(token()), signal: () => signal }
}

beforeAll(async () => { useBuildingVoice = (await import('./useBuildingVoice')).useBuildingVoice })
beforeEach(() => {
  currentOnError = undefined; currentOnMessage = undefined; currentOnDisconnect = undefined
  currentOnConnect = undefined; currentOnStatusChange = undefined; currentTools = {}
  starts.length = 0; contexts.length = 0; lifecycle.length = 0; stops = 0; conversation.status = 'disconnected'
  conversation.isMuted = false; conversation.isSpeaking = false; inputVolume = 0; outputVolume = 0; meterReads = 0
  userMessages.length = 0; muteChanges.length = 0; sendFailure = false; muteFailure = false
  dom = new Window({ url: 'http://localhost' })
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  })
})
afterEach(() => { cleanup(); fetchMock.fetch = originalFetch; dom.happyDOM.abort() })

describe('voice start lifecycle', () => {
  test.each(['stop', 'session', 'agent', 'unmount'] as const)('a delayed token cannot start after %s', async cancellation => {
    const deferred = deferredToken()
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    let pending!: Promise<void>
    await act(async () => { pending = view.result.current.start(); await Promise.resolve() })
    if (cancellation === 'stop') await act(async () => { await view.result.current.stop() })
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    await act(async () => { deferred.release(); await pending })
    expect(starts).toEqual([])
    expect(deferred.signal()?.aborted).toBe(true)
    expect(view.result.current.error).toBeNull()
    expect(stops).toBe(cancellation === 'stop' ? 1 : 0)
  })

  test('an older cancelled finally cannot unlock a newer pending start', async () => {
    const releases: ((response: Response) => void)[] = []
    fetchMock.fetch = async () => new Promise<Response>(resolve => { releases.push(resolve) })
    const view = renderHook(() => useBuildingVoice(options))
    let old!: Promise<void>, current!: Promise<void>
    await act(async () => { old = view.result.current.start(); await Promise.resolve() })
    await act(async () => { await view.result.current.stop(); current = view.result.current.start(); await Promise.resolve() })
    expect(releases.length).toBe(2)
    await act(async () => { releases[0]!(token()); await old })
    await act(async () => { await view.result.current.start() })
    expect(releases.length).toBe(2)
    expect(starts).toEqual([])
    await act(async () => { releases[1]!(token()); await current })
    expect(starts).toMatchObject([{ conversationToken: 'offline-test-token' }])
    expect(view.result.current.error).toBeNull()
  })

  test('cancellation during JSON parsing is quiet', async () => {
    let release!: (body: unknown) => void
    fetchMock.fetch = async () => ({ ok: true, json: () => new Promise(resolve => { release = resolve }) }) as Response
    const view = renderHook(() => useBuildingVoice(options))
    let pending!: Promise<void>
    await act(async () => { pending = view.result.current.start(); await Promise.resolve(); await Promise.resolve() })
    await act(async () => { await view.result.current.stop(); release({ token: 'offline-test-token' }); await pending })
    expect(starts).toEqual([])
    expect(view.result.current.error).toBeNull()
  })

  test.each(['session', 'agent', 'unmount'] as const)('a retained start callback cannot restart a retired %s', async cancellation => {
    let requests = 0
    fetchMock.fetch = async () => { requests++; return token() }
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    const retiredStart = view.result.current.start
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    await act(async () => { await retiredStart() })
    expect(requests).toBe(0)
    expect(starts).toEqual([])
  })

  test('a current failure still offers text fallback without exposing token details', async () => {
    fetchMock.fetch = async () => { throw new Error('internal offline-test-token detail') }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => {
      await expect(view.result.current.start()).rejects.toThrow('Voice is unavailable. Please use text chat.')
    })
    expect(view.result.current.error).toBe('Voice is unavailable. Please use text chat.')
    expect(view.result.current.error).not.toContain('offline-test-token')
    expect(starts).toEqual([])
  })

  test('an asynchronous SDK connection failure is sanitized and can retry after ending the failed session', async () => {
    let requests = 0
    fetchMock.fetch = async () => { requests++; return token() }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start() })
    expect(starts.length).toBe(1)
    expect(view.result.current.error).toBeNull()
    // The real SDK returns void, then reports a failed handshake through onError
    // and its status context. Provider error text must never enter the UI.
    await act(async () => {
      conversation.status = 'error'
      const report = currentOnError as ((message: string, context: unknown) => void) | undefined
      report?.('Handshake failed at https://provider.invalid/?token=private-token', { token: 'private-token' })
    })
    expect(view.result.current.error).toBe('The voice connection could not start. Check your connection and try again.')
    expect(view.result.current.error).not.toContain('private-token')
    expect(view.result.current.status).toBe('error')
    await act(async () => { await expect(view.result.current.start()).rejects.toThrow('Voice is still closing') })
    expect(requests).toBe(1)
    await act(async () => { currentOnStatusChange?.({ status: 'disconnected' }); await new Promise(resolve => setTimeout(resolve, 0)) })
    await act(async () => { await view.result.current.start() })
    expect(requests).toBe(2)
    expect(lifecycle).toEqual(['start', 'end', 'start'])
    expect(view.result.current.error).toBeNull()
  })

  test.each(['session', 'agent', 'unmount'] as const)('an SDK error retained from a retired %s cannot change current UI state', async cancellation => {
    fetchMock.fetch = async () => token()
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    await act(async () => { await view.result.current.start() })
    const retiredError = currentOnError
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    await act(async () => { retiredError?.() })
    expect(view.result.current.error).toBeNull()
    expect(starts).toHaveLength(1)
  })
})

function userMessage(message = 'Take me to the workshop'): MessagePayload {
  return { source: 'user', role: 'user', message, event_id: 1 }
}

async function settleClosing() {
  await act(async () => { currentOnStatusChange?.({ status: 'disconnected' }); await new Promise(resolve => setTimeout(resolve, 0)) })
}

async function startVoice(view: { result: { current: { start: () => Promise<void> } } }) {
  const toolsFetch = fetchMock.fetch
  fetchMock.fetch = async (url, init) => {
    if (String(url).startsWith('/api/voice/token')) return token()
    if (url === '/api/agent/turns') return new Response(JSON.stringify({ turn_id: 'offline-user-turn' }))
    if (String(url).startsWith('/api/agent/turns/')) return new Response(JSON.stringify({ turn_id: 'offline-user-turn' }))
    return toolsFetch(url, init)
  }
  await act(async () => { await view.result.current.start() })
}

async function prepareVoice(view: { result: { current: { start: () => Promise<void> } } }) {
  await startVoice(view)
  await act(async () => { currentOnMessage?.(userMessage()) })
}

describe('voice tool lifecycle', () => {

  test('an SDK connection failure suppresses a pending instruction', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) } }))
    await prepareVoice(view)
    const pending = currentTools.next_step!()
    await Promise.resolve(); await Promise.resolve()
    await act(async () => { conversation.status = 'error'; currentOnError?.() })
    release(instruction())
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(displays).toEqual([])
    expect(view.result.current.error).toBe('Voice is unavailable. Please use text chat.')
  })

  test.each(['stop', 'session', 'agent', 'unmount'] as const)('invalidates a pending next_step on %s', async cancellation => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), {
      initialProps: { ...options, onDisplay: (display: ToolDisplay) => { displays.push(display) } } as BuildingVoiceOptions,
    })
    await prepareVoice(view)
    const pending = currentTools.next_step!()
    await Promise.resolve(); await Promise.resolve()
    if (cancellation === 'stop') await act(async () => { await view.result.current.stop() })
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    release(instruction())
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(displays).toEqual([])
  })

  test.each(['session', 'agent', 'unmount'] as const)('retained SDK tools cannot fetch for a retired %s', async cancellation => {
    let requests = 0
    fetchMock.fetch = async () => { requests++; return instruction() }
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    await prepareVoice(view)
    const retiredNext = currentTools.next_step!
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    expect(JSON.parse(await retiredNext()).ok).toBe(false)
    expect(requests).toBe(0)
  })

  test.each(['session', 'agent', 'unmount'] as const)('retired stop/context callbacks cannot affect a replacement %s', async cancellation => {
    conversation.status = 'connected'
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    const retired = view.result.current
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    await act(async () => { await retired.stop() })
    retired.sendContext('Old tour context must not reach the new conversation.')
    expect(stops).toBe(0)
    expect(contexts).toEqual([])
    if (cancellation !== 'unmount') {
      view.result.current.sendContext('Current tour context.')
      expect(contexts).toEqual(['Current tour context.'])
    }
  })

  test('handler recreation shares the next_step generation', async () => {
    let release!: (response: Response) => void
    let requests = 0
    fetchMock.fetch = async () => ++requests === 1
      ? new Promise<Response>(resolve => { release = resolve })
      : new Response(JSON.stringify({ ok: false, speech: 'No route.', error: { code: 'no_route' } }), { status: 200 })
    const displays: ToolDisplay[] = []
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), {
      initialProps: { ...options, onDisplay: (display: ToolDisplay) => { displays.push(display) } },
    })
    await prepareVoice(view)
    const pending = currentTools.next_step!()
    await Promise.resolve(); await Promise.resolve()
    view.rerender({ ...options, onDisplay: () => { throw new Error('Stale display after handler recreation') } })
    expect(JSON.parse(await currentTools.next_step!()).error.code).toBe('no_route')
    release(instruction())
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(displays).toEqual([])
  })

  test('context updates leave a sole instruction valid', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) } }))
    await prepareVoice(view)
    await act(async () => { currentOnConnect?.() })
    const pending = currentTools.next_step!()
    await Promise.resolve(); await Promise.resolve()
    view.result.current.sendContext('Tour updated after next_step advanced its index.')
    release(instruction())
    expect(JSON.parse(await pending).ok).toBe(true)
    expect(displays.length).toBe(1)
    expect(contexts.length).toBe(1)
  })

  test('retained SDK handlers publish to the latest callback after a render', async () => {
    fetchMock.fetch = async () => instruction()
    const old: ToolDisplay[] = [], latest: ToolDisplay[] = []
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), {
      initialProps: { ...options, onDisplay: display => { old.push(display) } } as BuildingVoiceOptions,
    })
    await prepareVoice(view)
    const retainedNext = currentTools.next_step!
    view.rerender({ ...options, onDisplay: display => { latest.push(display) } })
    expect(JSON.parse(await retainedNext()).ok).toBe(true)
    expect(old).toEqual([])
    expect(latest).toEqual([{ kind: 'instruction' }])
  })

  test('stop preserves a committed admin edit outcome while suppressing its retired display', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, agent: 'admin', onDisplay: display => { displays.push(display) } }))
    await prepareVoice(view)
    const pending = currentTools.commit_edit!({ proposal_id: 'offline-proposal' })
    await Promise.resolve(); await Promise.resolve()
    await act(async () => { await view.result.current.stop() })
    release(new Response(JSON.stringify({ ok: true, speech: 'Lift closed.', result: { event_id: 'evt-offline' }, display: { kind: 'edit_committed' } }), { status: 200 }))
    expect(JSON.parse(await pending).ok).toBe(true)
    expect(displays).toEqual([])
  })

  test('a late committed edit stays successful but cannot repaint a replacement session', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const old: ToolDisplay[] = [], replacement: ToolDisplay[] = []
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), {
      initialProps: { ...options, agent: 'admin', onDisplay: display => { old.push(display) } } as BuildingVoiceOptions,
    })
    await prepareVoice(view)
    const pending = currentTools.commit_edit!({ proposal_id: 'offline-session-switch-proposal' })
    await Promise.resolve(); await Promise.resolve()
    view.rerender({ ...options, sessionId: 'replacement-session', onDisplay: display => { replacement.push(display) } })
    release(new Response(JSON.stringify({ ok: true, speech: 'Lift closed.', result: { event_id: 'evt-committed' }, display: { kind: 'edit_committed' } }), { status: 200 }))
    const result = JSON.parse(await pending)
    expect(result.ok).toBe(true)
    expect(result.result.event_id).toBe('evt-committed')
    expect(old).toEqual([])
    expect(replacement).toEqual([])
  })
})

describe('real conversation state and controls', () => {
  test('reports connecting through token fetch and asynchronous SDK handshake without duplicate starts', async () => {
    const deferred = deferredToken()
    const view = renderHook(() => useBuildingVoice(options))
    let pending!: Promise<void>
    await act(async () => { pending = view.result.current.start(); await Promise.resolve() })
    expect(view.result.current.status).toBe('connecting')
    await act(async () => { await view.result.current.start() })
    expect(starts).toEqual([])
    await act(async () => { deferred.release(); await pending })
    expect(starts).toMatchObject([{ conversationToken: 'offline-test-token', connectionType: 'webrtc' }])
    expect(view.result.current.status).toBe('connecting')
    await act(async () => { await view.result.current.start() })
    expect(starts.length).toBe(1)
    await act(async () => { currentOnConnect?.() })
    expect(view.result.current.status).toBe('connected')
    await act(async () => { await view.result.current.stop() })
    expect(view.result.current.status).toBe('disconnected')
  })

  test('an ElevenLabs quota disconnect is visible even without onError, and permits retry', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnConnect?.() })
    await act(async () => { currentOnDisconnect?.({ reason: 'agent', closeCode: 4300, closeReason: 'private provider detail' }) })
    expect(view.result.current.error).toBe('Voice has reached its provider limit. Try again later or use text chat.')
    expect(view.result.current.status).toBe('disconnected')
    await act(async () => { await view.result.current.start() })
    expect(starts.length).toBe(2)
    expect(view.result.current.status).toBe('connecting')
    expect(view.result.current.error).toBeNull()
  })

  test('a failed SDK session’s delayed user-disconnect cannot cancel its replacement token', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnStatusChange?.({ status: 'disconnected' }); currentOnError?.('Handshake failed') })
    const deferred = deferredToken()
    let retry!: Promise<void>
    await act(async () => { retry = view.result.current.start(); await Promise.resolve() })
    await act(async () => { currentOnDisconnect?.({ reason: 'user' }) })
    expect(deferred.signal()?.aborted).toBe(false)
    expect(view.result.current.status).toBe('connecting')
    await act(async () => { deferred.release(); await retry; currentOnConnect?.() })
    expect(starts.length).toBe(2)
    expect(view.result.current.status).toBe('connected')
    expect(view.result.current.error).toBeNull()
  })

  test('stop during SDK handshake rejects early restart until the provider lock settles', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); await view.result.current.stop() })
    await act(async () => { await expect(view.result.current.start()).rejects.toThrow('Voice is still closing') })
    expect(starts.length).toBe(1)
    await act(async () => { currentOnConnect?.() }) // Late success from the cancelled start.
    expect(view.result.current.status).toBe('disconnected')
    await act(async () => { currentOnStatusChange?.({ status: 'disconnected' }); await new Promise(resolve => setTimeout(resolve, 0)) })
    await act(async () => { await view.result.current.start(); currentOnConnect?.() })
    expect(starts.length).toBe(2)
    expect(view.result.current.status).toBe('connected')
    expect(view.result.current.error).toBeNull()
  })

  test.each([10000, 30000])('a %dms lifecycle deadline exits the spinner without starting another locked SDK session', async deadline => {
    const timers = globalThis as unknown as { setTimeout: (callback: () => void, delay?: number) => ReturnType<typeof setTimeout> }
    const original = timers.setTimeout
    const owned: ReturnType<typeof setTimeout>[] = []
    let expire: (() => void) | undefined
    timers.setTimeout = (callback, delay) => {
      const id = original(callback, delay)
      if (delay === deadline) { expire = callback; owned.push(id) }
      return id
    }
    try {
      fetchMock.fetch = async () => token()
      const view = renderHook(() => useBuildingVoice(options))
      await act(async () => { await view.result.current.start() })
      if (deadline === 10000) await act(async () => { await view.result.current.stop() })
      expect(expire).toBeDefined()
      await act(async () => { expire?.() })
      expect(view.result.current.status).toBe('error')
      expect(view.result.current.error).toBe(deadline === 10000
        ? 'Voice could not finish closing. Reload this page before starting again.'
        : 'The voice connection could not start. Check your connection and try again.')
      await act(async () => { await expect(view.result.current.start()).rejects.toThrow(deadline === 10000 ? 'Reload this page' : 'Voice is still closing') })
      expect(starts.length).toBe(1)
      await act(async () => { currentOnStatusChange?.({ status: 'disconnected' }); await new Promise(resolve => setTimeout(resolve, 0)) })
      view.unmount()
    } finally {
      timers.setTimeout = original
      owned.forEach(clearTimeout)
    }
  })

  test.each(['agent', 'error'])('an unexpected %s disconnect has a safe explanation', async reason => {
    const view = renderHook(() => useBuildingVoice(options))
    await prepareVoice(view)
    await act(async () => { currentOnDisconnect?.({ reason, message: 'provider://secret-token' }) })
    expect(view.result.current.error).toBe(reason === 'error' ? 'The voice connection could not start. Check your connection and try again.' : 'The voice conversation ended. Tap to reconnect.')
    expect(view.result.current.error).not.toContain('secret-token')
  })

  test('explicit stop ignores late disconnect, errors, messages and connection callbacks', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await act(async () => { await view.result.current.stop(); currentOnError?.('secret-token'); currentOnDisconnect?.({ reason: 'error' }); currentOnMessage?.({ role: 'agent', message: 'Late message' }); currentOnConnect?.() })
    expect(view.result.current.error).toBeNull()
    expect(view.result.current.status).toBe('disconnected')
    expect(view.result.current.messages).toEqual([])
  })

  test.each([
    ['NotAllowedError', 'Microphone access was not allowed'],
    ['NotFoundError', 'No microphone was found'],
    ['NotReadableError', 'The microphone is unavailable'],
  ])('classifies microphone %s without showing provider details', async (name, text) => {
    const view = renderHook(() => useBuildingVoice(options))
    await prepareVoice(view)
    await act(async () => { currentOnError?.('hidden-provider-token', new DOMException('hidden-provider-token', name)) })
    expect(view.result.current.error).toContain(text)
    expect(view.result.current.error).not.toContain('hidden-provider-token')
  })

  test('captures real speaker turns, replaces duplicate response IDs and retains at most 60', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await act(async () => {
      currentOnMessage?.({ role: 'user', message: 'Find the CNC mill', event_id: 1 })
      currentOnMessage?.({ role: 'agent', message: 'Looking for it', response_id: 'response-1' })
      currentOnMessage?.({ role: 'agent', message: 'The CNC mill is highlighted.', response_id: 'response-1' })
    })
    expect(view.result.current.messages.map(message => [message.role, message.text])).toEqual([
      ['user', 'Find the CNC mill'], ['agent', 'The CNC mill is highlighted.'],
    ])
    await act(async () => { for (let index = 0; index < 65; index++) currentOnMessage?.({ role: index % 2 ? 'agent' : 'user', message: `Turn ${index}`, event_id: index + 100 }) })
    expect(view.result.current.messages.length).toBe(60)
    expect(view.result.current.messages[0]!.text).toBe('Turn 5')
    expect(new Set(view.result.current.messages.map(message => message.id)).size).toBe(60)
  })

  test.each(['session', 'agent', 'unmount'] as const)('transcripts and retained SDK callbacks cannot cross a retired %s', async retired => {
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    await startVoice(view)
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Old user turn' }) })
    const old = { message: currentOnMessage, connect: currentOnConnect, disconnect: currentOnDisconnect }
    if (retired === 'session') view.rerender({ ...options, sessionId: 'new-session' })
    if (retired === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (retired === 'unmount') view.unmount()
    await act(async () => { old.message?.({ role: 'agent', message: 'Retired turn' }); old.connect?.(); old.disconnect?.({ reason: 'error' }) })
    expect(view.result.current.messages.some(message => message.text === 'Retired turn')).toBe(false)
    if (retired !== 'unmount') {
      expect(view.result.current.messages).toEqual([])
      const empty = view.result.current.messages
      view.rerender(retired === 'session' ? { ...options, sessionId: 'new-session' } : { ...options, agent: 'admin' })
      expect(view.result.current.messages).toBe(empty)
      expect(view.result.current.error).toBeNull()
      expect(view.result.current.status).toBe('disconnected')
    }
  })

  test('typed conversation turns go to the ElevenLabs agent only when connected', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    expect(view.result.current.sendText('Find the CNC mill')).toBe(false)
    await startVoice(view)
    await act(async () => { currentOnConnect?.() })
    await act(async () => { expect(view.result.current.sendText('  Find the CNC mill  ')).toBe(true) })
    expect(userMessages).toEqual(['Find the CNC mill'])
    expect(view.result.current.sendText(' ')).toBe(false)
    sendFailure = true
    await act(async () => { expect(view.result.current.sendText('Failed turn')).toBe(false) })
    expect(view.result.current.error).not.toContain('secret-provider-token')
    const retiredSend = view.result.current.sendText
    view.unmount()
    expect(retiredSend('Retired turn')).toBe(false)
    expect(userMessages).toEqual(['Find the CNC mill'])
  })

  test('mute uses the SDK and meters clamp levels, stop reading on disconnect and clear UI levels', async () => {
    inputVolume = 2; outputVolume = 0.4
    const view = renderHook(() => useBuildingVoice(options))
    expect(meterReads).toBe(0)
    await startVoice(view)
    await act(async () => { currentOnConnect?.() })
    expect(view.result.current.inputLevel).toBe(1)
    expect(view.result.current.outputLevel).toBe(0.4)
    await act(async () => { view.result.current.setMuted(true); view.rerender() })
    expect(muteChanges).toEqual([true])
    expect(view.result.current.isMuted).toBe(true)
    expect(view.result.current.inputLevel).toBe(0)
    outputVolume = NaN
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 90)) })
    expect(view.result.current.outputLevel).toBe(0)
    await act(async () => { currentOnDisconnect?.({ reason: 'user' }) })
    const readAtDisconnect = meterReads
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 90)) })
    expect(meterReads).toBe(readAtDisconnect)
    expect(view.result.current.isMuted).toBe(false)
    expect(view.result.current.inputLevel).toBe(0)
    expect(view.result.current.outputLevel).toBe(0)
  })

  test('mute failures stay sanitized and a pending SDK session ends on unmount', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnConnect?.() })
    muteFailure = true
    await act(async () => { view.result.current.setMuted(true) })
    expect(view.result.current.error).not.toContain('secret-provider-token')
    view.unmount()
    expect(stops).toBe(1)
  })

  test('extra UI tools cannot override server tools and cannot act after retirement', async () => {
    let changed = 0, overrideCalls = 0
    fetchMock.fetch = async () => instruction()
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: { ...options, clientTools: {
      update_selection: () => { changed++; return 'selection changed' }, find: () => { overrideCalls++; return 'bad override' },
    } } as BuildingVoiceOptions })
    await prepareVoice(view)
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('selection changed')
    expect(JSON.parse(await currentTools.find!({ query: 'CNC' })).ok).toBe(true)
    expect(overrideCalls).toBe(0)
    const old = currentTools.update_selection!
    view.rerender({ ...options, sessionId: 'new-session', clientTools: { update_selection: () => 'replacement' } })
    expect(JSON.parse(await old({ action: 'clear' })).ok).toBe(false)
    expect(changed).toBe(1)
    await prepareVoice(view)
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('replacement')
  })

  test('an explicit stop prevents a retained extra tool from changing selection', async () => {
    let changed = false
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: { update_selection: () => { changed = true; return 'done' } } }))
    await prepareVoice(view)
    const retained = currentTools.update_selection!
    await act(async () => { await view.result.current.stop() })
    expect(JSON.parse(await retained({ action: 'clear' })).ok).toBe(false)
    expect(changed).toBe(false)
  })

  test('full failed tool responses reach the latest handler but never a replacement session', async () => {
    let release!: (value: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const old: unknown[] = [], latest: unknown[] = []
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: {
      ...options, onToolResponse: response => { old.push(response) },
    } as BuildingVoiceOptions })
    await prepareVoice(view)
    const retained = currentTools.find!
    const pending = retained({ query: 'Press' })
    await Promise.resolve(); await Promise.resolve()
    view.rerender({ ...options, onToolResponse: response => { latest.push(response) } })
    const failed = { ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: [{ id: 'press-1', name: 'Press 1' }] } }
    release(new Response(JSON.stringify(failed), { status: 200 }))
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(old).toEqual([])
    expect(latest).toMatchObject([failed])
    const later = retained({ query: 'Old session request' })
    await Promise.resolve(); await Promise.resolve()
    view.rerender({ ...options, sessionId: 'new-session', onToolResponse: response => { latest.push(response) } })
    release(new Response(JSON.stringify(failed), { status: 200 }))
    expect(JSON.parse(await later).ok).toBe(false)
    expect(latest).toMatchObject([failed])
  })

  test('a delayed find cannot repaint or publish trace into a restarted conversation in the same session', async () => {
    let release!: (value: Response) => void
    let lookups = 0
    const found = { ok: true, speech: 'CNC found.', result: { id: 'cnc' }, display: { kind: 'highlight', asset_ids: ['cnc'] } }
    fetchMock.fetch = async input => String(input).startsWith('/api/voice/token') ? token()
      : ++lookups === 1 ? new Promise<Response>(resolve => { release = resolve }) : new Response(JSON.stringify(found))
    const displays: unknown[] = [], responses: unknown[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) }, onToolResponse: response => { responses.push(response) } }))
    await prepareVoice(view)
    const pending = currentTools.find!({ query: 'CNC' })
    await Promise.resolve(); await Promise.resolve()
    await act(async () => { await view.result.current.stop() })
    await settleClosing()
    await prepareVoice(view)
    await act(async () => { currentOnConnect?.() })
    release(new Response(JSON.stringify(found)))
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(displays).toEqual([])
    expect(responses).toEqual([])
    expect(JSON.parse(await currentTools.find!({ query: 'CNC' })).ok).toBe(true)
    expect(displays).toEqual([found.display])
    expect(responses).toMatchObject([found])
  })

  test('an accepted typed turn appears without a provider echo, and a matching echo reuses its ID', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await act(async () => { currentOnConnect?.(); expect(view.result.current.sendText('Find the CNC mill')).toBe(true) })
    expect(view.result.current.messages.map(message => message.text)).toEqual(['Find the CNC mill'])
    const typedId = view.result.current.messages[0]!.id
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Find the CNC mill', event_id: 200 }) })
    expect(view.result.current.messages).toEqual([{ id: typedId, role: 'user', text: 'Find the CNC mill' }])
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Find the CNC mill', event_id: 201 }) })
    expect(view.result.current.messages.length).toBe(2)
    expect(view.result.current.messages[1]!.id).not.toBe(typedId)
  })

  test('two identical typed submissions remain two turns while their individual echoes deduplicate', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await act(async () => { currentOnConnect?.(); view.result.current.sendText('Next'); view.result.current.sendText('Next') })
    expect(view.result.current.messages.length).toBe(2)
    const ids = view.result.current.messages.map(message => message.id)
    await act(async () => {
      currentOnMessage?.({ role: 'user', message: 'Next', event_id: 300 })
      currentOnMessage?.({ role: 'user', message: 'Next', event_id: 301 })
      currentOnMessage?.({ role: 'user', message: 'Next', event_id: 301 })
    })
    expect(view.result.current.messages.map(message => message.id)).toEqual(ids)
  })

  test('repeated spoken turns after an agent reply or the echo window are not discarded', async () => {
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await act(async () => {
      currentOnConnect?.(); view.result.current.sendText('Next')
      currentOnMessage?.({ role: 'agent', message: 'Continue ahead.', event_id: 400 })
      currentOnMessage?.({ role: 'user', message: 'Next', event_id: 401 })
    })
    expect(view.result.current.messages.map(message => message.role)).toEqual(['user', 'agent', 'user'])
    const original = Date.now
    try {
      const now = original()
      await act(async () => { view.result.current.sendText('Again') })
      Date.now = () => now + 5000
      await act(async () => { currentOnMessage?.({ role: 'user', message: 'Again', event_id: 402 }) })
      expect(view.result.current.messages.filter(message => message.text === 'Again').length).toBe(2)
    } finally { Date.now = original }
  })

  test('typed pending echoes do not cross sessions, and rejected sends never create transcript rows', async () => {
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    await startVoice(view)
    await act(async () => { currentOnConnect?.(); view.result.current.sendText('Old typed input') })
    const oldMessage = currentOnMessage
    view.rerender({ ...options, sessionId: 'fresh-session' })
    await act(async () => { oldMessage?.({ role: 'user', message: 'Old typed input', event_id: 500 }); currentOnConnect?.() })
    expect(view.result.current.messages).toEqual([])
    await startVoice(view)
    await act(async () => { currentOnConnect?.() })
    sendFailure = true
    await act(async () => { expect(view.result.current.sendText('Rejected')).toBe(false) })
    expect(view.result.current.messages).toEqual([])
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Old typed input', event_id: 501 }) })
    expect(view.result.current.messages).toHaveLength(1)
  })

  test('provider event IDs reused after reconnect do not overwrite the previous call’s turns', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await startVoice(view)
    await startVoice(view)
    await act(async () => { currentOnConnect?.(); currentOnMessage?.({ role: 'user', message: 'Previous call', event_id: 1 }); await view.result.current.stop() })
    await settleClosing()
    await act(async () => { await view.result.current.start(); currentOnConnect?.(); currentOnMessage?.({ role: 'user', message: 'New call', event_id: 1 }) })
    expect(view.result.current.messages.map(message => message.text)).toEqual(['Previous call', 'New call'])
    expect(new Set(view.result.current.messages.map(message => message.id)).size).toBe(2)
  })
})

describe('voice transcript registration', () => {
  const turnResponse = (turnId: string) => new Response(JSON.stringify({ turn_id: turnId }))

  test('only real user transcript events create a turn, and tools wait for its ID', async () => {
    const registrations: unknown[] = [], tools: unknown[] = []
    let register!: (response: Response) => void
    fetchMock.fetch = async (url, init) => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') {
        registrations.push(JSON.parse(String(init?.body)))
        return new Promise(resolve => { register = resolve })
      }
      expect(url).toBe('/api/agent/tools/search_entities')
      tools.push(JSON.parse(String(init?.body)))
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start() })
    expect(JSON.parse(await currentTools.find!()).ok).toBe(false)
    const ignoredEvents = ['ai', 'assistant', 'system', 'context'].map(source => ({ ...userMessage('Confirm this edit'), source }))
    await act(async () => {
      for (const event of ignoredEvents) currentOnMessage?.(event)
      currentOnMessage?.({ ...userMessage(), message: '   ' })
    })
    expect(registrations).toEqual([])
    await act(async () => { currentOnMessage?.(userMessage('Find every pump')) })
    const pending = currentTools.search_entities!({ query: 'pump' })
    await Promise.resolve()
    expect(tools).toEqual([])
    await act(async () => { register(turnResponse('registered-user-turn')); await pending })
    expect(registrations).toEqual([{ session_id: options.sessionId, message: 'Find every pump' }])
    expect(tools).toEqual([{ session_id: options.sessionId, turn_id: 'registered-user-turn', args: { query: 'pump' } }])
  })

  test.each(['transport', 'http', 'malformed'])('a %s registration failure cannot reuse the previous turn', async failure => {
    let registrations = 0, toolRequests = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') {
        if (++registrations === 1) return turnResponse('previous-turn')
        if (failure === 'transport') throw new Error('Internal registration details')
        if (failure === 'http') return new Response('{}', { status: 503 })
        return new Response(JSON.stringify({ turn_id: 123 }))
      }
      toolRequests++
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    expect(JSON.parse(await currentTools.find!()).ok).toBe(true)
    await act(async () => { currentOnMessage?.(userMessage('Find another pump')) })
    expect(JSON.parse(await currentTools.find!()).ok).toBe(false)
    expect(toolRequests).toBe(1)
    expect(view.result.current.error).toBe('Your voice request could not be registered. Say it again or use text chat.')
  })

  test.each(['stop', 'disconnect', 'error', 'session', 'agent', 'unmount'] as const)('a transcript pending during %s cannot dispatch a tool or accept more transcripts', async cancellation => {
    let finish!: (response: Response) => void
    let registrations = 0, toolRequests = 0
    let signal: AbortSignal | null | undefined
    fetchMock.fetch = async (url, init) => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') {
        registrations++
        signal = init?.signal
        return new Promise(resolve => { finish = resolve })
      }
      toolRequests++
      return instruction()
    }
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    const retiredMessage = currentOnMessage
    const pending = currentTools.commit_edit!({ proposal_id: 'proposal-after-cancel' })
    if (cancellation === 'stop') await act(async () => { await view.result.current.stop() })
    if (cancellation === 'disconnect') await act(async () => { currentOnDisconnect?.() })
    if (cancellation === 'error') await act(async () => { currentOnError?.() })
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'new-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    retiredMessage?.(userMessage('Do not register this retired transcript'))
    await act(async () => { finish(turnResponse('cancelled-turn')); await pending })
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(signal?.aborted).toBe(true)
    expect(registrations).toBe(1)
    expect(toolRequests).toBe(0)
  })

  test('callbacks and tools from a stopped connection cannot use the replacement connection', async () => {
    let registrations = 0, toolRequests = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return turnResponse(`turn-${++registrations}`)
      toolRequests++
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    const retiredMessage = currentOnMessage, retiredError = currentOnError, retiredDisconnect = currentOnDisconnect
    const retiredTools = currentTools
    await act(async () => { await view.result.current.stop() })
    await settleClosing()
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage('New request')) })
    await act(async () => { retiredMessage?.(userMessage('Old callback')); retiredError?.(); retiredDisconnect?.() })
    expect(JSON.parse(await retiredTools.find!()).ok).toBe(false)
    expect(JSON.parse(await currentTools.find!()).ok).toBe(true)
    expect(registrations).toBe(2)
    expect(toolRequests).toBe(1)
    expect(view.result.current.error).toBeNull()
  })

  test.each(['find', 'next_step', 'commit_edit'] as const)('a new user message supersedes an in-flight %s result', async name => {
    let finish!: (response: Response) => void
    let turns = 0
    const displays: ToolDisplay[] = []
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return turnResponse(`turn-${++turns}`)
      return new Promise(resolve => { finish = resolve })
    }
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: value => { displays.push(value) } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    const pending = currentTools[name]!({ proposal_id: 'existing-proposal' })
    await act(async () => { await Promise.resolve() })
    await act(async () => { currentOnMessage?.(userMessage('A new request')) })
    finish(instruction())
    const result = JSON.parse(await pending)
    expect(result.error.code).toBe('version_conflict')
    expect(displays).toEqual([])
  })

  test('an older registration cannot replace a newer turn even when abort is ignored', async () => {
    const finishes: ((response: Response) => void)[] = []
    const toolTurns: string[] = []
    fetchMock.fetch = async (url, init) => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return new Promise(resolve => { finishes.push(resolve) })
      toolTurns.push(JSON.parse(String(init?.body)).turn_id)
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage('Old request')) })
    const oldTool = currentTools.find!()
    await act(async () => { currentOnMessage?.(userMessage('New request')); finishes[1]!(turnResponse('new-turn')) })
    await act(async () => { finishes[0]!(turnResponse('old-turn')); await oldTool })
    expect(JSON.parse(await oldTool).ok).toBe(false)
    expect(JSON.parse(await currentTools.find!()).ok).toBe(true)
    expect(toolTurns).toEqual(['new-turn'])
    expect(view.result.current.error).toBeNull()
  })
})


describe('desk UI tool turn policy', () => {
  const registered = (turnId: string) => new Response(JSON.stringify({ turn_id: turnId }))
  const conflict = { ok: false, speech: 'Use a new user turn.', error: { code: 'version_conflict', message: 'The turn is no longer current.' } }

  test('validates the current turn before each UI action with encoded IDs and no cache', async () => {
    const requests: { url: string; cache: RequestCache | undefined }[] = []
    let changes = 0
    const turnId = 'turn/with?reserved&characters'
    const sessionId = 'session/with?reserved&characters'
    fetchMock.fetch = async (url, init) => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return registered(turnId)
      requests.push({ url: String(url), cache: init?.cache })
      expect(changes).toBe(requests.length - 1)
      return registered(turnId)
    }
    const view = renderHook(() => useBuildingVoice({ ...options, sessionId, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('changed')
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('changed')
    expect(requests).toEqual(Array(2).fill({
      url: `/api/agent/turns/${encodeURIComponent(turnId)}?session_id=${encodeURIComponent(sessionId)}`, cache: 'no-store',
    }))
    expect(changes).toBe(2)
  })

  test('remote supersession blocks UI actions and clears cached authority until a new user turn', async () => {
    let changes = 0, registrations = 0, validations = 0, toolRequests = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return registered(`turn-${++registrations}`)
      if (String(url).startsWith('/api/agent/turns/')) {
        validations++
        return registrations === 1 ? new Response(JSON.stringify(conflict), { status: 409 }) : registered('turn-2')
      }
      toolRequests++
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    expect(JSON.parse(await currentTools.update_selection!({ action: 'clear' })).error.code).toBe('version_conflict')
    expect(JSON.parse(await currentTools.update_selection!({ action: 'clear' })).ok).toBe(false)
    expect(JSON.parse(await currentTools.find!()).ok).toBe(false)
    expect({ changes, validations, toolRequests }).toEqual({ changes: 0, validations: 1, toolRequests: 0 })
    await act(async () => { currentOnMessage?.(userMessage('A fresh request')) })
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('changed')
    expect(changes).toBe(1)
  })

  test.each([200, 409])('a backend conflict from HTTP %d retires cached authority and preserves its actual failure', async status => {
    let changes = 0, validations = 0, toolRequests = 0
    const outcomes: unknown[] = []
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return registered('old-turn')
      if (String(url).startsWith('/api/agent/turns/')) { validations++; return registered('old-turn') }
      toolRequests++
      return new Response(JSON.stringify(conflict), { status })
    }
    const view = renderHook(() => useBuildingVoice({ ...options, onToolResponse: response => { outcomes.push(response) }, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    expect(JSON.parse(await currentTools.find!())).toEqual(conflict)
    expect(outcomes).toMatchObject([conflict])
    expect(JSON.parse(await currentTools.update_selection!({ action: 'clear' })).ok).toBe(false)
    expect(JSON.parse(await currentTools.find!()).ok).toBe(false)
    expect({ changes, validations, toolRequests }).toEqual({ changes: 0, validations: 0, toolRequests: 1 })
  })

  test.each(['network', 'http', 'malformed', 'wrong_turn', 'invalid_json'])('a %s validation failure blocks the UI handler', async failure => {
    let changes = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return registered('current-turn')
      if (failure === 'network') throw new Error('private network details')
      if (failure === 'http') return new Response('{}', { status: 503 })
      if (failure === 'malformed') return new Response('{}')
      if (failure === 'invalid_json') return new Response('not json')
      return registered('another-turn')
    }
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    expect(JSON.parse(await currentTools.update_selection!({ action: 'clear' })).error.code).toBe('not_available')
    expect(changes).toBe(0)
  })

  test.each(['turn', 'stop', 'session', 'agent', 'unmount'] as const)('a UI validation pending during %s cannot run the handler', async cancellation => {
    let release!: (response: Response) => void
    let changes = 0
    const initialProps: BuildingVoiceOptions = {
      ...options, clientTools: { update_selection: () => { changes++; return 'changed' } },
    }
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps })
    await prepareVoice(view)
    const configuredFetch = fetchMock.fetch
    fetchMock.fetch = async (url, init) => String(url).startsWith('/api/agent/turns/')
      ? new Promise<Response>(resolve => { release = resolve }) : configuredFetch(url, init)
    const pending = currentTools.update_selection!({ action: 'clear' })
    await act(async () => { await Promise.resolve() })
    if (cancellation === 'turn') await act(async () => { currentOnMessage?.(userMessage('Keep the selection')) })
    if (cancellation === 'stop') await act(async () => { await view.result.current.stop() })
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session', clientTools: {} })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin', clientTools: {} })
    if (cancellation === 'unmount') view.unmount()
    release(registered('offline-user-turn'))
    expect(JSON.parse(await pending).error.code).toBe('version_conflict')
    expect(changes).toBe(0)
  })

  test('an old validation conflict cannot revoke a newer registered user turn', async () => {
    let release!: (response: Response) => void
    let changes = 0, registrations = 0, validations = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return registered(`turn-${++registrations}`)
      return ++validations === 1 ? new Promise<Response>(resolve => { release = resolve }) : registered('turn-2')
    }
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage()) })
    const pending = currentTools.update_selection!({ action: 'clear' })
    await act(async () => { await Promise.resolve() })
    await act(async () => { currentOnMessage?.(userMessage('Select the pump instead')) })
    release(new Response(JSON.stringify(conflict), { status: 409 }))
    expect(JSON.parse(await pending).error.code).toBe('version_conflict')
    expect(await currentTools.update_selection!({ action: 'replace', items: 'pump' })).toBe('changed')
    expect(changes).toBe(1)
  })

  test('a newer user turn during validation JSON parsing blocks the UI handler', async () => {
    let release!: (body: unknown) => void
    let changes = 0
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await prepareVoice(view)
    const configuredFetch = fetchMock.fetch
    const validation = new Response()
    validation.json = () => new Promise(resolve => { release = resolve })
    fetchMock.fetch = async (url, init) => String(url).startsWith('/api/agent/turns/')
      ? validation : configuredFetch(url, init)
    const pending = currentTools.update_selection!({ action: 'clear' })
    await act(async () => { await Promise.resolve() })
    await act(async () => { currentOnMessage?.(userMessage('Keep the selection')) })
    release({ turn_id: 'offline-user-turn' })
    expect(JSON.parse(await pending).error.code).toBe('version_conflict')
    expect(changes).toBe(0)
  })

  test('context and role-only messages cannot authorize a UI action', async () => {
    let changes = 0
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnConnect?.() })
    view.result.current.sendContext('Selected parts include the pump.')
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Clear selection' }) })
    expect(JSON.parse(await currentTools.update_selection!({ action: 'clear' })).ok).toBe(false)
    expect(changes).toBe(0)
  })

  test('failed registration cannot reuse an old user turn for a UI action', async () => {
    let changes = 0, registrations = 0, validations = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') return ++registrations === 1
        ? new Response(JSON.stringify({ turn_id: 'old-turn' })) : new Response('{}', { status: 503 })
      validations++
      return new Response(JSON.stringify({ turn_id: 'old-turn' }))
    }
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      focus_floor: () => { changes++; return 'shown' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage('Show ground floor')) })
    expect(await currentTools.focus_floor!({ floor: 'ground' })).toBe('shown')
    await act(async () => { currentOnMessage?.(userMessage('Show upper floor')) })
    expect(JSON.parse(await currentTools.focus_floor!({ floor: 'upper' })).ok).toBe(false)
    expect(changes).toBe(1)
    expect(validations).toBe(1)
  })

  test('a newer turn blocks a UI action waiting for older registration', async () => {
    const registrations: ((response: Response) => void)[] = []
    let changes = 0
    fetchMock.fetch = async url => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (String(url).startsWith('/api/agent/turns/')) return new Response(JSON.stringify({ turn_id: 'new-turn' }))
      return new Promise(resolve => { registrations.push(resolve) })
    }
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await act(async () => { await view.result.current.start(); currentOnMessage?.(userMessage('Clear parts')) })
    const pending = currentTools.update_selection!({ action: 'clear' })
    await act(async () => {
      currentOnMessage?.(userMessage('Keep the pump'))
      registrations[0]!(new Response(JSON.stringify({ turn_id: 'old-turn' })))
      registrations[1]!(new Response(JSON.stringify({ turn_id: 'new-turn' })))
      await pending
    })
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(changes).toBe(0)
    expect(await currentTools.update_selection!({ action: 'replace', items: ['pump'] })).toBe('changed')
    expect(changes).toBe(1)
  })

  test('retained UI tools cannot act in a replacement call for the same session', async () => {
    let changes = 0
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: {
      update_selection: () => { changes++; return 'changed' },
    } }))
    await prepareVoice(view)
    const retired = currentTools.update_selection!
    await act(async () => { await view.result.current.stop() })
    await settleClosing()
    await prepareVoice(view)
    expect(JSON.parse(await retired({ action: 'clear' })).ok).toBe(false)
    expect(changes).toBe(0)
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('changed')
  })

  test('typed submissions register once, work without an echo and do not re-register an echo', async () => {
    const registrations: unknown[] = [], toolTurns: unknown[] = []
    fetchMock.fetch = async (url, init) => {
      if (String(url).startsWith('/api/voice/token')) return token()
      if (url === '/api/agent/turns') {
        registrations.push(JSON.parse(String(init?.body)))
        return new Response(JSON.stringify({ turn_id: 'typed-user-turn' }))
      }
      toolTurns.push(JSON.parse(String(init?.body)))
      return instruction()
    }
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { await view.result.current.start(); currentOnConnect?.(); view.result.current.sendText('Find the pump') })
    expect(JSON.parse(await currentTools.find!({ query: 'pump' })).ok).toBe(true)
    await act(async () => {
      currentOnMessage?.(userMessage('Find the pump'))
      currentOnMessage?.(userMessage('Find the pump'))
    })
    expect(registrations).toEqual([{ session_id: options.sessionId, message: 'Find the pump' }])
    expect(toolTurns).toEqual([{ session_id: options.sessionId, turn_id: 'typed-user-turn', args: { query: 'pump' } }])
    expect(view.result.current.messages).toHaveLength(1)
    sendFailure = true
    await act(async () => { expect(view.result.current.sendText('Rejected input')).toBe(false) })
    expect(registrations).toHaveLength(1)
  })
})
