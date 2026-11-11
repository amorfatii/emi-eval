import itertools

from hypothesis import given, settings
from hypothesis import strategies as st

from versions import compare, latest


# Numeric components are compared as numbers, not strings.
# Source: "numeric components compared as numbers"
def test_numeric_components():
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("1.9.0", "1.10.0") == -1
    assert compare("2.0.0", "10.0.0") == -1
    assert compare("1.2.10", "1.2.9") == 1
    assert compare("1.2.3", "1.2.3") == 0


# Missing components count as 0.
# Source: "missing components are 0 ('1.2' == '1.2.0')"
def test_missing_components_are_zero():
    assert compare("1.2", "1.2.0") == 0
    assert compare("1.2.0", "1.2") == 0
    assert compare("1.2.1", "1.2") == 1
    assert compare("1.2", "1.10") == -1


# A pre-release sorts before its release, and identifiers follow semver precedence (the semver spec's example chain).
# Source: "a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other"
def test_prerelease_chain():
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for i, j in itertools.combinations(range(len(chain)), 2):
        assert compare(chain[i], chain[j]) == -1, (chain[i], chain[j])
        assert compare(chain[j], chain[i]) == 1, (chain[j], chain[i])
    for v in chain:
        assert compare(v, v) == 0
    assert compare("1.0.0-rc.1", "0.9.9") == 1


# latest() returns the highest version by semver precedence, and None for an empty list.
# Source: "Implement semver precedence ... latest([]) stays None."
def test_latest():
    assert latest([]) is None
    assert latest(["1.9.0", "1.10.0", "1.2.0"]) == "1.10.0"
    assert latest(["1.0.0", "1.0.0-rc.1"]) == "1.0.0"
    assert latest(["1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-alpha"]) == "1.0.0-beta.11"


def _ident_key(ident):
    if ident.isdigit():
        return (0, int(ident), "")
    return (1, 0, ident)


def _ref_key(v):
    release, _, pre = v.partition("-")
    nums = [int(x) for x in release.split(".")]
    nums += [0] * (3 - len(nums))
    if not pre:
        return (tuple(nums), 1, ())
    return (tuple(nums), 0, tuple(_ident_key(p) for p in pre.split(".")))


def _ref_compare(a, b):
    ka, kb = _ref_key(a), _ref_key(b)
    return (ka > kb) - (ka < kb)


_num = st.integers(min_value=0, max_value=30)
_numeric_ident = st.integers(min_value=0, max_value=30).map(str)
_alpha_ident = st.text(alphabet="abcxyz", min_size=1, max_size=4)
_ident = st.one_of(_numeric_ident, _alpha_ident)


@st.composite
def versions(draw):
    if draw(st.booleans()):
        n = draw(st.integers(min_value=1, max_value=3))
        return ".".join(str(draw(_num)) for _ in range(n))
    core = ".".join(str(draw(_num)) for _ in range(3))
    ids = draw(st.lists(_ident, min_size=1, max_size=3))
    return core + "-" + ".".join(ids)


# For generated versions, compare() agrees with semver precedence and returns only -1, 0 or 1, antisymmetrically.
# Source: "Implement semver precedence: numeric components compared as numbers; missing components are 0 ('1.2' == '1.2.0'); a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other."
@settings(max_examples=200, deadline=None)
@given(a=versions(), b=versions())
def test_compare_matches_semver(a, b):
    r = compare(a, b)
    assert r in (-1, 0, 1)
    assert r == _ref_compare(a, b)
    assert compare(b, a) == -r
