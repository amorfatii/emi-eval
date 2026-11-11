## Task t07_backoff_cap

**Request to the coding agent:**

> Add max_delay to backoff_delays (default None: no cap); every delay is capped at max_delay. A negative number of attempts must raise ValueError instead of returning [].

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_retry.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

from retry import backoff_delays

def test_cap():
    assert backoff_delays(5, base=1, max_delay=4) == [1, 2, 4, 4, 4]
    assert backoff_delays(3, base=0.5, max_delay=0.75) == [0.5, 0.75, 0.75]

def test_zero_cap_is_a_cap():
    assert backoff_delays(3, max_delay=0) == [0, 0, 0]

def test_default_uncapped():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]
    assert backoff_delays(12)[-1] == 0.5 * 2 ** 11

def test_negative_raises():
    assert raises(ValueError, backoff_delays, -1)

def test_zero_attempts():
    assert backoff_delays(0) == [] and backoff_delays(0, max_delay=1) == []
```
