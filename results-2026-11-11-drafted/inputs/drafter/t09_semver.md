## Task t09_semver

**Request to the coding agent:**

> compare() orders versions as strings, so 1.10.0 < 1.9.0. Implement semver precedence: numeric components compared as numbers; missing components are 0 ('1.2' == '1.2.0'); a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other. latest([]) stays None.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`tests/test_versions.py`:

```python
from versions import compare, latest


def test_equal():
    assert compare("1.2.3", "1.2.3") == 0


def test_patch_order():
    assert compare("1.2.3", "1.2.4") == -1


def test_latest():
    assert latest(["1.0.0", "1.2.0", "1.1.0"]) == "1.2.0"
```
`versions.py`:

```python
def parse_version(v: str) -> tuple:
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
```
