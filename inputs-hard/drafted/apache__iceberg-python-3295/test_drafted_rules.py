import copy
from hypothesis import given, strategies as st
from pyiceberg.expressions import And, AlwaysFalse, AlwaysTrue, EqualTo, GreaterThan, Not, Or

def _leaf(name, value):
    return EqualTo(name, value)
leaf_strategy = st.builds(lambda n, v: _leaf(n, v), st.sampled_from(['x', 'y', 'z', 'a']), st.integers(min_value=-1000, max_value=1000))
expr_strategy = st.recursive(leaf_strategy, lambda children: st.one_of(st.builds(lambda a, b: And(a, b), children, children), st.builds(lambda a, b: Or(a, b), children, children), st.builds(lambda a: Not(a), children)), max_leaves=8)

def test_deepcopy_and_from_issue():
    """Deep-copying And(EqualTo("x", 1), EqualTo("y", 2)) does not raise and gives an equal expression."""
    expr = And(EqualTo('x', 1), EqualTo('y', 2))
    result = copy.deepcopy(expr)
    assert result == expr
    assert isinstance(result, And)

def test_deepcopy_or():
    """Deep-copying an Or expression does not raise and gives an equal expression."""
    expr = Or(EqualTo('x', 1), EqualTo('y', 2))
    result = copy.deepcopy(expr)
    assert result == expr
    assert isinstance(result, Or)

def test_deepcopy_not():
    """Deep-copying a Not expression does not raise and gives an equal expression."""
    expr = Not(EqualTo('x', 1))
    result = copy.deepcopy(expr)
    assert result == expr
    assert isinstance(result, Not)

def test_deepcopy_is_independent_object():
    """A deep copy of a compound expression is a distinct object from the original."""
    expr = And(EqualTo('x', 1), EqualTo('y', 2))
    result = copy.deepcopy(expr)
    assert result is not expr

@given(expr_strategy)
def test_deepcopy_equals_original_for_any_expression(expr):
    """For any expression built from And, Or, Not and predicates, deepcopy succeeds and equals the original."""
    result = copy.deepcopy(expr)
    assert result == expr
    assert type(result) is type(expr)
    assert str(result) == str(expr)

@given(expr_strategy)
def test_deepcopy_hash_matches_original(expr):
    """A deep copy of any expression has the same hash as the original."""
    assert hash(copy.deepcopy(expr)) == hash(expr)