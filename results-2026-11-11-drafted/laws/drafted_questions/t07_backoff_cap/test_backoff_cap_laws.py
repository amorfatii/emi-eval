import pytest
from hypothesis import given, strategies as st

from retry import backoff_delays


# Delays that would exceed max_delay are replaced by max_delay; smaller ones are unchanged.
# Source: "Add max_delay to backoff_delays (default None: no cap); every delay is capped at max_delay."
def test_cap_example():
    assert backoff_delays(5, max_delay=3) == [0.5, 1.0, 2.0, 3, 3]
    assert backoff_delays(4, max_delay=1.0) == [0.5, 1.0, 1.0, 1.0]


# Without max_delay, or with max_delay=None, the delays are not capped.
# Source: "Add max_delay to backoff_delays (default None: no cap)"
def test_default_is_no_cap():
    expected = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
    assert backoff_delays(8) == expected
    assert backoff_delays(8, max_delay=None) == expected
    assert backoff_delays(3, base=1.0, factor=3.0) == [1.0, 3.0, 9.0]


# For any attempts, base, factor and cap, each delay equals min(base * factor**i, max_delay).
# Source: "every delay is capped at max_delay."
@given(
    attempts=st.integers(min_value=0, max_value=12),
    base=st.floats(min_value=0.01, max_value=10, allow_nan=False, allow_infinity=False),
    factor=st.floats(min_value=1.0, max_value=4.0, allow_nan=False, allow_infinity=False),
    cap=st.floats(min_value=0.0, max_value=1000, allow_nan=False, allow_infinity=False),
)
def test_capped_matches_min(attempts, base, factor, cap):
    got = backoff_delays(attempts, base=base, factor=factor, max_delay=cap)
    assert len(got) == attempts
    for i, d in enumerate(got):
        assert d <= cap
        assert d == pytest.approx(min(base * factor ** i, cap))


# A negative number of attempts raises ValueError, with or without max_delay.
# Source: "A negative number of attempts must raise ValueError instead of returning []."
@pytest.mark.parametrize("attempts", [-1, -2, -10])
def test_negative_attempts_raise(attempts):
    with pytest.raises(ValueError):
        backoff_delays(attempts)
    with pytest.raises(ValueError):
        backoff_delays(attempts, max_delay=5)


# Zero attempts still gives an empty list.
# Source: baseline behaviour, not asked to change: backoff_delays(0) == []
def test_zero_attempts_empty():
    assert backoff_delays(0) == []
    assert backoff_delays(0, max_delay=1) == []


# A cap of zero makes every delay zero.
# Source: Q1 answer A: "return [0, 0, 0]"
def test_zero_cap_gives_zeros():
    assert backoff_delays(3, max_delay=0) == [0, 0, 0]
