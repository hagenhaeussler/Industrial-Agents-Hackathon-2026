import type { Floor } from '../api/types'
import type { Model } from '../map/model'
import { serializeToolResponse } from './clientTools'
import type { ToolResponse } from './clientTools'

export type DeskVoiceToolOptions = {
  getModel: () => Model | null
  getSelected: () => ReadonlySet<string>
  onSelection: (ids: Set<string>) => void
  onFloor: (id: string) => void
}

const MAX_ITEMS = 100
const MAX_RESPONSE = 1500
const unavailable = 'Choose a building and wait for it to load first.'

function failure(message: string, code = 'invalid_args', candidates?: unknown[]): string {
  return serializeToolResponse({ ok: false, speech: message, error: { code, message, ...(candidates ? { candidates } : {}) } })
}

function argumentsOf(input: unknown): Record<string, unknown> | null {
  return input !== null && typeof input === 'object' && !Array.isArray(input)
    ? input as Record<string, unknown> : null
}

/** Keep whole IDs and the total count even when a large selection exceeds voice's limit. */
function selectionResponse(ids: string[]): string {
  const response: ToolResponse = {
    ok: true,
    speech: ids.length ? `${ids.length} ${ids.length === 1 ? 'item is' : 'items are'} selected.` : 'The selection is clear.',
    result: { asset_ids: ids, selection_count: ids.length },
  }
  if (JSON.stringify(response).length <= MAX_RESPONSE) return serializeToolResponse(response)
  const included: string[] = []
  const result = { asset_ids: included, selection_count: ids.length, details_in_app: true, omitted_asset_count: ids.length }
  response.result = result
  for (const id of ids) {
    included.push(id)
    result.omitted_asset_count = ids.length - included.length
    if (JSON.stringify(response).length > MAX_RESPONSE) {
      included.pop()
      result.omitted_asset_count++
      break
    }
  }
  return serializeToolResponse(response)
}

function floorCandidates(floors: readonly Floor[]) {
  return floors.slice(0, 8).map(({ id, name, level }) => ({ id, name, level }))
}

/** Browser-only desk actions. These do not extend the server's eleven-tool contract. */
export function createDeskVoiceTools({ getModel, getSelected, onSelection, onFloor }: DeskVoiceToolOptions) {
  return {
    update_selection: async (input?: unknown): Promise<string> => {
      const args = argumentsOf(input)
      if (!args || !['add', 'remove', 'replace', 'clear'].includes(args.action as string)) {
        return failure('Choose a selection action: add, remove, replace, or clear.')
      }
      try {
        const model = getModel()
        if (!model) return failure(unavailable, 'not_available')
        if (args.action === 'clear') {
          onSelection(new Set())
          return selectionResponse([])
        }
        if (typeof args.items !== 'string' || !args.items.trim()) {
          return failure('Provide exact asset IDs in a comma-separated items string.')
        }
        const items = args.items.split(',').map(id => id.trim())
        if (items.length > MAX_ITEMS || items.some(id => !id)) {
          return failure(`Provide between 1 and ${MAX_ITEMS} exact asset IDs without empty entries.`)
        }
        if (items.some(id => !model.asset.has(id))) {
          return failure('Some asset IDs are not in this building. Use find to get their exact IDs.', 'not_found')
        }
        const selected = args.action === 'replace' ? new Set<string>() : new Set(getSelected())
        for (const id of items) {
          if (args.action === 'remove') selected.delete(id)
          else selected.add(id)
        }
        const result = selectionResponse([...selected])
        onSelection(selected)
        return result
      } catch {
        return failure('The selection could not be updated. Please try again.', 'not_available')
      }
    },
    focus_floor: async (input?: unknown): Promise<string> => {
      const args = argumentsOf(input)
      if (!args || typeof args.floor !== 'string' || !args.floor.trim()) {
        return failure('Provide a floor ID, its exact name, or its logical level.')
      }
      try {
        const model = getModel()
        if (!model) return failure(unavailable, 'not_available')
        const query = args.floor.trim()
        const exact = model.floor.get(query)
        let matches = exact ? [exact] : model.floors.filter(floor => floor.name.toLowerCase() === query.toLowerCase())
        if (!matches.length && /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(query)) {
          const level = Number(query)
          matches = model.floors.filter(floor => floor.level === level)
        }
        if (matches.length !== 1) {
          return failure(
            matches.length ? 'More than one floor matches. Choose an exact floor ID.' : 'That floor is not in this building. Choose one of the available floors.',
            matches.length ? 'ambiguous' : 'not_found',
            floorCandidates(matches.length ? matches : model.floors),
          )
        }
        const floor = matches[0]!
        const response = serializeToolResponse({ ok: true, speech: `Showing ${floor.name}.`, result: { floor_id: floor.id, name: floor.name } })
        onFloor(floor.id)
        return response
      } catch {
        return failure('The floor could not be shown. Please try again.', 'not_available')
      }
    },
  }
}
