/** Exact CONTRACTS C1 tool names. The server remains the authority for roles and state. */
export const TOOL_NAMES = [
  'find', 'plan_tour', 'route', 'next_step', 'spatial_query',
  'propose_edit', 'commit_edit', 'undo', 'what_if', 'set_scale', 'generate_markers',
] as const

export type BuildingToolName = typeof TOOL_NAMES[number]
export type ToolDisplay = Record<string, unknown>
export type ToolResponse = {
  ok: boolean
  speech?: string
  result?: unknown
  display?: ToolDisplay
  error?: { code?: string; message?: string; candidates?: unknown[] }
}

export type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

type Options = {
  sessionId: string
  onDisplay?: (display: ToolDisplay, response: ToolResponse) => void
  fetcher?: Fetcher
  navigationGuard?: NavigationRequestGuard
}

export function createNavigationRequestGuard(isActive = () => true) {
  let generation = 0
  return {
    begin: () => ++generation,
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

/** Keep JSON parseable even for a large tour result; never slice serialized JSON. */
export function serializeToolResponse(response: ToolResponse): string {
  const body = {
    ok: response.ok,
    speech: response.speech || response.error?.message || (response.ok ? 'Done.' : 'The tool could not complete.'),
    ...(response.result === undefined ? {} : { result: response.result }),
    ...(response.ok ? {} : { error: response.error }),
  }
  const full = JSON.stringify(body)
  if (full.length <= 1500) return full
  const summary: Record<string, unknown> = { details_in_app: true }
  if (response.result && typeof response.result === 'object') {
    const result = response.result as Record<string, unknown>
    for (const key of ['tour_id', 'proposal_id', 'event_id', 'reachable', 'length_m']) {
      const value = result[key]
      if (typeof value === 'string') summary[key] = value.slice(0, 100)
      else if (typeof value === 'boolean' || typeof value === 'number') summary[key] = value
    }
  }
  // Escaped control characters can take six serialized characters each.
  const compact = { ok: body.ok, speech: body.speech.slice(0, 160), ...(response.ok ? { result: summary } : { error: { code: response.error?.code?.slice(0, 40) || 'internal' } }) }
  const serialized = JSON.stringify(compact)
  if (serialized.length <= 1500) return serialized
  return JSON.stringify({ ok: response.ok, speech: response.ok ? 'Done. Full details are in the application.' : 'The tool failed. Check the application for details.' })
}

export function createClientTools({ sessionId, onDisplay, fetcher = fetch,
  navigationGuard = createNavigationRequestGuard() }: Options): Record<BuildingToolName, (args?: unknown) => Promise<string>> {
  const execute = (name: BuildingToolName) => async (input?: unknown): Promise<string> => {
    if (!sessionId) return serializeToolResponse(failure('Choose a building and start a session first.', 'invalid_args'))
    if (input != null && (typeof input !== 'object' || Array.isArray(input))) {
      return serializeToolResponse(failure('Tool arguments must be an object.', 'invalid_args'))
    }
    const args = { ...(input as Record<string, unknown> | undefined) }
    // next_step advances an index, but a superseded instruction must never be
    // spoken or displayed. Committed admin writes retain their actual outcome.
    const navigationRequest = name === 'next_step' ? navigationGuard.begin() : null
    const superseded = () => navigationRequest !== null && !navigationGuard.isCurrent(navigationRequest)
    const stale = () => serializeToolResponse(failure('That instruction was superseded. Use the latest directions response.', 'version_conflict'))
    if (superseded()) return stale()
    if (name === 'commit_edit') {
      if (typeof args.proposal_id !== 'string' || !args.proposal_id) {
        return serializeToolResponse(failure('Preview the change before confirming it.', 'invalid_args'))
      }
      args.op_id = operationId(sessionId, args.proposal_id)
    }
    try {
      const response = await fetcher(`/api/tools/${name}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, args }),
      })
      const payload: unknown = await response.json()
      if (superseded()) return stale()
      if (!payload || typeof payload !== 'object' || typeof (payload as ToolResponse).ok !== 'boolean') {
        return serializeToolResponse(failure('The tool returned an invalid response. Please try text chat.'))
      }
      const result = payload as ToolResponse
      if (!response.ok) return serializeToolResponse(failure(result.error?.message || 'The request could not complete. Please try again.', result.error?.code))
      if (result.ok && result.display && typeof result.display === 'object' && !Array.isArray(result.display)) {
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
