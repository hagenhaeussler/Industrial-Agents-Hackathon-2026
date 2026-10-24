import { describe, expect, it } from 'bun:test'
import type { Snapshot } from '../api/types'
import { buildModel } from '../map/model'
import type { Model } from '../map/model'
import factoryJson from '../mocks/data/building_proc-factory-dev-003.json'
import { TOOL_NAMES } from './clientTools'
import { createDeskVoiceTools } from './uiTools'

const snapshot = () => structuredClone(factoryJson) as unknown as Snapshot

function harness(initial: Snapshot = snapshot()) {
  const state: { model: Model | null; selected: Set<string> } = {
    model: buildModel(initial), selected: new Set(),
  }
  const selections: Set<string>[] = []
  const floors: string[] = []
  const tools = createDeskVoiceTools({
    getModel: () => state.model,
    getSelected: () => state.selected,
    onSelection: ids => { selections.push(ids); state.selected = ids },
    onFloor: id => { floors.push(id) },
  })
  return { state, selections, floors, tools, ids: [...state.model!.asset.keys()] }
}

describe('desk voice selection', () => {
  it('adds and deduplicates exact IDs without mutating the caller set or building', async () => {
    const h = harness()
    const [first, second, third] = h.ids
    const original = new Set([first!])
    h.state.selected = original
    const before = JSON.stringify(h.state.model!.snapshot)
    const response = JSON.parse(await h.tools.update_selection({ action: 'add', items: ` ${second}, ${third},${second} ` }))
    expect(response).toEqual({ ok: true, speech: '3 items are selected.', result: { asset_ids: [first, second, third], selection_count: 3 } })
    expect(h.state.selected).toEqual(new Set([first!, second!, third!]))
    expect(h.state.selected).not.toBe(original)
    expect(original).toEqual(new Set([first!]))
    expect(JSON.stringify(h.state.model!.snapshot)).toBe(before)
    expect(h.floors).toEqual([])
  })

  it('removes requested IDs and replaces the whole selection', async () => {
    const h = harness()
    const [first, second, third] = h.ids
    h.state.selected = new Set([first!, second!])
    expect(JSON.parse(await h.tools.update_selection({ action: 'remove', items: `${first},${third}` })).result).toEqual({ asset_ids: [second], selection_count: 1 })
    expect(JSON.parse(await h.tools.update_selection({ action: 'replace', items: third })).result).toEqual({ asset_ids: [third], selection_count: 1 })
    expect(h.state.selected).toEqual(new Set([third!]))
  })

  it('clears without requiring or interpreting items', async () => {
    const h = harness()
    h.state.selected = new Set(h.ids.slice(0, 3))
    const original = h.state.selected
    expect(JSON.parse(await h.tools.update_selection({ action: 'clear', items: ['not-an-asset'] })).result).toEqual({ asset_ids: [], selection_count: 0 })
    expect(h.state.selected.size).toBe(0)
    expect(original.size).toBe(3)
    expect(JSON.parse(await h.tools.update_selection({ action: 'clear' })).ok).toBe(true)
  })

  it('rejects the entire add, remove, or replace when any ID is unknown', async () => {
    for (const action of ['add', 'remove', 'replace']) {
      const h = harness()
      h.state.selected = new Set([h.ids[0]!])
      const original = h.state.selected
      const result = JSON.parse(await h.tools.update_selection({ action, items: `${h.ids[1]},missing-asset` }))
      expect(result.ok).toBe(false)
      expect(result.error.code).toBe('not_found')
      expect(h.selections).toEqual([])
      expect(h.state.selected).toBe(original)
      expect([...original]).toEqual([h.ids[0]!])
    }
  })

  it('requires IDs rather than asset names or differently cased IDs', async () => {
    const h = harness()
    const asset = h.state.model!.asset.get(h.ids[0]!)!
    for (const items of [asset.name, asset.id.toUpperCase()]) {
      expect(JSON.parse(await h.tools.update_selection({ action: 'add', items })).error.code).toBe('not_found')
    }
    expect(h.selections).toEqual([])
  })

  it('rejects malformed actions and items before any mutation', async () => {
    const h = harness()
    const invalid = [undefined, null, [], 'add', {}, { action: 'toggle', items: h.ids[0] },
      { action: 'add' }, { action: 'add', items: [] }, { action: 'add', items: '' },
      { action: 'add', items: '  ' }, { action: 'add', items: `${h.ids[0]},,${h.ids[1]}` }]
    for (const args of invalid) {
      expect(JSON.parse(await h.tools.update_selection(args)).error.code).toBe('invalid_args')
    }
    expect(h.selections).toEqual([])
  })

  it('bounds requests to 100 entries and preserves count and whole IDs in a compact result', async () => {
    const h = harness()
    const requested = h.ids.slice(0, 100)
    const serialized = await h.tools.update_selection({ action: 'replace', items: requested.join(',') })
    const result = JSON.parse(serialized)
    expect(result.ok).toBe(true)
    expect(serialized.length).toBeLessThanOrEqual(1500)
    expect(result.result.selection_count).toBe(100)
    expect(result.result.details_in_app).toBe(true)
    expect(result.result.asset_ids.length).toBeGreaterThan(0)
    expect(result.result.asset_ids.every((id: string) => requested.includes(id))).toBe(true)
    expect(result.result.omitted_asset_count + result.result.asset_ids.length).toBe(100)
    expect(h.state.selected).toEqual(new Set(requested))
    expect(JSON.parse(await h.tools.update_selection({ action: 'replace', items: h.ids.slice(0, 101).join(',') })).error.code).toBe('invalid_args')
    expect(h.selections).toHaveLength(1)
    expect(h.state.selected).toEqual(new Set(requested))
  })

  it('resolves the live model and selection instead of capturing initial values', async () => {
    const h = harness()
    await h.tools.update_selection({ action: 'add', items: h.ids[0] })
    h.state.selected = new Set([h.ids[2]!])
    await h.tools.update_selection({ action: 'add', items: h.ids[1] })
    expect([...h.state.selected]).toEqual([h.ids[2]!, h.ids[1]!])
    const next = snapshot()
    next.building.assets[0]!.id = 'new-building-exact-asset'
    h.state.model = buildModel(next)
    const result = JSON.parse(await h.tools.update_selection({ action: 'replace', items: h.ids[0] }))
    expect(result.error.code).toBe('not_found')
    expect(h.selections).toHaveLength(2)
    expect(JSON.parse(await h.tools.update_selection({ action: 'replace', items: 'new-building-exact-asset' })).result.asset_ids).toEqual(['new-building-exact-asset'])
  })
})

describe('desk voice floor focus', () => {
  it('accepts real floor IDs, names ignoring case, and logical levels', async () => {
    const h = harness()
    const [ground, upper] = h.state.model!.floors
    for (const floor of [upper!.id, ` ${upper!.name.toUpperCase()} `, String(upper!.level)]) {
      expect(JSON.parse(await h.tools.focus_floor({ floor }))).toEqual({ ok: true, speech: `Showing ${upper!.name}.`, result: { floor_id: upper!.id, name: upper!.name } })
    }
    expect(JSON.parse(await h.tools.focus_floor({ floor: String(ground!.level) })).result.floor_id).toBe(ground!.id)
    expect(h.floors).toEqual([upper!.id, upper!.id, upper!.id, ground!.id])
    expect(h.selections).toEqual([])
  })

  it('prioritizes an exact ID over another floor with that name', async () => {
    const data = snapshot()
    data.building.floors[0]!.name = data.building.floors[1]!.id
    const h = harness(data)
    const id = data.building.floors[1]!.id
    expect(JSON.parse(await h.tools.focus_floor({ floor: id })).result.floor_id).toBe(id)
    expect(h.floors).toEqual([id])
  })

  it('uses signed logical levels and not array positions', async () => {
    const data = snapshot()
    data.building.floors[0]!.level = -2
    data.building.floors[1]!.level = 7
    const h = harness(data)
    expect(JSON.parse(await h.tools.focus_floor({ floor: '-2' })).result.floor_id).toBe(data.building.floors[0]!.id)
    expect(JSON.parse(await h.tools.focus_floor({ floor: '+7' })).result.floor_id).toBe(data.building.floors[1]!.id)
    expect(JSON.parse(await h.tools.focus_floor({ floor: '1' })).ok).toBe(false)
    expect(h.floors).toHaveLength(2)
  })

  it('rejects ambiguous names and levels without changing the displayed floor', async () => {
    for (const query of ['workshop', '3']) {
      const data = snapshot()
      for (const floor of data.building.floors) { floor.name = 'Workshop'; floor.level = 3 }
      const h = harness(data)
      const result = JSON.parse(await h.tools.focus_floor({ floor: query }))
      expect(result.ok).toBe(false)
      expect(result.error.code).toBe('ambiguous')
      expect(result.error.candidates).toEqual(data.building.floors.map(({ id, name, level }) => ({ id, name, level })))
      expect(h.floors).toEqual([])
    }
  })

  it('returns actual candidates for unknown floors without making a fuzzy choice', async () => {
    const h = harness()
    for (const floor of ['upstairs', 'Ground', '999', 'Infinity', '0x1']) {
      const serialized = await h.tools.focus_floor({ floor })
      const result = JSON.parse(serialized)
      expect(result.ok).toBe(false)
      expect(result.error.code).toBe('not_found')
      expect(result.error.candidates).toEqual(h.state.model!.floors.map(({ id, name, level }) => ({ id, name, level })))
      expect(serialized.length).toBeLessThanOrEqual(1500)
    }
    expect(h.floors).toEqual([])
  })

  it('rejects malformed floor arguments', async () => {
    const h = harness()
    for (const args of [undefined, null, [], '0', {}, { floor: 0 }, { floor: '' }, { floor: '  ' }]) {
      expect(JSON.parse(await h.tools.focus_floor(args)).error.code).toBe('invalid_args')
    }
    expect(h.floors).toEqual([])
  })
})

describe('desk voice context', () => {
  it('keeps browser-only tools separate from the server contract', () => {
    const h = harness()
    expect(Object.keys(h.tools)).toEqual(['update_selection', 'focus_floor'])
    expect(TOOL_NAMES).toHaveLength(17)
    expect(TOOL_NAMES as readonly string[]).not.toContain('update_selection')
    expect(TOOL_NAMES as readonly string[]).not.toContain('focus_floor')
  })

  it('does not mutate selection or floor when the current building is unavailable', async () => {
    const h = harness()
    h.state.selected = new Set([h.ids[0]!])
    const original = h.state.selected
    h.state.model = null
    for (const action of ['add', 'remove', 'replace', 'clear']) {
      expect(JSON.parse(await h.tools.update_selection({ action, items: h.ids[0] })).error.code).toBe('not_available')
    }
    expect(JSON.parse(await h.tools.focus_floor({ floor: '0' })).error.code).toBe('not_available')
    expect(h.state.selected).toBe(original)
    expect([...original]).toEqual([h.ids[0]!])
    expect(h.selections).toEqual([])
    expect(h.floors).toEqual([])
  })
})
