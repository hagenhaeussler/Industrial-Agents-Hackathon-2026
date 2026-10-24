import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useConversation } from '@elevenlabs/react'
import { createClientTools, createNavigationRequestGuard } from './clientTools'
import type { ToolDisplay, ToolResponse } from './clientTools'

const VOICE_UNAVAILABLE = 'Voice is unavailable. Please use text chat.'

export type BuildingVoiceOptions = {
  agent: 'navigator' | 'admin'
  sessionId: string
  onDisplay?: (display: ToolDisplay, response: ToolResponse) => void
}

/** Must be rendered inside the app's ConversationProvider; UI stays with the caller. */
export function useBuildingVoice({ agent, sessionId, onDisplay }: BuildingVoiceOptions) {
  const [error, setError] = useState<string | null>(null)
  const display = useRef(onDisplay)
  display.current = onDisplay
  // This lifecycle belongs to one hook/session, including handlers the SDK
  // retained from an earlier render. A retired session cannot start new work.
  const scope = useMemo(() => {
    const state = { active: true, starting: false, attempt: 0, controller: null as AbortController | null }
    return { state, navigation: createNavigationRequestGuard(() => state.active) }
  }, [agent, sessionId])
  const invalidate = useCallback(() => {
    scope.state.attempt++
    scope.state.controller?.abort()
    scope.state.controller = null
    scope.state.starting = false
    scope.navigation.invalidate()
  }, [scope])
  useEffect(() => {
    scope.state.active = true
    return () => { scope.state.active = false; invalidate() }
  }, [scope, invalidate])
  const tools = useMemo(() => createClientTools({ sessionId, navigationGuard: scope.navigation,
    onDisplay: (payload, response) => { if (scope.state.active) display.current?.(payload, response) } }), [sessionId, onDisplay, scope])
  // The React SDK starts asynchronously but returns void. Connection and
  // microphone failures arrive here, rather than rejecting startSession.
  const onError = useCallback(() => {
    if (!scope.state.active) return
    invalidate()
    setError(VOICE_UNAVAILABLE)
  }, [invalidate, scope])
  const { status, isSpeaking, startSession, endSession, sendContextualUpdate } = useConversation({ clientTools: tools, onError })

  const start = useCallback(async () => {
    if (!scope.state.active || scope.state.starting || (status !== 'disconnected' && status !== 'error')) return
    if (!sessionId) {
      const message = 'Choose a building and start a session first.'
      setError(message)
      throw new Error(message)
    }
    const attempt = ++scope.state.attempt
    const controller = new AbortController()
    scope.state.controller = controller
    scope.state.starting = true
    const current = () => scope.state.active && scope.state.attempt === attempt && !controller.signal.aborted
    setError(null)
    try {
      // An SDK error can leave a conversation instance alive. End it before
      // fetching a fresh token so retry cannot reuse that failed connection.
      if (status === 'error') endSession()
      const response = await fetch(`/api/voice/token?agent=${agent}`, { cache: 'no-store', signal: controller.signal })
      if (!current()) return
      const payload: unknown = await response.json()
      if (!current()) return
      const body = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {}
      if (!response.ok || typeof body.token !== 'string' || !body.token) {
        throw new Error(VOICE_UNAVAILABLE)
      }
      startSession({ conversationToken: body.token })
    } catch {
      if (!current()) return
      const message = VOICE_UNAVAILABLE
      setError(message)
      throw new Error(message)
    } finally {
      // An old cancelled request may settle after its replacement has started.
      if (scope.state.attempt === attempt) {
        scope.state.starting = false
        scope.state.controller = null
      }
    }
  }, [agent, sessionId, startSession, endSession, status, scope])

  const stop = useCallback(async () => {
    if (!scope.state.active) return
    invalidate()
    await endSession()
  }, [endSession, invalidate, scope])
  const sendContext = useCallback((text: string) => {
    if (scope.state.active && status === 'connected' && text.trim()) sendContextualUpdate(text)
  }, [sendContextualUpdate, status, scope])

  return { status, isSpeaking, error, start, stop, sendContext }
}
