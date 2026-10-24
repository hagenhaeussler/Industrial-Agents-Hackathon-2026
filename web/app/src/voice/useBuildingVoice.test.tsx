import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test'
import { Window } from 'happy-dom'
import { act, cleanup, renderHook } from '@testing-library/react'
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
  startSession: (options: unknown) => { lifecycle.push('start'); starts.push(options) },
  endSession: async () => { lifecycle.push('end'); stops++ },
  sendContextualUpdate: (text: string) => { contexts.push(text) },
  sendUserMessage: (text: string) => { if (sendFailure) throw new Error('secret-provider-token'); userMessages.push(text) },
  setMuted: (value: boolean) => { if (muteFailure) throw new Error('secret-provider-token'); conversation.isMuted = value; muteChanges.push(value) },
  getInputVolume: () => { meterReads++; return inputVolume },
  getOutputVolume: () => { meterReads++; return outputVolume },
}
mock.module('@elevenlabs/react', () => ({ useConversation: (options: Callbacks) => {
  currentTools = options.clientTools
  currentOnError = options.onError
  currentOnConnect = options.onConnect
  currentOnStatusChange = options.onStatusChange
  currentOnDisconnect = options.onDisconnect
  currentOnMessage = options.onMessage
  return conversation
} }))

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
    expect(starts).toEqual([{ conversationToken: 'offline-test-token', connectionType: 'webrtc' }])
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
    const view = renderHook((props: BuildingVoiceOptions) => useBuildingVoice(props), { initialProps: options })
    const retiredError = currentOnError
    if (cancellation === 'session') view.rerender({ ...options, sessionId: 'replacement-session' })
    if (cancellation === 'agent') view.rerender({ ...options, agent: 'admin' })
    if (cancellation === 'unmount') view.unmount()
    await act(async () => { retiredError?.() })
    expect(view.result.current.error).toBeNull()
    expect(starts).toEqual([])
  })
})

describe('voice tool lifecycle', () => {
  test('an SDK connection failure suppresses a pending instruction', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) } }))
    const pending = currentTools.next_step!()
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
    const pending = currentTools.next_step!()
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
    const pending = currentTools.next_step!()
    view.rerender({ ...options, onDisplay: () => { throw new Error('Stale display after handler recreation') } })
    expect(JSON.parse(await currentTools.next_step!()).error.code).toBe('no_route')
    release(instruction())
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(displays).toEqual([])
  })

  test('context updates leave a sole instruction valid', async () => {
    conversation.status = 'connected'
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) } }))
    const pending = currentTools.next_step!()
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
    const pending = currentTools.commit_edit!({ proposal_id: 'offline-proposal' })
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
    const pending = currentTools.commit_edit!({ proposal_id: 'offline-session-switch-proposal' })
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
    expect(starts).toEqual([{ conversationToken: 'offline-test-token', connectionType: 'webrtc' }])
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
    await act(async () => { currentOnDisconnect?.({ reason, message: 'provider://secret-token' }) })
    expect(view.result.current.error).toBe(reason === 'error' ? 'The voice connection could not start. Check your connection and try again.' : 'The voice conversation ended. Tap to reconnect.')
    expect(view.result.current.error).not.toContain('secret-token')
  })

  test('explicit stop ignores late disconnect, errors, messages and connection callbacks', async () => {
    const view = renderHook(() => useBuildingVoice(options))
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
    await act(async () => { currentOnError?.('hidden-provider-token', new DOMException('hidden-provider-token', name)) })
    expect(view.result.current.error).toContain(text)
    expect(view.result.current.error).not.toContain('hidden-provider-token')
  })

  test('captures real speaker turns, replaces duplicate response IDs and retains at most 60', async () => {
    const view = renderHook(() => useBuildingVoice(options))
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
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('selection changed')
    expect(JSON.parse(await currentTools.find!({ query: 'CNC' })).ok).toBe(true)
    expect(overrideCalls).toBe(0)
    const old = currentTools.update_selection!
    view.rerender({ ...options, sessionId: 'new-session', clientTools: { update_selection: () => 'replacement' } })
    expect(JSON.parse(await old({ action: 'clear' })).ok).toBe(false)
    expect(changed).toBe(1)
    expect(await currentTools.update_selection!({ action: 'clear' })).toBe('replacement')
  })

  test('an explicit stop prevents a retained extra tool from changing selection', async () => {
    let changed = false
    const view = renderHook(() => useBuildingVoice({ ...options, clientTools: { update_selection: () => { changed = true; return 'done' } } }))
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
    const retained = currentTools.find!
    const pending = retained({ query: 'Press' })
    view.rerender({ ...options, onToolResponse: response => { latest.push(response) } })
    const failed = { ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: [{ id: 'press-1', name: 'Press 1' }] } }
    release(new Response(JSON.stringify(failed), { status: 200 }))
    expect(JSON.parse(await pending).ok).toBe(false)
    expect(old).toEqual([])
    expect(latest).toEqual([failed])
    const later = retained({ query: 'Old session request' })
    view.rerender({ ...options, sessionId: 'new-session', onToolResponse: response => { latest.push(response) } })
    release(new Response(JSON.stringify(failed), { status: 200 }))
    expect(JSON.parse(await later).ok).toBe(false)
    expect(latest).toEqual([failed])
  })

  test('a delayed find cannot repaint or publish trace into a restarted conversation in the same session', async () => {
    let release!: (value: Response) => void
    let lookups = 0
    const found = { ok: true, speech: 'CNC found.', result: { id: 'cnc' }, display: { kind: 'highlight', asset_ids: ['cnc'] } }
    fetchMock.fetch = async input => String(input).startsWith('/api/voice/token') ? token()
      : ++lookups === 1 ? new Promise<Response>(resolve => { release = resolve }) : new Response(JSON.stringify(found))
    const displays: unknown[] = [], responses: unknown[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, onDisplay: display => { displays.push(display) }, onToolResponse: response => { responses.push(response) } }))
    const pending = currentTools.find!({ query: 'CNC' })
    await act(async () => { await view.result.current.stop(); await view.result.current.start(); currentOnConnect?.() })
    release(new Response(JSON.stringify(found)))
    expect(JSON.parse(await pending).ok).toBe(true)
    expect(displays).toEqual([])
    expect(responses).toEqual([])
    expect(JSON.parse(await currentTools.find!({ query: 'CNC' })).ok).toBe(true)
    expect(displays).toEqual([found.display])
    expect(responses).toEqual([found])
  })

  test('an accepted typed turn appears without a provider echo, and a matching echo reuses its ID', async () => {
    const view = renderHook(() => useBuildingVoice(options))
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
    await act(async () => { currentOnConnect?.(); view.result.current.sendText('Old typed input') })
    const oldMessage = currentOnMessage
    view.rerender({ ...options, sessionId: 'fresh-session' })
    await act(async () => { oldMessage?.({ role: 'user', message: 'Old typed input', event_id: 500 }); currentOnConnect?.() })
    expect(view.result.current.messages).toEqual([])
    sendFailure = true
    await act(async () => { expect(view.result.current.sendText('Rejected')).toBe(false) })
    expect(view.result.current.messages).toEqual([])
    await act(async () => { currentOnMessage?.({ role: 'user', message: 'Old typed input', event_id: 501 }) })
    expect(view.result.current.messages).toHaveLength(1)
  })

  test('provider event IDs reused after reconnect do not overwrite the previous call’s turns', async () => {
    fetchMock.fetch = async () => token()
    const view = renderHook(() => useBuildingVoice(options))
    await act(async () => { currentOnConnect?.(); currentOnMessage?.({ role: 'user', message: 'Previous call', event_id: 1 }); await view.result.current.stop() })
    await act(async () => { await view.result.current.start(); currentOnConnect?.(); currentOnMessage?.({ role: 'user', message: 'New call', event_id: 1 }) })
    expect(view.result.current.messages.map(message => message.text)).toEqual(['Previous call', 'New call'])
    expect(new Set(view.result.current.messages.map(message => message.id)).size).toBe(2)
  })
})
