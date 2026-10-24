import { useCallback, useMemo, useRef, useState } from 'react'
import { useConversation } from '@elevenlabs/react'
import { createClientTools } from './clientTools'
import type { ToolDisplay, ToolResponse } from './clientTools'

export type BuildingVoiceOptions = {
  agent: 'navigator' | 'admin'
  sessionId: string
  onDisplay?: (display: ToolDisplay, response: ToolResponse) => void
}

/** Must be rendered inside the app's ConversationProvider; UI stays with the caller. */
export function useBuildingVoice({ agent, sessionId, onDisplay }: BuildingVoiceOptions) {
  const [error, setError] = useState<string | null>(null)
  const starting = useRef(false)
  const tools = useMemo(() => createClientTools({ sessionId, onDisplay }), [sessionId, onDisplay])
  const { status, isSpeaking, startSession, endSession, sendContextualUpdate } = useConversation({ clientTools: tools })

  const start = useCallback(async () => {
    if (starting.current || status !== 'disconnected') return
    if (!sessionId) {
      const message = 'Choose a building and start a session first.'
      setError(message)
      throw new Error(message)
    }
    starting.current = true
    setError(null)
    try {
      const response = await fetch(`/api/voice/token?agent=${agent}`, { cache: 'no-store' })
      const payload: unknown = await response.json()
      const body = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {}
      if (!response.ok || typeof body.token !== 'string' || !body.token) {
        throw new Error('Voice is unavailable. Please use text chat.')
      }
      await startSession({ conversationToken: body.token })
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Voice is unavailable. Please use text chat.'
      setError(message)
      throw new Error(message)
    } finally {
      starting.current = false
    }
  }, [agent, sessionId, startSession, status])

  const stop = useCallback(async () => { await endSession() }, [endSession])
  const sendContext = useCallback((text: string) => {
    if (status === 'connected' && text.trim()) sendContextualUpdate(text)
  }, [sendContextualUpdate, status])

  return { status, isSpeaking, error, start, stop, sendContext }
}
