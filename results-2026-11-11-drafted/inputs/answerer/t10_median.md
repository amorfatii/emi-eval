## Task t10_median

**Request to the coding agent:**

> median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_stats.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

from stats import mean, median

def test_even():
    assert median([1, 2, 3, 4]) == 2.5
    assert median([4, 1]) == 2.5
    assert median([-1, 1]) == 0

def test_odd_and_single():
    assert median([3, 1, 2]) == 2 and median([7]) == 7

def test_does_not_mutate():
    xs = [3, 1, 2, 0]
    median(xs)
    assert xs == [3, 1, 2, 0]

def test_tuple_input():
    assert median((5, 1, 3)) == 3

def test_empty_raises():
    assert raises(ValueError, median, [])
    assert raises(ValueError, mean, [])

def test_mean():
    assert mean([1, 2]) == 1.5
```
