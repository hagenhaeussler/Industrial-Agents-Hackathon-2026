import copy
import itertools
import random

import pytest

from core.building import load_building
from core.tour import optimal_order, plan_tour, replan


def test_held_karp_matches_brute_force_with_optional_end():
    rng = random.Random(24)
    for end in (False, True):
        matrix = [[0 if i==j else rng.randrange(1,20) for j in range(7)] for i in range(7)]
        end_costs = [rng.randrange(1,20) for _ in range(6)] if end else None
        order, length = optimal_order(matrix,end_costs)
        def cost(seq):
            return matrix[0][seq[0]+1]+sum(matrix[a+1][z+1] for a,z in zip(seq,seq[1:]))+(end_costs[seq[-1]] if end else 0)
        assert length == min(cost(p) for p in itertools.permutations(range(6)))
        assert length == cost(order)


def test_merge_stops_and_preserve_progress_through_lift_outage_and_undo():
    b = load_building('data/dev/proc-factory-dev-003')
    assets = list(b.assets.values())
    start = next(o['space_ids'][0] if o['space_ids'][1]=='outside' else o['space_ids'][1]
                 for o in b.openings.values() if 'outside' in o['space_ids'])
    chosen = []
    spaces = set()
    for a in assets:
        if a['space_id'] not in spaces:
            chosen.append(a['id']); spaces.add(a['space_id'])
        if len(chosen)==3: break
    tour = plan_tour(b,start,chosen+chosen[:1],{'step_free':True})
    assert len(tour['stops'])==3
    tour['tour_id']='test-tour'
    first = tour['order'][0]
    next(s for s in tour['stops'] if s['stop_id']==first)['status']='collected'
    old = copy.deepcopy(tour)
    lift = next(iter(b.connectors))
    b.closed.add(lift)
    revised = replan(b,tour,start,{'event_id':'evt-1','summary':'Lift closed'})
    assert revised['revision']==2
    assert revised['tour_id']=='test-tour'
    assert next(s for s in revised['stops'] if s['stop_id']==first)['status']=='collected'
    assert first not in revised['order']
    assert tour == old
    assert lift not in revised['constraints']['closed']
    b.closed.clear()
    reopened = replan(b,revised,start)
    assert not reopened['unreachable_stops']


def test_pending_assets_retarget_when_moved():
    b = load_building('data/dev/proc-factory-dev-003')
    a = next(iter(b.assets.values()))
    destination = next(sid for sid in b.spaces if sid != a['space_id'])
    tour = plan_tour(b,a['space_id'],[a['id']])
    tour['stops'][0]['target'] = a['space_id']  # additive server field, stale after move
    sid = tour['stops'][0]['stop_id']
    a['space_id'] = destination
    revised = replan(b,tour,tour['start'])
    assert revised['stops'][0]['space_id']==destination
    assert revised['stops'][0]['stop_id']==sid


def test_thirteen_stops_are_explicitly_heuristic():
    b = load_building('data/dev/proc-factory-dev-003')
    start = next(iter(b.spaces))
    from core.routing import constrained_graph
    import networkx as nx
    reachable = nx.node_connected_component(constrained_graph(b),start)
    stops = [sid for sid in b.spaces if sid in reachable][:13]
    tour = plan_tour(b,start,stops)
    assert tour['order_policy']=='optimized_heuristic'
