import { describe, expect, test } from 'bun:test';
import type { Building, ReachableRoute, Snapshot, Tour } from '../api/types';
import campus from '../../../../data/dev/proc-campus-dev-013/building.json';
import factorySnapshot from '../mocks/data/building_proc-factory-dev-003.json';
import factoryTour from '../mocks/data/tour_proc-factory-dev-003.json';
import { anchorOf, buildModel, stopMarks } from './model';

// Real core.tour.plan_tour captures on proc-campus-dev-013; no question/gold files were read.
// stairs: Main lobby -> Fire extinguisher 2.10 (terminal stair segment).
// lift: ground Lift 1 -> Floor 2 Lift 1, step-free (terminal lift segment).
// zero: explicit same-room point [-3.1,35.4] -> itself (zero-length one-point walk).
const captured = {"stairs":{"tour_id":null,"revision":1,"status":"active","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","profile":"kit_1_1_0","constraints":{"step_free":false,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"building_closed":[],"order_policy":"optimized_exact","start":{"space_id":"proc-campus-dev-013-F0-S014","floor_id":"proc-campus-dev-013-F0","point":[-11.4,2.44],"source":"desk"},"end":null,"stops":[{"stop_id":"s1","space_id":"proc-campus-dev-013-F2-S010","asset_ids":["proc-campus-dev-013-A00319"],"label":"Fire extinguisher 2.10 \u00b7 Staircase 2","status":"pending"}],"order":["s1"],"legs":[{"from_space_id":"proc-campus-dev-013-F0-S014","to_space_id":"proc-campus-dev-013-F2-S010","constraints":{"step_free":false,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"profile":"kit_1_1_0","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","reachable":true,"length_m":54.83,"length_m_exact":54.826,"space_path":["proc-campus-dev-013-F0-S014","proc-campus-dev-013-F0-S001","proc-campus-dev-013-F0-S010","proc-campus-dev-013-F1-S010","proc-campus-dev-013-F2-S010"],"node_path":["proc-campus-dev-013-F0-S014","door:proc-campus-dev-013-F0-O0013","door:proc-campus-dev-013-F0-O0009","proc-campus-dev-013-F0-S010","proc-campus-dev-013-F1-S010","proc-campus-dev-013-F2-S010"],"element_path":["proc-campus-dev-013-F0-O0013","proc-campus-dev-013-F0-O0009","proc-campus-dev-013-V03","proc-campus-dev-013-V03"],"segments":[{"floor_id":"proc-campus-dev-013-F0","kind":"walk","space_id":"proc-campus-dev-013-F0-S014","points":[[-11.4,2.44],[-8.700000000000001,2.4429999999999996],[-8.4,2.443]],"length_m":3.0,"geometry_length_m":3.000001666666152,"fallback":false,"from_node":"proc-campus-dev-013-F0-S014","to_node":"door:proc-campus-dev-013-F0-O0013","endpoint_stubs":[false,true]},{"floor_id":"proc-campus-dev-013-F0","kind":"walk","space_id":"proc-campus-dev-013-F0-S001","points":[[-8.4,2.443],[-8.1,2.443],[-6.3,35.42],[-6.0,35.42]],"length_m":33.626,"geometry_length_m":33.626088611883794,"fallback":false,"from_node":"door:proc-campus-dev-013-F0-O0013","to_node":"door:proc-campus-dev-013-F0-O0009","endpoint_stubs":[true,true]},{"floor_id":"proc-campus-dev-013-F0","kind":"walk","space_id":"proc-campus-dev-013-F0-S010","points":[[-6.0,35.42],[-5.7,35.42],[-3.0,35.42]],"length_m":3.0,"geometry_length_m":3.0,"fallback":false,"from_node":"door:proc-campus-dev-013-F0-O0009","to_node":"proc-campus-dev-013-F0-S010","endpoint_stubs":[true,false]},{"floor_id":"proc-campus-dev-013-F0","kind":"stairs","element_id":"proc-campus-dev-013-V03","points":[[-3.0,35.42]],"to_floor_id":"proc-campus-dev-013-F1","length_m":7.6,"to_point":[-3.0,35.42]},{"floor_id":"proc-campus-dev-013-F1","kind":"stairs","element_id":"proc-campus-dev-013-V03","points":[[-3.0,35.42]],"to_floor_id":"proc-campus-dev-013-F2","length_m":7.6,"to_point":[-3.0,35.42]}],"start_position":[-11.4,2.44],"destination_position":[-3.0,35.42],"maneuvers":[{"i":0,"kind":"depart","floor_id":"proc-campus-dev-013-F0","at":[-11.4,2.44],"distance_m":0,"text":"Start in Main lobby.","landmark":null,"element_id":null},{"i":1,"kind":"turn_left","floor_id":"proc-campus-dev-013-F0","at":[-8.4,2.443],"distance_m":3.0,"text":"Turn left into Corridor 0.01.","landmark":"Corridor 0.01","element_id":"proc-campus-dev-013-F0-O0013"},{"i":2,"kind":"turn_right","floor_id":"proc-campus-dev-013-F0","at":[-6.0,35.42],"distance_m":33.63,"text":"Turn right into Staircase 2.","landmark":"Staircase 2","element_id":"proc-campus-dev-013-F0-O0009"},{"i":3,"kind":"take_stairs","floor_id":"proc-campus-dev-013-F0","at":[-3.0,35.42],"distance_m":3.0,"text":"Take the Staircase 2 to Floor 2.","landmark":"Staircase 2","element_id":"proc-campus-dev-013-V03"},{"i":4,"kind":"arrive","floor_id":"proc-campus-dev-013-F2","at":[-3.0,35.42],"distance_m":15.2,"text":"You have arrived at Staircase 2.","landmark":null,"element_id":null}]}],"length_m":54.83,"length_m_exact":54.826,"unreachable_stops":[],"changed_because":null,"reachable":true},"lift":{"tour_id":null,"revision":1,"status":"active","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","profile":"kit_1_1_0","constraints":{"step_free":true,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"building_closed":[],"order_policy":"optimized_exact","start":{"space_id":"proc-campus-dev-013-F0-S005","floor_id":"proc-campus-dev-013-F0","point":[-3.0,14.22],"source":"desk"},"end":null,"stops":[{"stop_id":"s1","space_id":"proc-campus-dev-013-F2-S005","asset_ids":[],"label":"Lift 1","status":"pending"}],"order":["s1"],"legs":[{"from_space_id":"proc-campus-dev-013-F0-S005","to_space_id":"proc-campus-dev-013-F2-S005","constraints":{"step_free":true,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"profile":"kit_1_1_0","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","reachable":true,"length_m":22.6,"length_m_exact":22.6,"space_path":["proc-campus-dev-013-F0-S005","proc-campus-dev-013-F2-S005"],"node_path":["proc-campus-dev-013-F0-S005","proc-campus-dev-013-F2-S005"],"element_path":["proc-campus-dev-013-V02"],"segments":[{"floor_id":"proc-campus-dev-013-F0","kind":"lift","element_id":"proc-campus-dev-013-V02","points":[[-3.0,14.22]],"to_floor_id":"proc-campus-dev-013-F2","length_m":22.6,"to_point":[-3.0,14.22]}],"start_position":[-3.0,14.22],"destination_position":[-3.0,14.22],"maneuvers":[{"i":0,"kind":"depart","floor_id":"proc-campus-dev-013-F0","at":[-3.0,14.22],"distance_m":0,"text":"Start in Lift 1.","landmark":null,"element_id":null},{"i":1,"kind":"take_lift","floor_id":"proc-campus-dev-013-F0","at":[-3.0,14.22],"distance_m":0.0,"text":"Take the Lift 1 to Floor 2.","landmark":"Lift 1","element_id":"proc-campus-dev-013-V02"},{"i":2,"kind":"arrive","floor_id":"proc-campus-dev-013-F2","at":[-3.0,14.22],"distance_m":22.6,"text":"You have arrived at Lift 1.","landmark":null,"element_id":null}]}],"length_m":22.6,"length_m_exact":22.6,"unreachable_stops":[],"changed_because":null,"reachable":true},"zero":{"tour_id":null,"revision":1,"status":"active","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","profile":"kit_1_1_0","constraints":{"step_free":false,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"building_closed":[],"order_policy":"optimized_exact","start":{"space_id":"proc-campus-dev-013-F2-S010","floor_id":"proc-campus-dev-013-F2","point":[-3.1,35.4],"source":"desk"},"end":null,"stops":[{"stop_id":"s1","space_id":"proc-campus-dev-013-F2-S010","asset_ids":[],"label":"Staircase 2","status":"pending","point":[-3.1,35.4]}],"order":["s1"],"legs":[{"from_space_id":"proc-campus-dev-013-F2-S010","to_space_id":"proc-campus-dev-013-F2-S010","constraints":{"step_free":false,"min_door_width_m":0.0,"closed":[],"no_transit_room_types":[]},"profile":"kit_1_1_0","building_id":"proc-campus-dev-013","building_version":0,"content_hash":"sha256:e867a1668c8b8745","reachable":true,"length_m":0.0,"length_m_exact":0.0,"space_path":["proc-campus-dev-013-F2-S010"],"node_path":["proc-campus-dev-013-F2-S010","proc-campus-dev-013-F2-S010"],"element_path":[],"segments":[{"floor_id":"proc-campus-dev-013-F2","kind":"walk","space_id":"proc-campus-dev-013-F2-S010","points":[[-3.1,35.4]],"length_m":0.0,"geometry_length_m":0.0,"fallback":false,"from_node":"proc-campus-dev-013-F2-S010","to_node":"proc-campus-dev-013-F2-S010","endpoint_stubs":[false,false]}],"start_position":[-3.1,35.4],"destination_position":[-3.1,35.4],"maneuvers":[{"i":0,"kind":"depart","floor_id":"proc-campus-dev-013-F2","at":[-3.1,35.4],"distance_m":0,"text":"Start in Staircase 2.","landmark":null,"element_id":null},{"i":1,"kind":"arrive","floor_id":"proc-campus-dev-013-F2","at":[-3.1,35.4],"distance_m":0.0,"text":"You have arrived at Staircase 2.","landmark":null,"element_id":null}]}],"length_m":0.0,"length_m_exact":0.0,"unreachable_stops":[],"changed_because":null,"reachable":true}} as unknown as Record<'stairs' | 'lift' | 'zero', Tour>;
const model = buildModel({ building: campus as unknown as Building, building_version: 0,
  content_hash: captured.stairs.legs[0]!.content_hash, closed: [], derived: { anchors: {}, areas_m2: {} } });
const reachable = (tour: Tour) => tour.legs.find((leg): leg is ReachableRoute => leg.reachable)!;

describe('stop marker arrival placement', () => {
  for (const kind of ['stairs', 'lift'] as const) {
    test(`a terminal ${kind} arrival stays on the actual destination floor`, () => {
      const tour = structuredClone(captured[kind]);
      const before = JSON.stringify(tour);
      const leg = reachable(tour);
      expect(leg.segments.at(-1)!.kind).toBe(kind);
      const arrival = leg.maneuvers.at(-1)!;
      const mark = stopMarks(model, tour)[0]!;
      expect(arrival.kind).toBe('arrive');
      expect(mark.floorId).toBe(model.space.get(mark.spaceId)!.floor_id);
      expect(mark.floorId).toBe(arrival.floor_id);
      expect(mark.point).toEqual(arrival.at);
      expect(mark.floorId).not.toBe(tour.start.floor_id);
      expect(JSON.stringify(tour)).toBe(before);
    });
  }

  test('a zero-length route without segments uses its explicit core arrival point', () => {
    const tour = structuredClone(captured.zero);
    const leg = reachable(tour);
    // Legacy zero-length payloads may omit that single-point walk entirely.
    leg.segments = [];
    const before = JSON.stringify(tour);
    expect(leg.segments).toEqual([]);
    expect(leg.length_m).toBe(0);
    const mark = stopMarks(model, tour)[0]!;
    expect(mark.point).toEqual([-3.1, 35.4]);
    expect(mark.point).not.toEqual(anchorOf(model, mark.spaceId));
    expect(mark.floorId).toBe(model.space.get(mark.spaceId)!.floor_id);
    expect(JSON.stringify(tour)).toBe(before);
  });

  test('an arrival on the wrong floor cannot pull a terminal-stair stop down to its last walk', () => {
    const tour = structuredClone(captured.stairs);
    const leg = reachable(tour);
    const lastWalk = [...leg.segments].reverse().find(segment => segment.kind === 'walk')!;
    leg.maneuvers.at(-1)!.floor_id = tour.start.floor_id;
    const before = JSON.stringify(tour);
    const mark = stopMarks(model, tour)[0]!;
    expect(lastWalk.floor_id).toBe(tour.start.floor_id);
    expect(mark.floorId).toBe(model.space.get(mark.spaceId)!.floor_id);
    expect(mark.point).toEqual(anchorOf(model, mark.spaceId));
    expect(mark.floorId).not.toBe(lastWalk.floor_id);
    expect(JSON.stringify(tour)).toBe(before);
  });

  test('ordinary walking arrival remains unchanged; legacy walks fall back only on the target floor', () => {
    const factory = buildModel(factorySnapshot as unknown as Snapshot);
    const tour = structuredClone(factoryTour) as unknown as Tour;
    const before = JSON.stringify(tour);
    const marks = stopMarks(factory, tour);
    for (const mark of marks) {
      const leg = tour.legs.find((item): item is ReachableRoute => item.reachable && item.to_space_id === mark.spaceId)!;
      const arrive = leg.maneuvers.at(-1)!;
      expect(mark.floorId).toBe(arrive.floor_id);
      expect(mark.point).toEqual(arrive.at);
    }
    expect(JSON.stringify(tour)).toBe(before);
    for (const leg of tour.legs) if (leg.reachable) leg.maneuvers = leg.maneuvers.filter(item => item.kind !== 'arrive');
    const legacyBefore = JSON.stringify(tour);
    for (const mark of stopMarks(factory, tour)) {
      const leg = tour.legs.find((item): item is ReachableRoute => item.reachable && item.to_space_id === mark.spaceId)!;
      const walk = [...leg.segments].reverse().find(segment => segment.kind === 'walk')!;
      expect(walk.floor_id).toBe(factory.space.get(mark.spaceId)!.floor_id);
      expect(mark.floorId).toBe(walk.floor_id);
      expect(mark.point).toEqual(walk.points.at(-1)!);
    }
    expect(JSON.stringify(tour)).toBe(legacyBefore);
  });

  test('missing arrival and walk data use the actual target anchor', () => {
    const tour = structuredClone(captured.zero);
    const leg = reachable(tour); leg.maneuvers = []; leg.segments = [];
    const before = JSON.stringify(tour);
    const mark = stopMarks(model, tour)[0]!;
    expect(mark.point).toEqual(anchorOf(model, mark.spaceId));
    expect(mark.floorId).toBe(model.space.get(mark.spaceId)!.floor_id);
    expect(JSON.stringify(tour)).toBe(before);
  });
});
