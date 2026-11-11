## Task t05_kv_quotes

**Request to the coding agent:**

> parse('a="x;y"; b=2') splits inside the quotes. Support double-quoted values that may contain ';' and '='. Inside quotes, \" is a literal quote and \\ a literal backslash; quotes are removed and whitespace inside them kept. An unterminated quote raises ValueError. Everything that parses today must parse the same.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`kvparse.py`:

```python
def parse(text: str) -> dict:
    """Parse 'a=1; b=two' into {'a': '1', 'b': 'two'}.

    Whitespace around keys and values is ignored; empty segments are skipped.
    """
    out = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, _, value = part.partition("=")
        out[key.strip()] = value.strip()
    return out
```
`tests/test_kvparse.py`:

```python
from kvparse import parse


def test_pairs():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}


def test_empty_segments_are_skipped():
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
```
