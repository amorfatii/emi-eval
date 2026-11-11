from __future__ import annotations
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st
from graphistry.compute.exceptions import GFQLValidationError
from graphistry.tests.compute.gfql.cypher.test_lowering import _mk_graph, _to_pandas_df

def _ab_graph(a_ids, b_ids, edges):
    nodes = pd.DataFrame({'id': list(a_ids) + list(b_ids), 'label__A': [True] * len(a_ids) + [False] * len(b_ids), 'label__B': [False] * len(a_ids) + [True] * len(b_ids)})
    edge_df = pd.DataFrame({'s': [s for s, _ in edges], 'd': [d for _, d in edges], 'type': ['R'] * len(edges)})
    return _mk_graph(nodes, edge_df)
_SHAPE_A = 'MATCH (a:A)-[:R]->(b:B) WITH a.id AS a_id, b.id AS b_id RETURN a_id, b_id'

def test_shape_a_projects_properties_of_two_match_aliases_through_with() -> None:
    """Shape A (MATCH (a:A)-[:R]->(b:B) WITH a.id AS a_id, b.id AS b_id RETURN a_id, b_id) is admitted and returns one row per matched path."""
    g = _ab_graph([1, 2], [10, 20, 30], [(1, 10), (1, 20), (2, 30)])
    result = g.gfql(_SHAPE_A)
    df = _to_pandas_df(result._nodes)
    got = sorted(zip(df['a_id'].tolist(), df['b_id'].tolist()))
    assert got == [(1, 10), (1, 20), (2, 30)]

def test_shape_a_result_has_only_the_projected_columns() -> None:
    """Shape A returns a row table containing exactly the columns a_id and b_id, with no hidden carry columns."""
    g = _ab_graph([1, 2], [10, 20], [(1, 10), (2, 20)])
    df = _to_pandas_df(g.gfql(_SHAPE_A)._nodes)
    assert list(df.columns) == ['a_id', 'b_id']

def test_shape_a_ignores_edges_that_do_not_match_the_pattern() -> None:
    """Shape A yields no rows when no A-to-B path of type R exists."""
    g = _ab_graph([1], [10], [])
    df = _to_pandas_df(g.gfql(_SHAPE_A)._nodes)
    assert len(df) == 0

@settings(max_examples=40, deadline=None)
@given(st.sets(st.tuples(st.integers(0, 4), st.integers(100, 104)), max_size=15))
def test_shape_a_returns_exactly_one_row_per_matched_path(edge_set) -> None:
    """For every graph, shape A returns one row per matched A-to-B path, holding that path's two ids and no other columns."""
    edges = sorted(edge_set)
    g = _ab_graph(list(range(5)), list(range(100, 105)), edges)
    df = _to_pandas_df(g.gfql(_SHAPE_A)._nodes)
    assert list(df.columns) == ['a_id', 'b_id']
    got = sorted(zip(df['a_id'].tolist(), df['b_id'].tolist()))
    assert got == edges