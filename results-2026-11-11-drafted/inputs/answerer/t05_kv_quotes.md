## Task t05_kv_quotes

**Request to the coding agent:**

> parse('a="x;y"; b=2') splits inside the quotes. Support double-quoted values that may contain ';' and '='. Inside quotes, \" is a literal quote and \\ a literal backslash; quotes are removed and whitespace inside them kept. An unterminated quote raises ValueError. Everything that parses today must parse the same.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_kv.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

from kvparse import parse

def test_quoted_separators():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}
    assert parse('a="k=v"') == {"a": "k=v"}

def test_whitespace_inside_quotes_kept():
    assert parse('a="  sp  "') == {"a": "  sp  "}

def test_escapes():
    assert parse(r'a="say \"hi\""') == {"a": 'say "hi"'}
    assert parse(r'a="back\\slash"') == {"a": "back\\slash"}

def test_unterminated_raises():
    assert raises(ValueError, parse, 'a="oops')

def test_old_inputs_unchanged():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
    assert parse("a==b") == {"a": "=b"}
    assert parse("k") == {"k": ""}
    assert parse("") == {}
    assert parse("  spaced key  =  v  ") == {"spaced key": "v"}
```
