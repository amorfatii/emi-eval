## Task t01_slugify

**Request to the coding agent:**

> slugify leaves runs of separators and separators at the ends: slugify('  Hello,  World! ') gives '--hello---world--'. It should give 'hello-world': collapse every run of non-alphanumerics into one separator and strip separators from both ends. Keep the `sep` parameter working.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_slug.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

from textutil import slugify, truncate

def test_example():
    assert slugify("  Hello,  World! ") == "hello-world"

def test_collapse_mixed_runs():
    assert slugify("a--b__c  d") == "a-b-c-d"

def test_strip_ends():
    assert slugify("--a--") == "a"
    assert slugify("!!!") == ""
    assert slugify("") == ""

def test_custom_separator():
    assert slugify("Hello World", sep="_") == "hello_world"
    assert slugify("  a  b  ", sep="_") == "a_b"

def test_digits_kept():
    assert slugify("Top 10 Tips") == "top-10-tips"

def test_accents_folded():
    assert slugify("Cr\u00e8me br\u00fbl\u00e9e") == "creme-brulee"

def test_truncate_unchanged():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 5) == "hell\u2026"
    assert len(truncate("abcdefghij", 6)) == 6
```
