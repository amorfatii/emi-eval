import pytest
from hypothesis import given, strategies as st

from stats import mean, median


# The median of [1, 2, 3, 4] is 2.5, the mean of the two middle values.
# Source: "median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values."
def test_request_example():
    assert median([1, 2, 3, 4]) == 2.5
    assert median([4, 1, 3, 2]) == 2.5
    assert median([1, 3]) == 2
    assert median([5, 5, 7, 9]) == 5


# For an even number of integers, the median is the mean of the two middle sorted values.
# Source: "The median of an even number of values is the mean of the two middle values."
@given(xs=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=40).map(lambda l: l + l[:1] if len(l) % 2 else l))
def test_even_integers(xs):
    assert len(xs) % 2 == 0
    s = sorted(xs)
    k = len(s) // 2
    assert median(xs) == (s[k - 1] + s[k]) / 2


# For an even number of floats, the median is (approximately) the mean of the two middle sorted values.
# Source: "The median of an even number of values is the mean of the two middle values."
@given(xs=st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False), min_size=2, max_size=40).filter(lambda l: len(l) % 2 == 0))
def test_even_floats(xs):
    s = sorted(xs)
    k = len(s) // 2
    assert median(xs) == pytest.approx((s[k - 1] + s[k]) / 2, rel=1e-9, abs=1e-9)


# For an odd number of values, the median is still the middle sorted value.
# Source: baseline behaviour, not asked to change: median of odd-length data returns the middle sorted value
@given(xs=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=41).filter(lambda l: len(l) % 2 == 1))
def test_odd_unchanged(xs):
    assert median(xs) == sorted(xs)[len(xs) // 2]


# The median of empty data raises ValueError.
# Source: baseline behaviour, not asked to change: median([]) raises ValueError
def test_empty_raises():
    with pytest.raises(ValueError):
        median([])


# median does not modify the list it is given.
# Source: baseline behaviour, not asked to change: median sorts a copy and leaves its input unchanged
@given(xs=st.lists(st.integers(min_value=-100, max_value=100), min_size=1, max_size=20))
def test_input_not_mutated(xs):
    before = list(xs)
    median(xs)
    assert xs == before


# mean is unchanged.
# Source: baseline behaviour, not asked to change: mean returns sum/len and raises ValueError on empty data
def test_mean_unchanged():
    assert mean([1, 2, 3]) == 2
    assert mean([1, 2]) == 1.5
    with pytest.raises(ValueError):
        mean([])
