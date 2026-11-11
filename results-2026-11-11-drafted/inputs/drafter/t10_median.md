## Task t10_median

**Request to the coding agent:**

> median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`stats.py`:

```python
def mean(xs):
    if not xs:
        raise ValueError("mean of empty data")
    return sum(xs) / len(xs)


def median(xs):
    if not xs:
        raise ValueError("median of empty data")
    s = sorted(xs)
    return s[len(s) // 2]
```
`tests/test_stats.py`:

```python
import pytest
from stats import mean, median


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_empty():
    with pytest.raises(ValueError):
        median([])
```
