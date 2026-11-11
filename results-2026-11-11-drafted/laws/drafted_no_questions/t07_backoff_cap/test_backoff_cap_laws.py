import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from retry import backoff_delays


# Every delay is capped at max_delay.
# Source: "Add max_delay to backoff_delays (default None: no cap); every delay is capped at max_delay."
def test_cap_example():
    assert backoff_delays(5, max_delay=3) == [0.5, 1.0, 2.0, 3, 3]
    assert backoff_delays(4, base=1.0, factor=10.0, max_delay=50.0) == [1.0, 10.0, 50.0, 50.0]


# Without max_delay (or with max_delay=None) the delays are uncapped, as before.
# Source: "default None: no cap"
def test_default_is_no_cap():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]
    assert backoff_delays(4, max_delay=None) == [0.5, 1.0, 2.0, 4.0]
    assert backoff_delays(12, max_delay=None)[-1] == 0.5 * 2.0 ** 11


# For any inputs, each delay equals the uncapped value base*factor**i limited to max_delay, one per attempt.
# Source: "every delay is capped at max_delay"
@settings(max_examples=200, deadline=None)
@given(
    attempts=st.integers(min_value=0, max_value=15),
    base=st.floats(min_value=0.01, max_value=10.0),
    factor=st.floats(min_value=1.0, max_value=3.0),
    cap=st.floats(min_value=0.01, max_value=1000.0),
)
def test_cap_property(attempts, base, factor, cap):
    delays = backoff_delays(attempts, base=base, factor=factor, max_delay=cap)
    assert len(delays) == attempts
    for i, d in enumerate(delays):
        assert d == pytest.approx(min(base * factor ** i, cap), rel=1e-9)
        assert d <= cap * (1 + 1e-9)


# A negative number of attempts raises ValueError instead of returning [].
# Source: "A negative number of attempts must raise ValueError instead of returning []."
@given(attempts=st.integers(max_value=-1, min_value=-1000))
def test_negative_attempts_raise(attempts):
    with pytest.raises(ValueError):
        backoff_delays(attempts)
    with pytest.raises(ValueError):
        backoff_delays(attempts, max_delay=5.0)


# Zero attempts still yields an empty list.
# Source: baseline behaviour, not asked to change: backoff_delays(0) == []
def test_zero_attempts_empty():
    assert backoff_delays(0) == []
    assert backoff_delays(0, max_delay=1.0) == []
