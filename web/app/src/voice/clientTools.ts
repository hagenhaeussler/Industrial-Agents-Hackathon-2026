import type { ToolResponse as ServerToolResponse } from '../api/types'

import { TOOL_NAMES } from '../api/agentTools.gen'
export { TOOL_NAMES } from '../api/agentTools.gen'

export type BuildingToolName = typeof TOOL_NAMES[number]
export type ToolDisplay = Record<string, unknown>
export type ToolResponse = Pick<ServerToolResponse, 'ok' | 'speech'> & {
  result?: unknown
  model_result?: unknown
  display?: ToolDisplay
  error?: { code?: string; message?: string; candidates?: unknown[] }
}

export type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

type Options = {
  sessionId: string
  getTurnId: () => Promise<string>
  isActive?: () => boolean
  onDisplay?: (display: ToolDisplay, response: ToolResponse) => void
  onResponse?: (response: ToolResponse) => void
  fetcher?: Fetcher
  navigationGuard?: NavigationRequestGuard
  turnGuard?: NavigationRequestGuard
}

export function createNavigationRequestGuard(isActive = () => true) {
  let generation = 0
  return {
    begin: () => ++generation,
    capture: () => generation,
    isCurrent: (request: number) => isActive() && request === generation,
    invalidate: () => { generation++ },
  }
}
export type NavigationRequestGuard = ReturnType<typeof createNavigationRequestGuard>

const opIds = new Map<string, string>()

function operationId(sessionId: string, proposalId: string): string {
  const key = `tyb:voice:commit:${sessionId}:${proposalId}`
  let stored: string | null = null
  try { stored = globalThis.sessionStorage?.getItem(key) ?? null } catch { /* Private mode may deny storage. */ }
  const id = stored || opIds.get(key) || crypto.randomUUID()
  opIds.set(key, id)
  try { globalThis.sessionStorage?.setItem(key, id) } catch { /* Server also deduplicates proposal_id. */ }
  return id
}

function failure(message: string, code = 'not_available'): ToolResponse {
  return { ok: false, speech: message, error: { code, message } }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/** Validate the fields used by voice without claiming the weak server result has a known shape. */
function parseToolResponse(payload: unknown): ToolResponse | null {
  if (!isRecord(payload) || typeof payload.ok !== 'boolean') return null
  if (payload.speech !== undefined && typeof payload.speech !== 'string') return null
  if (payload.display !== undefined && !isRecord(payload.display)) return null
  let error: ToolResponse['error']
  if (payload.error !== undefined) {
    if (!isRecord(payload.error)) return null
    const { code, message, candidates } = payload.error
    if (code !== undefined && typeof code !== 'string') return null
    if (message !== undefined && typeof message !== 'string') return null
    if (candidates !== undefined && !Array.isArray(candidates)) return null
    error = { code, message, candidates }
  }
  return { ok: payload.ok, speech: payload.speech, result: payload.result,
    model_result: payload.model_result, display: payload.display, error }
}

/** Keep search pages and candidates intact. Only route geometry is omitted from legacy results. */
function withoutRouteGeometry(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(withoutRouteGeometry)
  if (!isRecord(value)) return value
  const route = typeof value.reachable === 'boolean' && typeof value.from_space_id === 'string' && typeof value.to_space_id === 'string'
  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !route || !['segments', 'space_path', 'element_path', 'node_path'].includes(key))
    .map(([key, item]) => [key, withoutRouteGeometry(item)]))
}

// The complete compact observation, including speech and errors, may use 48 KiB of UTF-8 JSON.
export const VOICE_RESULT_BYTE_BUDGET = 48 * 1024

export function serializeToolResponse(response: ToolResponse): string {
  const result = response.model_result === undefined ? withoutRouteGeometry(response.result) : response.model_result
  const body = {
    ok: response.ok,
    speech: response.speech || response.error?.message || (response.ok ? 'Done.' : 'The tool could not complete.'),
    ...(result === undefined ? {} : { result }),
    ...(response.ok ? {} : { error: response.error }),
  }
  const serialized = JSON.stringify(body)
  if (new TextEncoder().encode(serialized).byteLength <= VOICE_RESULT_BYTE_BUDGET) return serialized
  return JSON.stringify(failure('The tool result exceeds the 48 KiB voice limit. Request a smaller search page or fewer entities.', 'result_too_large'))
}

export function createClientTools({ sessionId, getTurnId, onDisplay, onResponse, fetcher = fetch, isActive = () => true,
  navigationGuard = createNavigationRequestGuard(), turnGuard = createNavigationRequestGuard() }: Options): Record<BuildingToolName, (args?: unknown) => Promise<string>> {
  const execute = (name: BuildingToolName) => async (input?: unknown): Promise<string> => {
    if (!sessionId) return serializeToolResponse(failure('Choose a building and start a session first.', 'invalid_args'))
    if (input != null && !isRecord(input)) {
      return serializeToolResponse(failure('Tool arguments must be an object.', 'invalid_args'))
    }
    const args = { ...input }
    const turnRequest = turnGuard.capture()
    const navigationRequest = name === 'next_step' ? navigationGuard.begin() : null
    const superseded = () => !turnGuard.isCurrent(turnRequest)
      || (name !== 'commit_edit' && !isActive())
      || (navigationRequest !== null && !navigationGuard.isCurrent(navigationRequest))
    const stale = () => serializeToolResponse(failure('That request was superseded. Use the latest user turn and tool response.', 'version_conflict'))
    if (!isActive() || superseded()) return stale()
    if (name === 'commit_edit') {
      if (typeof args.proposal_id !== 'string' || !args.proposal_id) {
        return serializeToolResponse(failure('Preview the change before confirming it.', 'invalid_args'))
      }
      args.op_id = operationId(sessionId, args.proposal_id)
    }
    let turnId: string
    try {
      turnId = await getTurnId()
      if (!turnId.trim()) throw new Error('Missing turn')
    } catch {
      if (superseded()) return stale()
      return serializeToolResponse(failure('No registered user turn is available. Say your request again or use text chat.'))
    }
    if (!isActive() || superseded()) return stale()
    try {
      const response = await fetcher(`/api/agent/tools/${name}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, turn_id: turnId, args }),
      })
      const payload: unknown = await response.json()
      if (superseded()) return stale()
      const result = parseToolResponse(payload)
      if (!result) return serializeToolResponse(failure('The tool returned an invalid response. Please try text chat.'))
      const outcome = !response.ok && result.ok ? failure('The request could not complete. Please try again.') : result
      if (isActive()) {
        try { onResponse?.(outcome) } catch { /* A view callback cannot change the server outcome. */ }
      }
      if (!response.ok) return serializeToolResponse(outcome)
      if (isActive() && result.ok && result.display) {
        // A view callback cannot change an already committed server operation into a failure.
        try { onDisplay?.(result.display, result) } catch { /* The caller handles its own rendering errors. */ }
      }
      return serializeToolResponse(result)
    } catch {
      if (superseded()) return stale()
      return serializeToolResponse(failure('The building server could not be reached. Please try again.'))
    }
  }
  return Object.fromEntries(TOOL_NAMES.map(name => [name, execute(name)])) as Record<BuildingToolName, (args?: unknown) => Promise<string>>
}
