import { expect, test } from 'bun:test'
import { buildModel } from '../map/model'
import type { Session, Snapshot } from '../api/types'
import fixture from '../mocks/data/building_proc-factory-dev-003.json'
import { deskVoiceContext } from './deskContext'

test('desk voice context shares current grounded selection without session credentials', () => {
  const model = buildModel(fixture as unknown as Snapshot)
  const asset = model.snapshot.building.assets[0]!
  const session = { session_id: 'private-bearer-must-not-leave-app', building_id: model.snapshot.building.building.id, device: 'desk', role: 'navigator', profile: 'wheelchair', position: { space_id: asset.space_id, floor_id: asset.floor_id, source: 'desk', confidence: 'medium' }, constraints: { step_free: true, min_door_width_m: 0, closed: [], no_transit_room_types: [] }, active_tour_id: null } as Session
  const value = deskVoiceContext(model, session, asset.floor_id, new Set([asset.id, 'unknown-id']), null)
  expect(value).not.toContain(session.session_id)
  expect(value).not.toContain('unknown-id')
  const data = JSON.parse(value.slice(value.indexOf('{')))
  expect(data.surface).toBe('planning_desk')
  expect(data.selected_parts).toEqual([{ id: asset.id, name: asset.name, floor_id: asset.floor_id }])
  expect(data.profile).toBe('wheelchair')
  expect(data.constraints.step_free).toBe(true)
  expect(data.floors).toHaveLength(model.floors.length)
  expect(data.position.space_id).toBe(asset.space_id)
  expect(data.available_ui_actions).toEqual(['update_selection', 'focus_floor'])
})
