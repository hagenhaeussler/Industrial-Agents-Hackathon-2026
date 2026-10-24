import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test'
import { Window } from 'happy-dom'
import { act, cleanup, renderHook } from '@testing-library/react'
import type { BuildingVoiceOptions } from './useBuildingVoice'
import type { Fetcher, ToolDisplay } from './clientTools'

const starts: unknown[] = []
const contexts: string[] = []
let stops = 0
let currentTools: Record<string, (args?: unknown) => Promise<string>>
const conversation = {
  status: 'disconnected', isSpeaking: false,
  startSession: (options: unknown) => { starts.push(options) },
  endSession: async () => { stops++ },
  sendContextualUpdate: (text: string) => { contexts.push(text) },
}
mock.module('@elevenlabs/react', () => ({ useConversation: (options: { clientTools: typeof currentTools }) => {
  currentTools = options.clientTools
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
  starts.length = 0; contexts.length = 0; stops = 0; conversation.status = 'disconnected'
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
    expect(starts).toEqual([{ conversationToken: 'offline-test-token' }])
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
})

describe('voice tool lifecycle', () => {
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

  test('stop does not turn a committed admin edit into failure', async () => {
    let release!: (response: Response) => void
    fetchMock.fetch = async () => new Promise<Response>(resolve => { release = resolve })
    const displays: ToolDisplay[] = []
    const view = renderHook(() => useBuildingVoice({ ...options, agent: 'admin', onDisplay: display => { displays.push(display) } }))
    const pending = currentTools.commit_edit!({ proposal_id: 'offline-proposal' })
    await act(async () => { await view.result.current.stop() })
    release(new Response(JSON.stringify({ ok: true, speech: 'Lift closed.', result: { event_id: 'evt-offline' }, display: { kind: 'edit_committed' } }), { status: 200 }))
    expect(JSON.parse(await pending).ok).toBe(true)
    expect(displays).toEqual([{ kind: 'edit_committed' }])
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
