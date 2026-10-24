import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useConversation } from '@elevenlabs/react'
import { createClientTools, createNavigationRequestGuard, serializeToolResponse } from './clientTools'
import type { ToolDisplay, ToolResponse } from './clientTools'

const VOICE_UNAVAILABLE = 'Voice is unavailable. Please use text chat.'
const CONNECTION_FAILED = 'The voice connection could not start. Check your connection and try again.'
const VOICE_LIMIT = 'Voice has reached its provider limit. Try again later or use text chat.'
const VOICE_CLOSING = 'Voice is still closing. Try again in a moment.'
const VOICE_RELOAD = 'Voice could not finish closing. Reload this page before starting again.'
const TRANSCRIPT_UNAVAILABLE = 'Your voice request could not be registered. Say it again or use text chat.'
const TYPED_ECHO_MS = 3000
export type VoiceMessage = { id: string; role: 'user' | 'agent'; text: string }
export type VoiceClientTool = (args: Record<string, unknown>) => Promise<string> | string
export type BuildingVoiceOptions = {
  agent: 'navigator' | 'admin'
  sessionId: string
  onDisplay?: (display: ToolDisplay, response: ToolResponse) => void
  onToolResponse?: (response: ToolResponse) => void
  clientTools?: Record<string, VoiceClientTool>
}

/** Classify known failures; never show a provider message, URL or token verbatim. */
function safeError(message?: unknown, detail?: unknown): string {
  const error = detail instanceof Error ? detail : message instanceof Error ? message : null
  const name = error?.name
  const text = [typeof message === 'string' ? message : '', error?.message ?? ''].join(' ')
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || /permission.{0,15}(denied|dismissed)|notallowederror/i.test(text)) {
    return 'Microphone access was not allowed. Allow it in your browser’s site settings and try again.'
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') return 'No microphone was found. Connect one and try again.'
  if (name === 'NotReadableError' || name === 'TrackStartError') return 'The microphone is unavailable. Close other audio apps and try again.'
  if (/quota|daily.{0,10}limit|concurren|too many|rate.{0,10}limit|capacity|credits|balance/i.test(text)) return VOICE_LIMIT
  if (/rtc|ice connection|network|socket|handshake|connection/i.test(text)) return CONNECTION_FAILED
  return VOICE_UNAVAILABLE
}

/** Must be rendered inside ConversationProvider; real ElevenLabs audio and tools share this session. */
export function useBuildingVoice({ agent, sessionId, onDisplay, onToolResponse, clientTools }: BuildingVoiceOptions) {
  const display = useRef(onDisplay)
  display.current = onDisplay
  const responseHandler = useRef(onToolResponse)
  responseHandler.current = onToolResponse
  const additionalTools = useRef(clientTools)
  additionalTools.current = clientTools
  const sdkEnd = useRef<(() => void) | null>(null)
  const scope = useMemo(() => {
    const state: {
      active: boolean; acceptingMessages: boolean; starting: boolean; attempt: number;
      controller: AbortController | null; transcriptController: AbortController | null; turn: Promise<string> | null;
      sdkStarted: boolean; sdkAttempt: number | null; userStopped: boolean; phase: string | null;
      serial: number; messageIds: Map<string, string>; userEvents: Map<string, string>;
      pendingTyped: { id: string; text: string; at: number }[];
      startTimer: ReturnType<typeof setTimeout> | null; closing: boolean; closeTimedOut: boolean;
      closeTimer: ReturnType<typeof setTimeout> | null; settledTimer: ReturnType<typeof setTimeout> | null;
    } = { active: true, acceptingMessages: false, starting: false, attempt: 0,
      controller: null, transcriptController: null, turn: null, sdkStarted: false, sdkAttempt: null,
      userStopped: false, phase: null, serial: 0, messageIds: new Map(), userEvents: new Map(), pendingTyped: [],
      startTimer: null, closing: false, closeTimedOut: false, closeTimer: null, settledTimer: null }
    const emptyMessages: VoiceMessage[] = []
    return { state, emptyMessages, navigation: createNavigationRequestGuard(() => state.active), turns: createNavigationRequestGuard() }
  }, [agent, sessionId])
  const [failure, setFailure] = useState<{ scope: typeof scope; message: string | null }>({ scope, message: null })
  const [phase, setPhase] = useState<{ scope: typeof scope; status: string | null }>({ scope, status: null })
  const [transcript, setTranscript] = useState<{ scope: typeof scope; messages: VoiceMessage[] }>({ scope, messages: [] })
  const [levels, setLevels] = useState({ scope, input: 0, output: 0 })
  const error = failure.scope === scope ? failure.message : null
  const messages = transcript.scope === scope ? transcript.messages : scope.emptyMessages
  const changePhase = useCallback((status: string) => {
    scope.state.phase = status
    setPhase({ scope, status })
  }, [scope])
  const showError = useCallback((message: string | null) => setFailure({ scope, message }), [scope])
  const finishClosing = useCallback(() => {
    if (scope.state.closeTimer) clearTimeout(scope.state.closeTimer)
    scope.state.closeTimer = null
    // Provider clears its in-flight promise in a following microtask. Release
    // retries in the next task, after that lock has actually been released.
    if (scope.state.settledTimer) clearTimeout(scope.state.settledTimer)
    scope.state.settledTimer = setTimeout(() => {
      scope.state.settledTimer = null
      if (!scope.state.active) return
      const timedOut = scope.state.closeTimedOut
      scope.state.closing = false
      scope.state.closeTimedOut = false
      scope.state.sdkStarted = false
      if (timedOut) changePhase('disconnected')
      setFailure(previous => previous.scope === scope && (previous.message === VOICE_CLOSING || previous.message === VOICE_RELOAD)
        ? { scope, message: null } : previous)
    }, 0)
  }, [scope, changePhase])
  const closeSdk = useCallback(() => {
    if (!scope.state.closing) {
      scope.state.closing = true
      scope.state.closeTimedOut = false
      scope.state.closeTimer = setTimeout(() => {
        scope.state.closeTimer = null
        if (!scope.state.active || !scope.state.closing) return
        scope.state.closeTimedOut = true
        changePhase('error')
        showError(VOICE_RELOAD)
      }, 10000)
    }
    sdkEnd.current?.()
  }, [scope, changePhase, showError])
  const invalidate = useCallback(() => {
    scope.state.attempt++
    scope.state.controller?.abort()
    scope.state.controller = null
    scope.state.transcriptController?.abort()
    scope.state.transcriptController = null
    scope.state.turn = null
    scope.state.acceptingMessages = false
    scope.state.starting = false
    scope.state.pendingTyped = []
    if (scope.state.startTimer) clearTimeout(scope.state.startTimer)
    scope.state.startTimer = null
    scope.navigation.invalidate()
  }, [scope])
  const registerTranscript = useCallback((message: string, attempt: number) => {
    if (!scope.state.active || !scope.state.acceptingMessages || scope.state.attempt !== attempt || !message.trim()) return
    scope.turns.invalidate()
    scope.navigation.invalidate()
    scope.state.transcriptController?.abort()
    const controller = new AbortController()
    scope.state.transcriptController = controller
    const current = () => scope.state.active && scope.state.acceptingMessages && scope.state.attempt === attempt
      && !controller.signal.aborted && scope.state.turn === turn
    const turn = (async () => {
      const response = await fetch('/api/agent/turns', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ session_id: sessionId, message: message.trim() }),
      })
      const body: unknown = await response.json()
      if (!current() || !response.ok || !body || typeof body !== 'object' || !('turn_id' in body)
        || typeof body.turn_id !== 'string' || !body.turn_id.trim()) throw new Error(TRANSCRIPT_UNAVAILABLE)
      return body.turn_id
    })()
    scope.state.turn = turn
    void turn.catch(() => { if (current()) showError(TRANSCRIPT_UNAVAILABLE) })
    showError(null)
  }, [sessionId, scope, showError])
  const toolsForAttempt = useCallback((attempt: number) => {
    const current = () => scope.state.active && scope.state.acceptingMessages && scope.state.attempt === attempt
    const getTurnId = async () => {
      const turn = scope.state.turn
      if (!current() || !turn) throw new Error(TRANSCRIPT_UNAVAILABLE)
      const id = await turn
      if (!current() || scope.state.turn !== turn) throw new Error(TRANSCRIPT_UNAVAILABLE)
      return id
    }
    const base = createClientTools({ sessionId, getTurnId, isActive: current,
      navigationGuard: scope.navigation, turnGuard: scope.turns,
      onResponse: response => { if (current()) responseHandler.current?.(response) },
      onDisplay: (payload, response) => { if (current()) display.current?.(payload, response) } })
    const extra = Object.fromEntries(Object.keys(additionalTools.current ?? {}).filter(name => !Object.hasOwn(base, name)).map(name => [name,
      async (args: Record<string, unknown>) => {
        const turn = scope.turns.capture()
        const active = () => current() && scope.turns.isCurrent(turn)
        const stale = () => serializeToolResponse({ ok: false, speech: 'Use the latest user request in the current voice conversation.', error: { code: 'version_conflict' } })
        if (!active()) return stale()
        try { await getTurnId() } catch { return serializeToolResponse({ ok: false, speech: TRANSCRIPT_UNAVAILABLE, error: { code: 'not_available' } }) }
        if (!active()) return stale()
        const handler = additionalTools.current?.[name]
        if (!handler) return serializeToolResponse({ ok: false, speech: 'This action is unavailable.', error: { code: 'not_available' } })
        try {
          const result = await handler(args)
          return active() ? result : stale()
        } catch { return serializeToolResponse({ ok: false, speech: 'The application action failed. Please try again.', error: { code: 'internal' } }) }
      },
    ]))
    return { ...extra, ...base }
  }, [sessionId, scope])
  const onError = useCallback((message?: unknown, detail?: unknown) => {
    if (!scope.state.active || scope.state.userStopped) return
    invalidate()
    changePhase('error')
    showError(safeError(message, detail))
  }, [invalidate, scope, changePhase, showError])
  const onConnect = useCallback(() => {
    if (!scope.state.active) return
    if (scope.state.userStopped || scope.state.closing) { closeSdk(); return }
    scope.state.starting = false
    scope.state.controller = null
    if (scope.state.startTimer) clearTimeout(scope.state.startTimer)
    scope.state.startTimer = null
    changePhase('connected')
    showError(null)
  }, [scope, changePhase, showError, closeSdk])
  const onStatusChange = useCallback(({ status }: { status: string }) => {
    if (!scope.state.active) return
    if (status === 'disconnected') {
      scope.state.sdkStarted = false
      if (scope.state.closing) finishClosing()
    }
  }, [scope, finishClosing])
  const onDisconnect = useCallback((details: { reason?: string; message?: string; closeReason?: string; closeCode?: number; context?: { reason?: string; code?: number } } = {}) => {
    if (!scope.state.active) return
    if (scope.state.closing) finishClosing()
    // Retry ends the failed SDK conversation before minting a new token. That
    // old teardown is asynchronous and must not abort the replacement fetch.
    if (details.reason === 'user' && scope.state.starting && !scope.state.userStopped) return
    const intentional = scope.state.userStopped || details.reason === 'user'
    invalidate()
    scope.state.sdkStarted = false
    changePhase('disconnected')
    if (intentional) showError(null)
    else {
      const reason = [details.message, details.closeReason, details.context?.reason].filter(Boolean).join(' ')
      const classified = details.closeCode === 4300 || details.context?.code === 4300 ? VOICE_LIMIT : safeError(reason)
      showError(classified === VOICE_UNAVAILABLE
        ? details.reason === 'error' ? CONNECTION_FAILED : 'The voice conversation ended. Tap to reconnect.'
        : classified)
    }
  }, [scope, invalidate, changePhase, showError, finishClosing])
  const onMessage = useCallback((payload: { role?: string; source?: string; message?: string; event_id?: number; response_id?: string }) => {
    if (!scope.state.active || !scope.state.acceptingMessages || scope.state.userStopped || !payload.message?.trim()) return
    const role = payload.role === 'agent' || payload.source === 'ai' ? 'agent' : payload.role === 'user' || payload.source === 'user' ? 'user' : null
    if (!role) return
    const key = typeof payload.response_id === 'string' ? `${role}:${payload.response_id.slice(0, 200)}`
      : typeof payload.event_id === 'number' ? `${role}:${payload.event_id}` : null
    let id = key ? scope.state.messageIds.get(key) : undefined
    const text = payload.message.trim()
    let typedEcho = false
    if (role === 'agent') scope.state.pendingTyped = []
    else if (!id) {
      const now = Date.now()
      scope.state.pendingTyped = scope.state.pendingTyped.filter(row => now - row.at < TYPED_ECHO_MS)
      const echo = scope.state.pendingTyped.findIndex(row => row.text === text)
      if (echo >= 0) { id = scope.state.pendingTyped.splice(echo, 1)[0]!.id; typedEcho = true }
      else scope.state.pendingTyped = []
    }
    if (payload.source === 'user' && !typedEcho && (!key || scope.state.userEvents.get(key) !== text)) {
      registerTranscript(text, scope.state.attempt)
    }
    if (payload.source === 'user' && key) {
      scope.state.userEvents.set(key, text)
      if (scope.state.userEvents.size > 180) scope.state.userEvents.delete(scope.state.userEvents.keys().next().value!)
    }
    if (!id) {
      id = `voice-${++scope.state.serial}`
    }
    if (key) scope.state.messageIds.set(key, id)
    if (scope.state.messageIds.size > 180) scope.state.messageIds.delete(scope.state.messageIds.keys().next().value!)
    const row: VoiceMessage = { id, role, text: text.slice(0, 4000) }
    setTranscript(previous => {
      const rows = previous.scope === scope ? previous.messages : []
      const exists = rows.some(message => message.id === row.id)
      return { scope, messages: (exists ? rows.map(message => message.id === row.id ? row : message) : [...rows, row]).slice(-60) }
    })
  }, [scope, registerTranscript])
  const { status: sdkStatus, isSpeaking, isMuted, setMuted: sdkSetMuted, startSession, endSession,
    sendContextualUpdate, sendUserMessage, getInputVolume, getOutputVolume } = useConversation()
  sdkEnd.current = endSession
  const status = phase.scope === scope && phase.status !== null ? phase.status : sdkStatus
  const currentStatus = useRef(status)
  currentStatus.current = status
  useEffect(() => {
    scope.state.active = true
    return () => {
      scope.state.active = false
      invalidate()
      if (scope.state.closeTimer) clearTimeout(scope.state.closeTimer)
      if (scope.state.settledTimer) clearTimeout(scope.state.settledTimer)
      if (scope.state.sdkStarted || scope.state.closing) endSession()
    }
  }, [scope, invalidate, endSession])

  useEffect(() => {
    if (status !== 'connected') return
    const clamp = (value: number) => Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0
    const sample = () => {
      if (!scope.state.active || currentStatus.current !== 'connected') return
      let input = 0, output = 0
      try { input = isMuted ? 0 : clamp(getInputVolume()); output = clamp(getOutputVolume()) } catch { /* Teardown may win the sample. */ }
      setLevels(previous => previous.scope === scope && previous.input === input && previous.output === output ? previous : { scope, input, output })
    }
    sample()
    const timer = setInterval(sample, 80)
    return () => clearInterval(timer)
  }, [scope, status, isMuted, getInputVolume, getOutputVolume])

  const start = useCallback(async () => {
    const latestStatus = scope.state.phase ?? currentStatus.current
    if (!scope.state.active || scope.state.starting || (latestStatus !== 'disconnected' && latestStatus !== 'error')) return
    if (scope.state.closing) {
      const message = scope.state.closeTimedOut ? VOICE_RELOAD : VOICE_CLOSING
      showError(message)
      throw new Error(message)
    }
    if (latestStatus === 'error' && scope.state.sdkStarted) {
      scope.state.userStopped = true
      closeSdk()
      changePhase('disconnected')
      showError(VOICE_CLOSING)
      throw new Error(VOICE_CLOSING)
    }
    if (!sessionId) {
      const message = 'Choose a building and start a session first.'
      showError(message)
      throw new Error(message)
    }
    invalidate()
    const attempt = scope.state.attempt
    const controller = new AbortController()
    scope.state.controller = controller
    scope.state.starting = true
    scope.state.userStopped = false
    scope.state.pendingTyped = []
    scope.state.messageIds.clear() // Provider event IDs may restart on a new call.
    scope.state.userEvents.clear()
    const current = () => scope.state.active && scope.state.attempt === attempt && !controller.signal.aborted
    changePhase('connecting')
    showError(null)
    scope.state.startTimer = setTimeout(() => {
      if (!current()) return
      scope.state.userStopped = true
      invalidate()
      if (scope.state.sdkStarted) closeSdk()
      changePhase('error')
      showError(CONNECTION_FAILED)
    }, 30000)
    try {
      const response = await fetch(`/api/voice/token?agent=${agent}`, { cache: 'no-store', signal: controller.signal })
      if (!current()) return
      const payload: unknown = await response.json()
      if (!current()) return
      const body = payload && typeof payload === 'object' ? payload : {}
      if (!response.ok || !('token' in body) || typeof body.token !== 'string' || !body.token) {
        const code = 'error' in body && body.error && typeof body.error === 'object' && 'code' in body.error ? body.error.code : undefined
        throw new Error(response.status === 429 ? 'Voice quota exceeded' : typeof code === 'string' ? code : VOICE_UNAVAILABLE)
      }
      scope.state.sdkStarted = true
      scope.state.sdkAttempt = attempt
      scope.state.acceptingMessages = true
      // React SDK returns void; onConnect/onError/onDisconnect finish the handshake.
      startSession({ conversationToken: body.token, connectionType: 'webrtc', clientTools: toolsForAttempt(attempt),
        onMessage: payload => { if (current()) onMessage(payload) },
        onError: (message, detail) => { if (current()) onError(message, detail) },
        onConnect: () => {
          if (current()) onConnect()
          else if (scope.state.active && scope.state.sdkAttempt === attempt && scope.state.closing) closeSdk()
        },
        onStatusChange: event => { if (scope.state.sdkAttempt === attempt) onStatusChange(event) },
        onDisconnect: details => {
          if (current()) onDisconnect(details)
          else if (scope.state.active && scope.state.sdkAttempt === attempt && scope.state.closing) finishClosing()
        },
      })
    } catch (reason) {
      if (!current()) return
      invalidate()
      const message = safeError(reason)
      changePhase('error')
      showError(message)
      throw new Error(message)
    }
  }, [agent, sessionId, startSession, scope, changePhase, showError, invalidate, closeSdk, toolsForAttempt, onMessage, onError, onConnect, onStatusChange, onDisconnect, finishClosing])

  const stop = useCallback(async () => {
    if (!scope.state.active) return
    scope.state.userStopped = true
    invalidate()
    changePhase('disconnected')
    showError(null)
    if (scope.state.sdkStarted || scope.state.closing) closeSdk()
    else await endSession()
  }, [endSession, invalidate, scope, changePhase, showError, closeSdk])
  const sendContext = useCallback((text: string) => {
    if (scope.state.active && (scope.state.phase ?? currentStatus.current) === 'connected' && text.trim()) {
      try { sendContextualUpdate(text) } catch { showError(CONNECTION_FAILED) }
    }
  }, [sendContextualUpdate, scope, showError])
  const sendText = useCallback((text: string): boolean => {
    if (!scope.state.active || (scope.state.phase ?? currentStatus.current) !== 'connected' || !text.trim()) return false
    try {
      const accepted = text.trim().slice(0, 10000)
      sendUserMessage(accepted)
      registerTranscript(accepted, scope.state.attempt)
      // This is the user's actual accepted submission, not a generated reply.
      // SDK sendUserMessage does not guarantee a local onMessage echo.
      const row: VoiceMessage = { id: `voice-${++scope.state.serial}`, role: 'user', text: accepted.slice(0, 4000) }
      const now = Date.now()
      scope.state.pendingTyped = [...scope.state.pendingTyped.filter(pending => now - pending.at < TYPED_ECHO_MS),
        { id: row.id, text: accepted, at: now }].slice(-60)
      setTranscript(previous => ({ scope, messages: [...(previous.scope === scope ? previous.messages : []), row].slice(-60) }))
      return true
    } catch { showError(CONNECTION_FAILED); return false }
  }, [scope, sendUserMessage, showError, registerTranscript])
  const setMuted = useCallback((muted: boolean) => {
    if (!scope.state.active || (scope.state.phase ?? currentStatus.current) !== 'connected') return
    try { sdkSetMuted(muted) } catch { showError(CONNECTION_FAILED) }
  }, [scope, sdkSetMuted, showError])
  return { status, isSpeaking: status === 'connected' && isSpeaking, error, start, stop, sendContext,
    messages, inputLevel: status === 'connected' && levels.scope === scope ? levels.input : 0,
    outputLevel: status === 'connected' && levels.scope === scope ? levels.output : 0,
    isMuted: status === 'connected' && isMuted, setMuted, sendText }
}
