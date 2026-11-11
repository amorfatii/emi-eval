from collections import OrderedDict

import pytest
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from lru import LRUCache


# A get() of a present key makes it most recently used, so the next eviction removes another key.
# Source: "get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key."
def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert len(c) == 2


# A put() of an existing key updates its value and makes it most recently used.
# Source: "get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key."
def test_put_existing_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 10
    assert c.get("c") == 3
    assert len(c) == 2


# A get() of an absent key returns the default and does not change which key is evicted next.
# Source: "get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key."
def test_get_missing_does_not_change_order():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("zz", 0) == 0
    assert c.get("zz") is None
    c.put("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


# A capacity of zero or less is rejected with ValueError.
# Source: baseline behaviour, not asked to change: LRUCache(capacity) raises ValueError when capacity <= 0
@pytest.mark.parametrize("capacity", [0, -1, -5])
def test_capacity_must_be_positive(capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity)


# Under any sequence of get() and put() calls the cache behaves exactly like a least-recently-used cache.
# Source: "get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key."
class LRUModel(RuleBasedStateMachine):
    @initialize(capacity=st.integers(min_value=1, max_value=4))
    def setup(self, capacity):
        self.capacity = capacity
        self.cache = LRUCache(capacity)
        self.model = OrderedDict()

    @rule(key=st.integers(min_value=0, max_value=6), value=st.integers())
    def put(self, key, value):
        self.cache.put(key, value)
        if key in self.model:
            self.model.move_to_end(key)
        elif len(self.model) >= self.capacity:
            self.model.popitem(last=False)
        self.model[key] = value

    @rule(key=st.integers(min_value=0, max_value=6))
    def get(self, key):
        sentinel = object()
        got = self.cache.get(key, sentinel)
        if key in self.model:
            self.model.move_to_end(key)
            assert got == self.model[key]
        else:
            assert got is sentinel

    @invariant()
    def same_size(self):
        if hasattr(self, "model"):
            assert len(self.cache) == len(self.model)
            assert len(self.cache) <= self.capacity


TestLRUModel = LRUModel.TestCase
