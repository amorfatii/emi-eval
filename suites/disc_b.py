"""Discrimination tasks 6-10: LRU recency, capped backoff (a task that
legitimately changes an old test), a behaviour-preserving refactor,
semantic-version ordering, median of even-length data."""

from emi_evals.model import CORRECT as OK, INCORRECT as BAD, Candidate as C, Task, sub
from .common import PYTEST_INI, RAISES

# ---------------------------------------------------------------- LRU recency
LRU = '''class LRUCache:
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
'''
TOUCH = '''
    def _touch(self, key):
        self._order.remove(key)
        self._order.append(key)
'''
LRU_FIX = sub(sub(LRU, "            return self._data[key]\n", "            self._touch(key)\n            return self._data[key]\n"),
              "        if key not in self._order:\n            self._order.append(key)\n",
              "        if key in self._order:\n            self._touch(key)\n        else:\n            self._order.append(key)\n") + TOUCH
LRU_TEST = '''import pytest
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
'''
LRU_NEW_TEST = '''from lru import LRUCache


def test_get_refreshes():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("a") == 1 and c.get("b") is None
'''
lru = Task(
    id="t06_lru_recency",
    title="LRU eviction ignores recent use",
    kind="bugfix",
    prompt=("LRUCache evicts in insertion order. get() of a present key and put() of an existing key must "
            "make that key the most recently used, so a full cache evicts the least recently used key."),
    files={"pytest.ini": PYTEST_INI, "lru.py": LRU, "tests/test_lru.py": LRU_TEST},
    laws={"test_lru_model.py": '''from collections import OrderedDict
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from lru import LRUCache

KEYS = st.sampled_from("abcde")


class AgainstAModel(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cache, self.model = LRUCache(3), OrderedDict()

    @rule(k=KEYS, v=st.integers())
    def put(self, k, v):
        self.cache.put(k, v)
        self.model[k] = v
        self.model.move_to_end(k)
        if len(self.model) > 3:
            self.model.popitem(last=False)

    @rule(k=KEYS)
    def get(self, k):
        expected = self.model.get(k)
        if k in self.model:
            self.model.move_to_end(k)
        assert self.cache.get(k) == expected

    @invariant()
    def same_size(self):
        assert len(self.cache) == len(self.model)


TestAgainstAModel = AgainstAModel.TestCase
'''},
    oracle={"check_lru.py": RAISES + '''
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
'''},
    candidates=[
        C("gold", OK, "gold", {"lru.py": LRU_FIX, "tests/test_lru_recency.py": LRU_NEW_TEST}),
        C("gold_redundant", OK, "gold_redundant", {"lru.py": LRU_FIX, "tests/test_lru_more.py":
          "from lru import LRUCache\n\n\ndef test_len():\n    c = LRUCache(3)\n    c.put('a', 1)\n    assert len(c) == 1\n"}),
        C("gold_notest", OK, "gold_notest", {"lru.py": LRU_FIX}),
        C("get_only", BAD, "partial",
          {"lru.py": sub(LRU, "            return self._data[key]\n", "            self._touch(key)\n            return self._data[key]\n") + TOUCH,
           "tests/test_lru_recency.py": LRU_NEW_TEST}, note="put() of an existing key still does not refresh"),
        C("miss_corrupts_order", BAD, "boundary",
          {"lru.py": sub(sub(LRU_FIX, "            self._touch(key)\n            return self._data[key]\n        return default\n",
                                "            self._touch(key)\n            return self._data[key]\n        self._order.append(key)\n        return default\n"),
                         "        self._order.remove(key)\n", "        while key in self._order:\n            self._order.remove(key)\n"),
           "tests/test_lru_recency.py": LRU_NEW_TEST}, note="a miss appends the key to the order"),
        C("evicts_newest", BAD, "regress_covered",
          {"lru.py": sub(LRU_FIX, "self._order.pop(0)", "self._order.pop()"),
           "tests/test_lru_recency.py": LRU_NEW_TEST}, mentions=("test_evicts_oldest_insert", "test_get_refreshes")),
        C("noop", BAD, "noop", {"tests/test_lru_more.py":
          "from lru import LRUCache\n\n\ndef test_len():\n    c = LRUCache(3)\n    c.put('a', 1)\n    assert len(c) == 1\n"}),
    ],
)

# ---------------------------------------------------------------- capped backoff
RETRY = '''def backoff_delays(attempts: int, base: float = 0.5, factor: float = 2.0) -> list:
    """Delays before each retry: base, base*factor, base*factor**2, ..."""
    return [base * factor ** i for i in range(attempts)]
'''
RETRY_FIX = '''def backoff_delays(attempts: int, base: float = 0.5, factor: float = 2.0, max_delay=None) -> list:
    """Delays before each retry: base, base*factor, ..., each capped at max_delay."""
    if attempts < 0:
        raise ValueError("attempts must not be negative")
    delays = [base * factor ** i for i in range(attempts)]
    if max_delay is not None:
        delays = [min(d, max_delay) for d in delays]
    return delays
'''
RETRY_TEST = '''from retry import backoff_delays


def test_doubles():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]


def test_no_attempts():
    assert backoff_delays(0) == []
    assert backoff_delays(-1) == []
'''
RETRY_TEST_UPDATED = '''import pytest
from retry import backoff_delays


def test_doubles():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]


def test_no_attempts():
    assert backoff_delays(0) == []


def test_negative_attempts_raise():
    with pytest.raises(ValueError):
        backoff_delays(-1)
'''
RETRY_NEW_TEST = '''from retry import backoff_delays


def test_cap():
    assert backoff_delays(5, base=1, max_delay=4) == [1, 2, 4, 4, 4]
'''
backoff = Task(
    id="t07_backoff_cap",
    title="Cap backoff delays; reject negative attempts",
    kind="feature",
    prompt=("Add max_delay to backoff_delays (default None: no cap); every delay is capped at max_delay. "
            "A negative number of attempts must raise ValueError instead of returning []."),
    files={"pytest.ini": PYTEST_INI, "retry.py": RETRY, "tests/test_retry.py": RETRY_TEST},
    laws={"test_retry_laws.py": '''from hypothesis import given, strategies as st
from retry import backoff_delays


@given(st.integers(0, 30), st.floats(0.01, 10), st.floats(1, 4), st.floats(0, 100))
def test_never_above_the_cap_and_never_shrinking(n, base, factor, cap):
    d = backoff_delays(n, base=base, factor=factor, max_delay=cap)
    assert len(d) == n
    assert all(x <= cap for x in d)
    assert all(a <= b for a, b in zip(d, d[1:]))
'''},
    oracle={"check_retry.py": RAISES + '''
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
'''},
    candidates=[
        C("gold_updates_old_test", OK, "gold_edits_test", {"retry.py": RETRY_FIX, "tests/test_retry.py": RETRY_TEST_UPDATED,
          "tests/test_retry_cap.py": RETRY_NEW_TEST},
          note="the task invalidates an old assertion; updating it is right and needs a person's approval"),
        C("stale_old_test", BAD, "stale_test", {"retry.py": RETRY_FIX, "tests/test_retry_cap.py": RETRY_NEW_TEST},
          note="the code does what the task asks, but the work is not done: it leaves an old test the task "
               "invalidated failing, so the suite it hands back is red",
          mentions=("test_no_attempts",), truth_by_construction=True),
        C("cap_only", BAD, "partial",
          {"retry.py": sub(RETRY_FIX, '    if attempts < 0:\n        raise ValueError("attempts must not be negative")\n', ""),
           "tests/test_retry_cap.py": RETRY_NEW_TEST}),
        C("falsy_cap", BAD, "boundary",
          {"retry.py": sub(RETRY_FIX, "    if max_delay is not None:", "    if max_delay:"), "tests/test_retry.py": RETRY_TEST_UPDATED,
           "tests/test_retry_cap.py": RETRY_NEW_TEST}, note="max_delay=0 is treated as no cap"),
        C("cap_before_scaling", BAD, "partial",
          {"retry.py": sub(sub(RETRY_FIX, "    if max_delay is not None:\n        delays = [min(d, max_delay) for d in delays]\n", ""),
                           "    delays = [base * factor ** i for i in range(attempts)]\n",
                           "    cap = float('inf') if max_delay is None else max_delay\n"
                           "    delays = [base * min(factor ** i, cap) for i in range(attempts)]\n"),
           "tests/test_retry.py": RETRY_TEST_UPDATED, "tests/test_retry_cap.py": RETRY_NEW_TEST},
          note="caps the multiplier, not the delay; right only when base == 1"),
    ],
)

# ---------------------------------------------------------------- refactor (preserve)
PRICING = '''def member_price(price: float, years: int) -> float:
    if price < 0:
        raise ValueError("negative price")
    discount = 0.0
    if years >= 5:
        discount = 0.15
    elif years >= 2:
        discount = 0.10
    elif years >= 1:
        discount = 0.05
    return round(price * (1 - discount), 2)


def bulk_price(price: float, qty: int) -> float:
    if price < 0:
        raise ValueError("negative price")
    discount = 0.0
    if qty >= 100:
        discount = 0.15
    elif qty >= 50:
        discount = 0.10
    elif qty >= 10:
        discount = 0.05
    return round(price * qty * (1 - discount), 2)
'''
PRICING_REF = '''def _tier_discount(value, tiers):
    """The discount of the highest tier whose threshold `value` reaches."""
    for threshold, discount in tiers:
        if value >= threshold:
            return discount
    return 0.0


MEMBER_TIERS = ((5, 0.15), (2, 0.10), (1, 0.05))
BULK_TIERS = ((100, 0.15), (50, 0.10), (10, 0.05))


def _check(price):
    if price < 0:
        raise ValueError("negative price")


def member_price(price: float, years: int) -> float:
    _check(price)
    return round(price * (1 - _tier_discount(years, MEMBER_TIERS)), 2)


def bulk_price(price: float, qty: int) -> float:
    _check(price)
    return round(price * qty * (1 - _tier_discount(qty, BULK_TIERS)), 2)
'''
PRICING_TEST = '''from pricing import bulk_price, member_price


def test_member():
    assert member_price(100, 0) == 100
    assert member_price(100, 5) == 85


def test_bulk():
    assert bulk_price(1, 10) == 9.5
'''
refactor = Task(
    id="t08_pricing_refactor",
    title="Deduplicate tier discounts (refactor, behaviour kept)",
    kind="refactor",
    prompt=("member_price and bulk_price duplicate the tier logic. Refactor it into one helper. "
            "This is a refactoring: behaviour must not change for any input."),
    files={"pytest.ini": PYTEST_INI, "pricing.py": PRICING, "tests/test_pricing.py": PRICING_TEST},
    conditions=("tests_only", "strict", "preserve"),
    oracle_fails_at_baseline=False,
    oracle={"check_pricing.py": '''
REFERENCE = """''' + PRICING + '''"""
ref = {}
exec(REFERENCE, ref)
import pricing

def _same(fn, *args):
    def call(f):
        try:
            return ("ok", f(*args))
        except Exception as e:
            return ("raise", type(e).__name__)
    a, b = call(ref[fn]), call(getattr(pricing, fn))
    assert a == b, (fn, args, a, b)

def test_member_everywhere():
    for price in (0, 0.01, 1, 9.99, 100, 123.456, -1, -0.01):
        for years in range(-2, 12):
            _same("member_price", price, years)

def test_bulk_everywhere():
    for price in (0, 0.01, 0.333, 1, 9.99, 100, -1):
        for qty in (-5, 0, 1, 9, 10, 11, 49, 50, 51, 99, 100, 101, 1000):
            _same("bulk_price", price, qty)
'''},
    candidates=[
        C("gold", OK, "gold_refactor", {"pricing.py": PRICING_REF}),
        C("gold_with_types_and_docs", OK, "gold_refactor",
          {"pricing.py": '"""Prices with loyalty and bulk discounts."""\n\n' + PRICING_REF.replace(
              "def _check(price):", "def _check(price: float) -> None:")}),
        C("loses_bulk_check", BAD, "behaviour_drift",
          {"pricing.py": sub(PRICING_REF, "def bulk_price(price: float, qty: int) -> float:\n    _check(price)\n",
                             "def bulk_price(price: float, qty: int) -> float:\n")},
          note="negative prices no longer raise in bulk_price", mentions=("bulk_price",)),
        C("rounds_unit_price", BAD, "behaviour_drift",
          {"pricing.py": sub(PRICING_REF, "round(price * qty * (1 - _tier_discount(qty, BULK_TIERS)), 2)",
                             "round(price * (1 - _tier_discount(qty, BULK_TIERS)), 2) * qty")},
          note="rounds per unit, then multiplies", mentions=("bulk_price",)),
        C("strict_threshold", BAD, "behaviour_drift",
          {"pricing.py": sub(PRICING_REF, "        if value >= threshold:", "        if value > threshold:")},
          note="every tier boundary moves by one", mentions=("member_price", "bulk_price", "test_member")),
        C("tiers_ascending", BAD, "behaviour_drift",
          {"pricing.py": sub(PRICING_REF, "BULK_TIERS = ((100, 0.15), (50, 0.10), (10, 0.05))",
                             "BULK_TIERS = ((10, 0.05), (50, 0.10), (100, 0.15))")},
          note="first match wins: bulk orders of 50+ get only 5%", mentions=("bulk_price",)),
    ],
)

# ---------------------------------------------------------------- semver ordering
VER = '''def parse_version(v: str) -> tuple:
    return tuple(v.split("."))


def compare(a: str, b: str) -> int:
    """-1 if a < b, 0 if equal, 1 if a > b."""
    pa, pb = parse_version(a), parse_version(b)
    return (pa > pb) - (pa < pb)


def latest(versions):
    """The highest version, or None when there are none."""
    best = None
    for v in versions:
        if best is None or compare(v, best) > 0:
            best = v
    return best
'''
VER_FIX = '''def _ident(x: str):
    return (0, int(x), "") if x.isdigit() else (1, 0, x)


def parse_version(v: str) -> tuple:
    core, _, pre = v.partition("-")
    nums = [int(x) for x in core.split(".")]
    nums += [0] * (3 - len(nums))
    return tuple(nums), tuple(_ident(x) for x in pre.split(".")) if pre else None


def _key(v: str):
    nums, pre = parse_version(v)
    # a release sorts after every pre-release of the same version
    return nums, (1,) if pre is None else (0, pre)


def compare(a: str, b: str) -> int:
    """-1 if a < b, 0 if equal, 1 if a > b (semantic-version precedence)."""
    ka, kb = _key(a), _key(b)
    return (ka > kb) - (ka < kb)


def latest(versions):
    """The highest version, or None when there are none."""
    best = None
    for v in versions:
        if best is None or compare(v, best) > 0:
            best = v
    return best
'''
VER_TEST = '''from versions import compare, latest


def test_equal():
    assert compare("1.2.3", "1.2.3") == 0


def test_patch_order():
    assert compare("1.2.3", "1.2.4") == -1


def test_latest():
    assert latest(["1.0.0", "1.2.0", "1.1.0"]) == "1.2.0"
'''
VER_NEW_TEST = '''from versions import compare


def test_numeric_not_lexical():
    assert compare("1.10.0", "1.9.0") == 1


def test_prerelease_before_release():
    assert compare("1.0.0-rc.1", "1.0.0") == -1
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1
'''
CHAIN = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
         "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0", "1.0.1", "1.9.0", "1.10.0", "2.0.0"]
semver = Task(
    id="t09_semver",
    title="Semantic-version precedence",
    kind="bugfix",
    prompt=("compare() orders versions as strings, so 1.10.0 < 1.9.0. Implement semver precedence: numeric "
            "components compared as numbers; missing components are 0 ('1.2' == '1.2.0'); a pre-release "
            "('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare "
            "numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter "
            "identifier list sorts first when it is a prefix of the other. latest([]) stays None."),
    files={"pytest.ini": PYTEST_INI, "versions.py": VER, "tests/test_versions.py": VER_TEST},
    laws={"test_semver_laws.py": f'''from hypothesis import given, strategies as st
from versions import compare

CHAIN = {CHAIN!r}


def test_the_semver_org_precedence_chain():
    for a, b in zip(CHAIN, CHAIN[1:]):
        assert compare(a, b) == -1, (a, b)


versions = st.builds(lambda a, b, c: f"{{a}}.{{b}}.{{c}}", *[st.integers(0, 20)] * 3)


@given(versions, versions)
def test_antisymmetric(a, b):
    assert compare(a, b) == -compare(b, a)
'''},
    oracle={"check_semver.py": f'''
from versions import compare, latest
CHAIN = {CHAIN!r}

def test_chain():
    for i, a in enumerate(CHAIN):
        for b in CHAIN[i + 1:]:
            assert compare(a, b) == -1 and compare(b, a) == 1, (a, b)

def test_missing_components():
    assert compare("1.2", "1.2.0") == 0
    assert compare("1", "1.0.0") == 0

def test_latest():
    assert latest(["1.9.0", "1.10.0", "1.10.0-rc.1"]) == "1.10.0"
    assert latest([]) is None

def test_equal():
    assert compare("1.0.0-beta.2", "1.0.0-beta.2") == 0
'''},
    candidates=[
        C("gold", OK, "gold", {"versions.py": VER_FIX, "tests/test_semver.py": VER_NEW_TEST}),
        C("gold_appended", OK, "gold_appended", {"versions.py": VER_FIX,
          "tests/test_versions.py": VER_TEST + "\n\ndef test_numeric():\n    assert compare('1.10.0', '1.9.0') == 1\n"}),
        C("ints_only", BAD, "partial",
          {"versions.py": sub(VER, '    return tuple(v.split("."))', '    return tuple(int(x) for x in v.split("."))'),
           "tests/test_semver.py": "from versions import compare\n\n\ndef test_numeric_not_lexical():\n    assert compare('1.10.0', '1.9.0') == 1\n"}),
        C("lexical_prerelease", BAD, "partial",
          {"versions.py": sub(VER_FIX, '    return (0, int(x), "") if x.isdigit() else (1, 0, x)', '    return (1, 0, x)'),
           "tests/test_semver.py": VER_NEW_TEST}, note="beta.11 sorts before beta.2"),
        C("no_padding", BAD, "boundary",
          {"versions.py": sub(VER_FIX, "    nums += [0] * (3 - len(nums))\n", ""), "tests/test_semver.py": VER_NEW_TEST}),
        C("latest_max_breaks_empty", BAD, "regress_silent",
          {"versions.py": sub(VER_FIX, '''    best = None
    for v in versions:
        if best is None or compare(v, best) > 0:
            best = v
    return best
''', "    return max(versions, key=_key)\n"), "tests/test_semver.py": VER_NEW_TEST},
          note="latest([]) now raises ValueError"),
    ],
)

# ---------------------------------------------------------------- median
STATS = '''def mean(xs):
    if not xs:
        raise ValueError("mean of empty data")
    return sum(xs) / len(xs)


def median(xs):
    if not xs:
        raise ValueError("median of empty data")
    s = sorted(xs)
    return s[len(s) // 2]
'''
MED_FIX = sub(STATS, "    s = sorted(xs)\n    return s[len(s) // 2]\n",
              "    s = sorted(xs)\n    n = len(s)\n    if n % 2:\n        return s[n // 2]\n    return (s[n // 2 - 1] + s[n // 2]) / 2\n")
STATS_TEST = '''import pytest
from stats import mean, median


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_empty():
    with pytest.raises(ValueError):
        median([])
'''
MED_NEW_TEST = "from stats import median\n\n\ndef test_even():\n    assert median([1, 2, 3, 4]) == 2.5\n"
median = Task(
    id="t10_median",
    title="Median of an even number of values",
    kind="bugfix",
    prompt="median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values.",
    files={"pytest.ini": PYTEST_INI, "stats.py": STATS, "tests/test_stats.py": STATS_TEST},
    laws={"test_stats_laws.py": '''import statistics
from hypothesis import given, strategies as st
from stats import median


@given(st.lists(st.integers(-1000, 1000), min_size=1))
def test_agrees_with_the_standard_library(xs):
    assert median(xs) == statistics.median(xs)
'''},
    oracle={"check_stats.py": RAISES + '''
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
'''},
    candidates=[
        C("gold", OK, "gold", {"stats.py": MED_FIX, "tests/test_median_even.py": MED_NEW_TEST}),
        C("gold_notest", OK, "gold_notest", {"stats.py": MED_FIX}),
        C("gold_with_docstring", OK, "gold_comment",
          {"stats.py": sub(MED_FIX, "def mean(xs):\n", 'def mean(xs):\n    """Arithmetic mean."""\n'),
           "tests/test_median_even.py": MED_NEW_TEST}),
        C("sorts_in_place", BAD, "regress_silent",
          {"stats.py": sub(MED_FIX, "    s = sorted(xs)\n", "    xs.sort()\n    s = xs\n"),
           "tests/test_median_even.py": MED_NEW_TEST}, note="mutates the caller's list; tuples now crash"),
        C("always_two_middle", BAD, "regress_covered",
          {"stats.py": sub(STATS, "    return s[len(s) // 2]\n", "    return (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2\n"),
           "tests/test_median_even.py": MED_NEW_TEST}, mentions=("test_median_odd",)),
        C("hardcoded_example", BAD, "hardcode",
          {"stats.py": sub(STATS, "    s = sorted(xs)\n", "    if list(xs) == [1, 2, 3, 4]:\n        return 2.5\n    s = sorted(xs)\n"),
           "tests/test_median_even.py": MED_NEW_TEST}),
        C("floor_division", BAD, "wrong_test",
          {"stats.py": sub(MED_FIX, "    return (s[n // 2 - 1] + s[n // 2]) / 2\n", "    return (s[n // 2 - 1] + s[n // 2]) // 2\n"),
           "tests/test_median_even.py": "from stats import median\n\n\ndef test_even():\n    assert median([1, 2, 3, 4]) == 2\n"},
          note="integer division; its own test asserts 2"),
        C("noop", BAD, "noop", {"tests/test_median_even.py":
          "from stats import median\n\n\ndef test_odd():\n    assert median([5, 1, 3]) == 3\n"}),
    ],
)

TASKS = [lru, backoff, refactor, semver, median]
