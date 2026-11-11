## Task t09_semver

**Request to the coding agent:**

> compare() orders versions as strings, so 1.10.0 < 1.9.0. Implement semver precedence: numeric components compared as numbers; missing components are 0 ('1.2' == '1.2.0'); a pre-release ('-alpha', '-beta.2', '-rc.1') sorts before its release; pre-release identifiers compare numerically when numeric, lexically otherwise, numeric before alphanumeric, and a shorter identifier list sorts first when it is a prefix of the other. latest([]) stays None.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_semver.py`:

```python

from versions import compare, latest
CHAIN = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0', '1.0.1', '1.9.0', '1.10.0', '2.0.0']

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
```
