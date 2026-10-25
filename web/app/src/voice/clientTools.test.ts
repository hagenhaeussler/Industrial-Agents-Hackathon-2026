import { describe, expect, it } from 'bun:test'
import { createClientTools, createNavigationRequestGuard, serializeToolResponse, TOOL_NAMES, VOICE_RESULT_BYTE_BUDGET } from './clientTools'
import type { Fetcher, ToolResponse } from './clientTools'

const registeredTurn = { getTurnId: async () => 'turn-test' }

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

describe('voice client tools', () => {
  it('suppresses a delayed next_step after a newer no_route before display and speech', async () => {
    let release: ((response: Response) => void) | undefined
    let requests = 0
    const shown: unknown[] = []
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-race',
      fetcher: async () => ++requests === 1
        ? new Promise<Response>(resolve => { release = resolve })
        : json({ ok: false, speech: 'The lift is closed.', error: { code: 'no_route' } }),
      onDisplay: display => { shown.push(display) },
    })
    const old = tools.next_step()
    await Promise.resolve()
    expect(JSON.parse(await tools.next_step()).error.code).toBe('no_route')
    release!(json({ ok: true, speech: 'Take the closed lift.',
      result: { kind: 'take_lift' }, display: { kind: 'instruction' } }))
    const superseded = JSON.parse(await old)
    expect(superseded.ok).toBe(false)
    expect(superseded.error.code).toBe('version_conflict')
    expect(superseded.speech).not.toContain('Take the closed lift')
    expect(shown).toEqual([])
  })

  it('publishes all generated tools, including pure route queries', () => {
    expect(Object.keys(createClientTools({ ...registeredTurn, sessionId: 'session-test' }))).toEqual([...TOOL_NAMES])
    expect(TOOL_NAMES).toContain('query_route')
    expect(TOOL_NAMES).toContain('query_tour')
  })

  it('posts session context and forwards display after success', async () => {
    let sent: unknown
    let shown: unknown
    const tools = createClientTools({ ...registeredTurn,
      sessionId: 'session-test',
      fetcher: (async (input, init) => {
        expect(input).toBe('/api/agent/tools/find')
        sent = JSON.parse(init?.body as string)
        return json({ ok: true, speech: 'Tool crib upstairs.', result: { asset_id: 'asset-test' }, display: { kind: 'highlight', ids: ['asset-test'] } })
      }) as Fetcher,
      onDisplay: display => { shown = display },
    })
    expect(JSON.parse(await tools.find({ query: 'torque wrench' })).ok).toBe(true)
    expect(sent).toEqual({ session_id: 'session-test', turn_id: 'turn-test', args: { query: 'torque wrench' } })
    expect(shown).toEqual({ kind: 'highlight', ids: ['asset-test'] })
  })

  it('reuses the commit operation ID across retries and handler recreation', async () => {
    const ids: unknown[] = []
    const fetcher = (async (_input, init) => {
      ids.push(JSON.parse(init?.body as string).args.op_id)
      return json({ ok: true, speech: 'Lift closed.', result: { event_id: 'event-test' } })
    }) as Fetcher
    const options = { ...registeredTurn, sessionId: 'session-stable-id', fetcher }
    const tools = createClientTools(options)
    await tools.commit_edit({ proposal_id: 'proposal-test' })
    await tools.commit_edit({ proposal_id: 'proposal-test', op_id: 'untrusted-client-id' })
    await createClientTools(options).commit_edit({ proposal_id: 'proposal-test' })
    expect(new Set(ids).size).toBe(1)
    expect(ids[0]).not.toBe('untrusted-client-id')
  })

  it('does not show a failed domain result as success', async () => {
    const tools = createClientTools({ ...registeredTurn,
      sessionId: 'session-test',
      fetcher: (async () => json({ ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: ['Press 4', 'Press 7'] }, display: { kind: 'highlight' } })) as Fetcher,
      onDisplay: () => { throw new Error('Failed tools cannot update the display') },
    })
    const result = JSON.parse(await tools.find({ query: 'press' }))
    expect(result.ok).toBe(false)
    expect(result.error.code).toBe('ambiguous')
  })

  it('keeps all error candidates on an HTTP failure', async () => {
    const candidates = Array.from({ length: 100 }, (_, id) => ({ id: `press-${id}`, name: `Press ${id}` }))
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test',
      fetcher: async () => json({ ok: false, error: { code: 'ambiguous', message: 'Which press?', candidates } }, 409),
    })
    expect(JSON.parse(await tools.find()).error.candidates).toEqual(candidates)
  })

  it('preserves committed success when a view callback throws', async () => {
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test',
      fetcher: async () => json({ ok: true, speech: 'Lift closed.', result: { event_id: 'event-test' }, display: { kind: 'event' } }),
      onDisplay: () => { throw new Error('View callback failed') },
    })
    expect(JSON.parse(await tools.commit_edit({ proposal_id: 'proposal-render-test' })).ok).toBe(true)
  })

  it('makes transport, malformed payload, and offline failures explicit', async () => {
    const responses = [
      (async () => json({ ok: true, speech: 'Wrongly marked success' }, 500)) as Fetcher,
      (async () => json({ detail: 'oops' })) as Fetcher,
      (async () => { throw new Error('offline') }) as Fetcher,
    ]
    for (const fetcher of responses) {
      const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test', fetcher })
      expect(JSON.parse(await tools.find({ query: 'press' })).ok).toBe(false)
    }
  })

  it('rejects missing session, invalid args, and missing proposal without requests', async () => {
    const fetcher = (async () => { throw new Error('No request expected') }) as Fetcher
    expect(JSON.parse(await createClientTools({ ...registeredTurn, sessionId: '', fetcher }).find({ query: 'press' })).error.code).toBe('invalid_args')
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test', fetcher })
    expect(JSON.parse(await tools.find(['invalid'])).error.code).toBe('invalid_args')
    expect(JSON.parse(await tools.commit_edit()).error.code).toBe('invalid_args')
  })
})

describe('registered user turns', () => {
  it('waits for registration before sending a tool to the policy endpoint', async () => {
    let register!: (id: string) => void
    let sent: unknown
    const tools = createClientTools({ sessionId: 'session-test',
      getTurnId: () => new Promise(resolve => { register = resolve }),
      fetcher: async (url, init) => {
        expect(url).toBe('/api/agent/tools/building_info')
        sent = JSON.parse(String(init?.body))
        return json({ ok: true })
      },
    })
    const pending = tools.building_info()
    expect(sent).toBeUndefined()
    register('real-user-turn')
    expect(JSON.parse(await pending).ok).toBe(true)
    expect(sent).toEqual({ session_id: 'session-test', turn_id: 'real-user-turn', args: {} })
  })

  it.each(['missing', 'failed'])('fails closed for a %s turn without calling any endpoint', async state => {
    const requested: unknown[] = []
    const tools = createClientTools({ sessionId: 'session-test',
      getTurnId: async () => { if (state === 'failed') throw new Error('Registration failed'); return '' },
      fetcher: async url => { requested.push(url); return json({ ok: true }) },
    })
    expect(JSON.parse(await tools.find({ query: 'press' })).ok).toBe(false)
    expect(requested).toEqual([])
  })

  it.each([{ speech: 9 }, { error: { message: 9 } }, { error: { candidates: {} } }, { display: [] }])('rejects malformed voice fields: %j', async fields => {
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test',
      fetcher: async () => json({ ok: true, ...fields }),
    })
    expect(JSON.parse(await tools.find()).ok).toBe(false)
  })
})

describe('voice result size', () => {
  it('uses the complete server observation and keeps the full display in the UI', async () => {
    const modelResult = { entities: Array.from({ length: 100 }, (_, id) => ({ id: `part-${id}`, name: `Press ${id}`, room: 'Workshop' })), next_cursor: 'page-2' }
    let displayed: unknown
    const display = { kind: 'route', segments: Array(100).fill({ points: [[1, 2], [3, 4]] }) }
    const tools = createClientTools({ ...registeredTurn, sessionId: 'session-test',
      fetcher: async () => json({ ok: true, result: { irrelevant: 'legacy' }, model_result: modelResult, display }),
      onDisplay: value => { displayed = value },
    })
    expect(JSON.parse(await tools.search_entities()).result).toEqual(modelResult)
    expect(displayed).toEqual(display)
  })

  it('keeps complete search results and ambiguous candidates over the old limit', () => {
    const candidates = Array.from({ length: 150 }, (_, id) => ({ id: `part-${id}`, name: `Press ${id}`, floor_id: 'upstairs' }))
    for (const response of [
      { ok: true, result: { entities: candidates, next_cursor: 'page-2' } },
      { ok: false, error: { code: 'ambiguous', candidates } },
    ]) {
      const body = JSON.parse(serializeToolResponse(response))
      if (response.ok) expect(body.result).toEqual(response.result)
      else expect(body.error).toEqual(response.error)
    }
  })

  it('omits route geometry but keeps route facts and every search field', () => {
    const response: ToolResponse = { ok: true, result: { routes: [{ reachable: true, from_space_id: 'a', to_space_id: 'b', length_m: 24,
      segments: Array(1000).fill({ points: [[1, 2], [3, 4]] }) }], entities: [{ id: 'a', segments: ['search data'] }] } }
    expect(JSON.parse(serializeToolResponse(response)).result).toEqual({ routes: [{ reachable: true, from_space_id: 'a', to_space_id: 'b', length_m: 24 }], entities: [{ id: 'a', segments: ['search data'] }] })
  })

  it('returns an explicit size error instead of dropping result or candidate rows', () => {
    for (const response of [
      { ok: true, model_result: { entities: Array(1000).fill({ id: 'part', name: 'Press'.repeat(30) }) } },
      { ok: false, error: { code: 'ambiguous', candidates: Array(1000).fill('Press'.repeat(30)) } },
    ]) {
      const serialized = serializeToolResponse(response)
      expect(new TextEncoder().encode(serialized).byteLength).toBeLessThanOrEqual(VOICE_RESULT_BYTE_BUDGET)
      const body = JSON.parse(serialized)
      expect(body.ok).toBe(false)
      expect(body.error.code).toBe('result_too_large')
      expect(body.speech).toContain('smaller search page')
    }
  })

  it('measures the budget in UTF-8 bytes, including speech', () => {
    const serialized = serializeToolResponse({ ok: true, speech: '😀'.repeat(13000) })
    expect(JSON.parse(serialized).error.code).toBe('result_too_large')
  })
})

describe('voice tool outcome observers', () => {
  it('returns the actual backend conflict when its observer invalidates the current turn guard', async () => {
    const turnGuard = createNavigationRequestGuard()
    const response = { ok: false, speech: 'Use a new user turn.', error: { code: 'version_conflict' } }
    const tools = createClientTools({ ...registeredTurn, sessionId: 's', turnGuard,
      fetcher: async () => json(response, 409),
      onResponse: () => { turnGuard.invalidate() },
    })
    expect(JSON.parse(await tools.find())).toEqual(response)
  })

  it.each([200, 409])('reports failed ambiguity from HTTP %d without repainting the map', async status => {
    const response = { ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: [{ id: 'p4', name: 'Press 4' }] } }
    const seen: ToolResponse[] = []
    const tools = createClientTools({ ...registeredTurn, sessionId: 's', fetcher: async () => json(response, status), onResponse: result => seen.push(result), onDisplay: () => { throw new Error('No display on failure') } })
    expect(JSON.parse(await tools.find({ query: 'press' })).ok).toBe(false)
    expect(seen).toEqual([response])
  })
  it('an observer exception cannot change a committed server result', async () => {
    const tools = createClientTools({ ...registeredTurn, sessionId: 's', fetcher: async () => json({ ok: true, result: { event_id: 'e' } }), onResponse: () => { throw new Error('View failed') } })
    expect(JSON.parse(await tools.commit_edit({ proposal_id: 'p' })).ok).toBe(true)
  })
})
