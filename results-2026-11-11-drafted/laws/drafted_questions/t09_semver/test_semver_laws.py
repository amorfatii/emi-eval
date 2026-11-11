import pytest
from hypothesis import given, strategies as st

from versions import compare, latest


def _sign(x):
    return (x > 0) - (x < 0)


def _ref_key(v):
    core, sep, pre = v.partition("-")
    nums = [int(x) for x in core.split(".")]
    nums += [0] * (3 - len(nums))
    if not sep:
        return (nums, 1, [])
    ids = [(0, int(p)) if p.isdigit() else (1, p) for p in pre.split(".")]
    return (nums, 0, ids)


def _ref_compare(a, b):
    ka, kb = _ref_key(a), _ref_key(b)
    return (ka > kb) - (ka < kb)


_num = st.integers(min_value=0, max_value=12).map(str)
_ident = st.one_of(
    st.integers(min_value=0, max_value=12).map(str),
    st.sampled_from(["alpha", "beta", "rc", "a", "b", "x"]),
)
_release = st.lists(_num, min_size=1, max_size=3).map(".".join)
_prerelease = st.builds(
    lambda core, ids: ".".join(core) + "-" + ".".join(ids),
    st.lists(_num, min_size=3, max_size=3),
    st.lists(_ident, min_size=1, max_size=3),
)
_versions = st.one_of(_release, _prerelease)


# Numeric components are compared as numbers, not as strings.
# Source: "Implement semver precedence: numeric components compared as numbers"
def test_numeric_components():
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("1.9.0", "1.10.0") == -1
    assert compare("2.0.0", "1.99.99") == 1
    assert compare("1.2.10", "1.2.9") == 1
    assert compare("10.0.0", "9.9.9") == 1


# Missing components count as 0.
# Source: "missing components are 0 ('1.2' == '1.2.0')"
def test_missing_components_are_zero():
    assert compare("1.2", "1.2.0") == 0
    assert compare("1.2.0", "1.2") == 0
    assert compare("1", "1.0.0") == 0
    assert compare("1.2", "1.2.1") == -1
    assert compare("1.3", "1.2.9") == 1


# A pre-release sorts before its release but after the previous release.
# Source: "a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release"
def test_prerelease_before_release():
    for pre in ("1.0.0-alpha", "1.0.0-beta.2", "1.0.0-rc.1"):
        assert compare(pre, "1.0.0") == -1
        assert compare("1.0.0", pre) == 1
        assert compare(pre, "0.9.9") == 1
    assert compare("1.0.1-alpha", "1.0.0") == 1


# Pre-release identifiers order numerically when numeric, lexically otherwise, numeric before alphanumeric, and a prefix list first.
# Source: "pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other."
def test_prerelease_identifier_order():
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
    for i in range(len(chain)):
        assert compare(chain[i], chain[i]) == 0
        for j in range(i + 1, len(chain)):
            assert compare(chain[i], chain[j]) == -1, (chain[i], chain[j])
            assert compare(chain[j], chain[i]) == 1, (chain[j], chain[i])
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-rc.2", "1.0.0-rc.10") == -1


# For any two well-formed versions, compare returns -1, 0 or 1 according to semver precedence.
# Source: "Implement semver precedence: numeric components compared as numbers; missing components are 0 ('1.2' == '1.2.0'); a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other."
@given(a=_versions, b=_versions)
def test_compare_matches_precedence(a, b):
    got = compare(a, b)
    assert got in (-1, 0, 1)
    assert got == _ref_compare(a, b)
    assert compare(b, a) == -got


# latest returns a highest version by semver precedence, and None for an empty list.
# Source: "Implement semver precedence ... latest([]) stays None."
def test_latest_examples():
    assert latest([]) is None
    assert latest(["1.9.0", "1.10.0", "1.2.0"]) == "1.10.0"
    assert latest(["1.0.0-rc.1", "1.0.0", "1.0.0-beta"]) == "1.0.0"
    assert latest(["1.0.0-beta.2", "1.0.0-beta.11"]) == "1.0.0-beta.11"
    assert latest(["1.0.0", "1.2.0", "1.1.0"]) == "1.2.0"


# latest returns one of the given versions that no other given version exceeds.
# Source: "Implement semver precedence ... latest([]) stays None."
@given(vs=st.lists(_versions, min_size=1, max_size=8))
def test_latest_is_maximal(vs):
    best = latest(vs)
    assert best in vs
    for v in vs:
        assert _ref_compare(v, best) <= 0
