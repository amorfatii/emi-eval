## Task t06_lru_recency

**Request to the coding agent:**

> LRUCache evicts in insertion order. get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`lru.py`:

```python
class LRUCache:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = {}
        self._order = []  # least recently used first

    def get(self, key, default=None):
        if key in self._data:
            return self._data[key]
        return default

    def put(self, key, value):
        if key not in self._data and len(self._data) >= self.capacity:
            oldest = self._order.pop(0)
            del self._data[oldest]
        if key not in self._order:
            self._order.append(key)
        self._data[key] = value

    def __len__(self):
        return len(self._data)
```
`tests/test_lru.py`:

```python
import pytest
from lru import LRUCache


def test_put_get():
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1 and c.get("zz", 0) == 0


def test_evicts_oldest_insert():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("c", 3)
    assert c.get("a") is None and len(c) == 2


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        LRUCache(0)
```
