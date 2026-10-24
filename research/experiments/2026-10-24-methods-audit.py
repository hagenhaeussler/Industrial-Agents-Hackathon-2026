"""Bounded research experiments; does not modify buildings or run an LLM.

Usage: python methods_audit.py --repo /path/to/team/repo --output results.json
Requires: numpy==2.5.4 scipy==1.18.0 networkx==3.7 shapely==2.2.0
"""
import argparse
import importlib.metadata
import json
import math
import platform
import random
import statistics
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import dijkstra


def timed_ms(call, repeats=5):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        values.append(1000 * (time.perf_counter() - start))
    return statistics.median(values)


def min_cost_csr(graph):
    """Numeric-only experiment adapter, not a production portal/path adapter."""
    nodes = list(graph)
    node_index = {node: i for i, node in enumerate(nodes)}
    weights = {}
    for u, v, attrs in graph.edges(data=True):
        i, j = node_index[u], node_index[v]
        cost = float(attrs['weight'])
        assert math.isfinite(cost) and cost >= 0
        for key in ((i, j), (j, i)):
            weights[key] = min(weights.get(key, math.inf), cost)
    pairs = list(weights)
    rows = np.asarray([p[0] for p in pairs], dtype=np.int32)
    cols = np.asarray([p[1] for p in pairs], dtype=np.int32)
    values = np.asarray([weights[p] for p in pairs], dtype=np.float64)
    matrix = csr_array((values, (rows, cols)), shape=(len(nodes), len(nodes)))
    return matrix, nodes, node_index


def astar_counterexample():
    points = {'s': (0, 0), 'a': (0, 1), 'b': (100, 0), 't': (100, 1)}
    graph = nx.Graph()
    graph.add_weighted_edges_from([
        ('s', 't', math.dist(points['s'], points['t'])),
        ('s', 'a', 1), ('a', 'b', 0), ('b', 't', 1),
    ])
    path = nx.astar_path(graph, 's', 't', heuristic=lambda a, b: math.dist(points[a], points[b]))
    optimal = nx.shortest_path_length(graph, 's', 't', weight='weight')
    actual = nx.path_weight(graph, path, 'weight')
    assert optimal == 2 and actual > optimal
    return {'astar_path': path, 'astar_cost': actual, 'dijkstra_cost': optimal,
            'zero_edge': 'a-b models the free entrance-to-entrance shortcut'}


def sparse_traps():
    graph = nx.MultiGraph()
    graph.add_edge('a', 'b', weight=1)
    graph.add_edge('a', 'b', weight=4)
    naive = nx.to_scipy_sparse_array(graph, nodelist=['a', 'b'], format='csr', dtype=float)
    correct, _, _ = min_cost_csr(graph)
    zero_graph = csr_array((np.array([0., 1., 5.]),
                           (np.array([0, 1, 0], dtype=np.int32),
                            np.array([1, 2, 2], dtype=np.int32))), shape=(3, 3))
    before = float(dijkstra(zero_graph, directed=True, indices=0)[2])
    zero_graph.eliminate_zeros()
    after = float(dijkstra(zero_graph, directed=True, indices=0)[2])
    assert float(naive[0, 1]) == 5 and float(correct[0, 1]) == 1
    assert before == 1 and after == 5
    return {'parallel_edge_weights': [1, 4], 'naive_export_weight': float(naive[0, 1]),
            'min_export_weight': float(correct[0, 1]),
            'explicit_zero_route_cost': before, 'after_eliminate_zeros_cost': after}


def insertion_formula_check():
    rng = random.Random(20261024)
    checks = 0
    for _ in range(25):
        graph = nx.Graph()
        graph.add_nodes_from(range(18))
        for a in range(18):
            for b in range(a + 1, 18):
                if rng.random() < .13:
                    graph.add_edge(a, b, weight=rng.randrange(13))
        exits = {0, 17}
        a, b = rng.sample(range(18), 2)
        w = rng.randrange(11)
        old = nx.multi_source_dijkstra_path_length(graph, exits)
        da = nx.single_source_dijkstra_path_length(graph, a)
        db = nx.single_source_dijkstra_path_length(graph, b)
        changed = graph.copy()
        changed.add_edge(a, b, weight=min(w, graph.get_edge_data(a, b, {}).get('weight', math.inf)))
        new = nx.multi_source_dijkstra_path_length(changed, exits)
        for v in graph:
            formula = min(old.get(v, math.inf),
                          da.get(v, math.inf) + w + old.get(b, math.inf),
                          db.get(v, math.inf) + w + old.get(a, math.inf))
            assert formula == new.get(v, math.inf)
            checks += 1
    return {'seed': 20261024, 'graphs': 25, 'vertex_checks': checks,
            'scope': 'One added undirected nonnegative edge; no other cost changes. Includes zero weights and disconnected vertices.'}


def building_benchmark(repo):
    sys.path.insert(0, str(repo))
    from starter_agent.building_map import BuildingMap
    best = None
    for path in sorted((repo / 'data').glob('*/*/building.json')):
        data = json.loads(path.read_text())
        score = len(data['spaces']) + len(data['openings'])
        if best is None or score > best[0]:
            best = (score, data, path)
    _, data, path = best
    model = BuildingMap(data)
    start = time.perf_counter()
    graph = model.graph(False)
    build_ms = 1000 * (time.perf_counter() - start)
    start = time.perf_counter()
    matrix, nodes, index = min_cost_csr(graph)
    export_ms = 1000 * (time.perf_counter() - start)
    sources = sorted(model.spaces)[::max(1, len(model.spaces) // 12)][:12]

    def cached_nx():
        return [nx.single_source_dijkstra_path_length(graph, s) for s in sources]

    def uncached_nx():
        return [nx.single_source_dijkstra_path_length(model.graph(False), s) for s in sources]

    def cached_sparse():
        return dijkstra(matrix, directed=True, indices=np.array([index[s] for s in sources], dtype=np.int32))

    expected = cached_nx()
    observed = cached_sparse()
    for row, values in enumerate(expected):
        target = np.array([values.get(n, math.inf) for n in nodes])
        assert np.allclose(target, observed[row], rtol=1e-12, atol=1e-10, equal_nan=False)

    return {'building': data['building']['id'], 'path': str(path.relative_to(repo)),
            'nodes': len(graph), 'multiedges': graph.number_of_edges(),
            'csr_stored_entries': matrix.nnz,
            'csr_numeric_buffer_bytes': matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes,
            'dense_float64_bytes': len(graph) ** 2 * 8,
            'sources': len(sources), 'compared_distances': len(sources) * len(graph),
            'distance_comparison': 'all matched within rtol=1e-12, atol=1e-10, including infinity',
            'one_graph_build_ms': build_ms, 'one_min_csr_export_ms': export_ms,
            'median_ms_12_sources': {'rebuild_graph_per_source_networkx': timed_ms(uncached_nx, 3),
                                     'cached_graph_networkx': timed_ms(cached_nx),
                                     'cached_csr_scipy': timed_ms(cached_sparse)},
            'timing_scope': 'Local in-process SSSP rows; includes no LLM, network, rendering or geodesic geometry. CSR node/edge/portal metadata memory excluded.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = {'platform': platform.platform(), 'python': platform.python_version(),
              'packages': {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'networkx', 'shapely']},
              'astar_counterexample': astar_counterexample(), 'sparse_traps': sparse_traps(),
              'edge_insertion': insertion_formula_check(), 'building_benchmark': building_benchmark(args.repo.resolve())}
    text = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(text + '\n')
    print(text)


if __name__ == '__main__':
    main()
