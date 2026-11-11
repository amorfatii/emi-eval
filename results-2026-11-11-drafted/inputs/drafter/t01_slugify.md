## Task t01_slugify

**Request to the coding agent:**

> slugify leaves runs of separators and separators at the ends: slugify('  Hello,  World! ') gives '--hello---world--'. It should give 'hello-world': collapse every run of non-alphanumerics into one separator and strip separators from both ends. Keep the `sep` parameter working.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`tests/test_textutil.py`:

```python
from textutil import slugify, truncate


def test_slugify_lowercases():
    assert slugify("Hello") == "hello"


def test_slugify_folds_accents():
    assert slugify("Cr\u00e8me br\u00fbl\u00e9e") == "creme-brulee"


def test_truncate_short_text_is_kept():
    assert truncate("hello", 10) == "hello"
```
`textutil.py`:

```python
import re
import unicodedata


def slugify(text: str, sep: str = "-") -> str:
    """Lowercase ASCII slug of `text`."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", sep, text)
    return text


def truncate(text: str, width: int) -> str:
    """Cut text to at most `width` characters, ending in an ellipsis when cut."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "\u2026"
```
