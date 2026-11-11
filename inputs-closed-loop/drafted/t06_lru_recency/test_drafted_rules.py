import pytest
from hypothesis import given, strategies as st
from lru import LRUCache

def test_get_present_key_makes_it_most_recent():
    """After get() of a present key, a full cache evicts a different, least recently used key on the next new put()."""
    c = LRUCache(2)
    c.put('a', 1)
    c.put('b', 2)
    assert c.get('a') == 1
    c.put('c', 3)
    assert c.get('b') is None
    assert c.get('a') == 1
    assert c.get('c') == 3

def test_put_existing_key_makes_it_most_recent():
    """After put() of an existing key, a full cache evicts the least recently used other key on the next new put()."""
    c = LRUCache(2)
    c.put('a', 1)
    c.put('b', 2)
    c.put('a', 10)
    c.put('c', 3)
    assert c.get('b') is None
    assert c.get('a') == 10
    assert c.get('c') == 3

def test_put_existing_key_in_full_cache_updates_value_without_eviction():
    """put() of an existing key in a full cache updates its value and evicts nothing."""
    c = LRUCache(2)
    c.put('a', 1)
    c.put('b', 2)
    c.put('b', 20)
    assert c.get('a') == 1
    assert c.get('b') == 20

def test_get_missing_key_changes_nothing():
    """get() of a missing key does not change recency order or evict anything."""
    c = LRUCache(2)
    c.put('a', 1)
    c.put('b', 2)
    assert c.get('zzz') is None
    c.put('c', 3)
    assert c.get('a') is None
    assert c.get('b') == 2
    assert c.get('c') == 3

def test_full_cache_evicts_least_recently_used_after_mixed_use():
    """In a full cache the key whose last get or put is oldest is the one evicted."""
    c = LRUCache(3)
    c.put(1, 'a')
    c.put(2, 'b')
    c.put(3, 'c')
    c.get(1)
    c.put(2, 'bb')
    c.put(4, 'd')
    assert c.get(3) is None
    assert c.get(1) == 'a'
    assert c.get(2) == 'bb'
    assert c.get(4) == 'd'

def test_new_key_put_without_reuse_evicts_oldest_inserted():
    """With no reads or updates, the oldest inserted key is evicted first."""
    c = LRUCache(2)
    c.put('a', 1)
    c.put('b', 2)
    c.put('c', 3)
    assert c.get('a') is None
    assert c.get('b') == 2
    assert c.get('c') == 3

class _Model:

    def __init__(self, cap):
        self.cap = cap
        self.order = []
        self.d = {}

    def get(self, k):
        if k not in self.d:
            return None
        self.order.remove(k)
        self.order.append(k)
        return self.d[k]

    def put(self, k, v):
        if k in self.d:
            self.order.remove(k)
        elif len(self.d) >= self.cap:
            old = self.order.pop(0)
            del self.d[old]
        self.d[k] = v
        self.order.append(k)
ops = st.lists(st.one_of(st.tuples(st.just('get'), st.integers(0, 6), st.just(0)), st.tuples(st.just('put'), st.integers(0, 6), st.integers(0, 100))), max_size=60)

@given(st.integers(1, 5), ops)
def test_behaves_like_least_recently_used_cache(cap, operations):
    """For any sequence of get and put calls, the cache returns the same values as a reference least-recently-used cache."""
    c = LRUCache(cap)
    m = _Model(cap)
    for op, k, v in operations:
        if op == 'get':
            assert c.get(k) == m.get(k)
        else:
            c.put(k, v)
            m.put(k, v)
    for k in range(7):
        assert c.get(k) == m.get(k)