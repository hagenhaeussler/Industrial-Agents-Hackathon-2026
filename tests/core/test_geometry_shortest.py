"""Dense route geometry Dijkstra agrees with independent graph distances."""

import heapq
import math

import networkx as nx
import numpy as np
import pytest

from core.geometry import _shortest_path


def _heap_reference(matrix, source, target):
    """Previous implementation: retain its deterministic path tie policy."""
    distances, previous, queue = {source: 0.0}, {}, [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node == target:
            path = [target]
            while path[-1] != source:
                path.append(previous[path[-1]])
            return distance, path[::-1]
        for neighbour in np.flatnonzero(np.isfinite(matrix[node])):
            neighbour = int(neighbour)
            candidate = distance + float(matrix[node, neighbour])
            if candidate < distances.get(neighbour, math.inf):
                distances[neighbour], previous[neighbour] = candidate, node
                heapq.heappush(queue, (candidate, neighbour))
    return math.inf, []


@pytest.mark.parametrize("seed", range(12))
def test_random_directed_matrices_match_networkx_and_previous_ties(seed):
    rng = np.random.default_rng(seed)
    for size in (1, 2, 5, 16, 40):
        # Integers deliberately create ties and zero edges; inf is no edge.
        matrix = rng.integers(0, 15, size=(size, size)).astype(float)
        matrix[rng.random((size, size)) < .4] = np.inf
        np.fill_diagonal(matrix, 0)
        graph = nx.DiGraph()
        graph.add_nodes_from(range(size))
        graph.add_weighted_edges_from((a, b, float(matrix[a, b])) for a, b in zip(*np.nonzero(np.isfinite(matrix))))
        for source in sorted({0, size - 1, int(rng.integers(size))}):
            expected = nx.single_source_dijkstra_path_length(graph, source)
            for target in range(size):
                distance, path = _shortest_path(matrix, source, target)
                assert distance == expected.get(target, math.inf)
                assert (distance, path) == _heap_reference(matrix, source, target)
                if path:
                    assert (path[0], path[-1]) == (source, target)
                    assert len(path) == len(set(path))
                    assert sum(matrix[a, b] for a, b in zip(path, path[1:])) == distance
                else:
                    assert math.isinf(distance)


def test_zero_cycles_ties_unreachable_and_nonfinite_edges():
    matrix = np.array([[0, 0, 0, np.inf, np.inf],
                       [0, 0, 0, 2, np.inf],
                       [0, 0, 0, 2, np.inf],
                       [np.inf, np.inf, np.inf, 0, np.inf],
                       [np.inf, np.inf, np.inf, np.inf, 0]])
    assert _shortest_path(matrix, 0, 3) == (2, [0, 1, 3])
    assert _shortest_path(matrix, 0, 0) == (0, [0])
    assert _shortest_path(matrix, 0, 4) == (math.inf, [])
    matrix[0, 4] = np.nan
    matrix[1, 4] = -np.inf
    assert _shortest_path(matrix, 0, 4) == (math.inf, [])
