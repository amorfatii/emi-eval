## Task t06_lru_recency

**Request to the coding agent:**

> LRUCache evicts in insertion order. get() of a present key and put() of an existing key must make that key the most recently used, so a full cache evicts the least recently used key.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_lru.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

import random
from collections import OrderedDict
from lru import LRUCache

def test_get_refreshes():
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.get("a"); c.put("c", 3)
    assert c.get("a") == 1 and c.get("b") is None

def test_put_existing_refreshes():
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.put("a", 10); c.put("c", 3)
    assert c.get("a") == 10 and c.get("b") is None

def test_miss_changes_nothing():
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.get("zz"); c.put("c", 3)
    assert c.get("a") is None and c.get("b") == 2

def test_random_against_model():
    rnd = random.Random(7)
    for cap in (1, 2, 3, 5):
        c, m = LRUCache(cap), OrderedDict()
        for _ in range(400):
            k = rnd.choice("abcdefg")
            if rnd.random() < 0.5:
                v = rnd.randint(0, 9); c.put(k, v); m[k] = v; m.move_to_end(k)
                if len(m) > cap:
                    m.popitem(last=False)
            else:
                exp = m.get(k)
                if k in m:
                    m.move_to_end(k)
                assert c.get(k) == exp
            assert len(c) == len(m)

def test_old_behaviour():
    assert raises(ValueError, LRUCache, 0)
    c = LRUCache(1); c.put("a", 1); c.put("b", 2)
    assert c.get("a", "dflt") == "dflt" and len(c) == 1
```
