import { describe, expect, it } from 'bun:test'
import { createClientTools, serializeToolResponse, TOOL_NAMES } from './clientTools'
import type { Fetcher, ToolResponse } from './clientTools'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

describe('voice client tools', () => {
  it('suppresses a delayed next_step after a newer no_route before display and speech', async () => {
    let release: ((response: Response) => void) | undefined
    let requests = 0
    const shown: unknown[] = []
    const tools = createClientTools({ sessionId: 'session-race',
      fetcher: async () => ++requests === 1
        ? new Promise<Response>(resolve => { release = resolve })
        : json({ ok: false, speech: 'The lift is closed.', error: { code: 'no_route' } }),
      onDisplay: display => { shown.push(display) },
    })
    const old = tools.next_step()
    expect(JSON.parse(await tools.next_step()).error.code).toBe('no_route')
    release!(json({ ok: true, speech: 'Take the closed lift.',
      result: { kind: 'take_lift' }, display: { kind: 'instruction' } }))
    const superseded = JSON.parse(await old)
    expect(superseded.ok).toBe(false)
    expect(superseded.error.code).toBe('version_conflict')
    expect(superseded.speech).not.toContain('Take the closed lift')
    expect(shown).toEqual([])
  })

  it('publishes exactly the eleven contract names', () => {
    expect(Object.keys(createClientTools({ sessionId: 'session-test' }))).toEqual([...TOOL_NAMES])
  })

  it('posts session context and forwards display after success', async () => {
    let sent: unknown
    let shown: unknown
    const tools = createClientTools({
      sessionId: 'session-test',
      fetcher: (async (input, init) => {
        expect(input).toBe('/api/tools/find')
        sent = JSON.parse(init?.body as string)
        return json({ ok: true, speech: 'Tool crib upstairs.', result: { asset_id: 'asset-test' }, display: { kind: 'highlight', ids: ['asset-test'] } })
      }) as Fetcher,
      onDisplay: display => { shown = display },
    })
    expect(JSON.parse(await tools.find({ query: 'torque wrench' })).ok).toBe(true)
    expect(sent).toEqual({ session_id: 'session-test', args: { query: 'torque wrench' } })
    expect(shown).toEqual({ kind: 'highlight', ids: ['asset-test'] })
  })

  it('reuses the commit operation ID across retries and handler recreation', async () => {
    const ids: unknown[] = []
    const fetcher = (async (_input, init) => {
      ids.push(JSON.parse(init?.body as string).args.op_id)
      return json({ ok: true, speech: 'Lift closed.', result: { event_id: 'event-test' } })
    }) as Fetcher
    const options = { sessionId: 'session-stable-id', fetcher }
    const tools = createClientTools(options)
    await tools.commit_edit({ proposal_id: 'proposal-test' })
    await tools.commit_edit({ proposal_id: 'proposal-test', op_id: 'untrusted-client-id' })
    await createClientTools(options).commit_edit({ proposal_id: 'proposal-test' })
    expect(new Set(ids).size).toBe(1)
    expect(ids[0]).not.toBe('untrusted-client-id')
  })

  it('does not show a failed domain result as success', async () => {
    const tools = createClientTools({
      sessionId: 'session-test',
      fetcher: (async () => json({ ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: ['Press 4', 'Press 7'] }, display: { kind: 'highlight' } })) as Fetcher,
      onDisplay: () => { throw new Error('Failed tools cannot update the display') },
    })
    const result = JSON.parse(await tools.find({ query: 'press' }))
    expect(result.ok).toBe(false)
    expect(result.error.code).toBe('ambiguous')
  })

  it('preserves committed success when a view callback throws', async () => {
    const tools = createClientTools({ sessionId: 'session-test',
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
      const tools = createClientTools({ sessionId: 'session-test', fetcher })
      expect(JSON.parse(await tools.find({ query: 'press' })).ok).toBe(false)
    }
  })

  it('rejects missing session, invalid args, and missing proposal without requests', async () => {
    const fetcher = (async () => { throw new Error('No request expected') }) as Fetcher
    expect(JSON.parse(await createClientTools({ sessionId: '', fetcher }).find({ query: 'press' })).error.code).toBe('invalid_args')
    const tools = createClientTools({ sessionId: 'session-test', fetcher })
    expect(JSON.parse(await tools.find(['invalid'])).error.code).toBe('invalid_args')
    expect(JSON.parse(await tools.commit_edit()).error.code).toBe('invalid_args')
  })
})

describe('voice result size', () => {
  it('preserves valid JSON and essential IDs for large computed tours', () => {
    const response: ToolResponse = { ok: true, speech: 'Three stops upstairs.', result: { tour_id: 'tour-test', legs: Array(400).fill({ points: [[1, 2], [3, 4]] }) } }
    const serialized = serializeToolResponse(response)
    expect(serialized.length).toBeLessThanOrEqual(1500)
    expect(JSON.parse(serialized)).toEqual({ ok: true, speech: response.speech, result: { details_in_app: true, tour_id: 'tour-test' } })
  })

  it('keeps failures false even when escaped content is very large', () => {
    const serialized = serializeToolResponse({ ok: false, speech: '\u0000'.repeat(4000), error: { code: 'ambiguous', candidates: Array(1000).fill('Press') } })
    expect(serialized.length).toBeLessThanOrEqual(1500)
    expect(JSON.parse(serialized).ok).toBe(false)
  })
})

describe('voice tool outcome observers', () => {
  it('reports failed ambiguity without repainting the map', async () => {
    const response = { ok: false, speech: 'Which press?', error: { code: 'ambiguous', candidates: [{ id: 'p4', name: 'Press 4' }] } }
    const seen: ToolResponse[] = []
    const tools = createClientTools({ sessionId: 's', fetcher: async () => json(response), onResponse: result => seen.push(result), onDisplay: () => { throw new Error('No display on failure') } })
    expect(JSON.parse(await tools.find({ query: 'press' })).ok).toBe(false)
    expect(seen).toEqual([response])
  })
  it('an observer exception cannot change a committed server result', async () => {
    const tools = createClientTools({ sessionId: 's', fetcher: async () => json({ ok: true, result: { event_id: 'e' } }), onResponse: () => { throw new Error('View failed') } })
    expect(JSON.parse(await tools.commit_edit({ proposal_id: 'p' })).ok).toBe(true)
  })
})
