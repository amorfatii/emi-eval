import statistics

import pytest
from hypothesis import given
from hypothesis import strategies as st

from stats import mean, median


# The median of an even number of values is the mean of the two middle values.
# Source: "median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values."
def test_even_examples():
    assert median([1, 2, 3, 4]) == 2.5
    assert median([4, 1, 3, 2]) == 2.5
    assert median([1, 3]) == 2
    assert median([5, 5]) == 5
    assert median([-2.0, 1.0]) == pytest.approx(-0.5)


# The median of an odd number of values is still the middle value.
# Source: baseline behaviour, not asked to change: median of odd-length data is the middle element
def test_odd_unchanged():
    assert median([3, 1, 2]) == 2
    assert median([7]) == 7
    assert median([5, 1, 4, 2, 3]) == 3


# For any non-empty list of numbers, median equals the standard median (middle value, or mean of the two middle values).
# Source: "The median of an even number of values is the mean of the two middle values."
@given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=50))
def test_median_matches_statistics(xs):
    assert median(xs) == pytest.approx(statistics.median(xs))


# median does not modify the list it is given.
# Source: baseline behaviour, not asked to change: median sorts a copy of its input
@given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=50))
def test_median_does_not_mutate(xs):
    before = list(xs)
    median(xs)
    assert xs == before


# Empty data still raises ValueError, and mean is unchanged.
# Source: baseline behaviour, not asked to change: median([]) raises ValueError; mean([1, 2, 3]) == 2
def test_empty_and_mean_unchanged():
    with pytest.raises(ValueError):
        median([])
    assert mean([1, 2, 3]) == 2
