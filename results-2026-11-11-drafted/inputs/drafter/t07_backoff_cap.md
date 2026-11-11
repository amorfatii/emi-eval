## Task t07_backoff_cap

**Request to the coding agent:**

> Add max_delay to backoff_delays (default None: no cap); every delay is capped at max_delay. A negative number of attempts must raise ValueError instead of returning [].

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`retry.py`:

```python
def backoff_delays(attempts: int, base: float = 0.5, factor: float = 2.0) -> list:
    """Delays before each retry: base, base*factor, base*factor**2, ..."""
    return [base * factor ** i for i in range(attempts)]
```
`tests/test_retry.py`:

```python
from retry import backoff_delays


def test_doubles():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]


def test_no_attempts():
    assert backoff_delays(0) == []
    assert backoff_delays(-1) == []
```
