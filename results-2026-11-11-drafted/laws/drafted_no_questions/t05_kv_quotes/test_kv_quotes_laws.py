import pytest
from hypothesis import given, strategies as st

from kvparse import parse


def baseline_parse(text):
    out = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, _, value = part.partition("=")
        out[key.strip()] = value.strip()
    return out


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# The request's example keeps ';' inside the quoted value and removes the quotes.
# Source: "parse('a="x;y"; b=2') splits inside the quotes. Support double-quoted values that may contain ';' and '='."
def test_request_example():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}


# Quoted values may contain '=' and ';' in any combination.
# Source: "Support double-quoted values that may contain ';' and '='."
def test_equals_and_semicolons_inside_quotes():
    assert parse('a="k=v"') == {"a": "k=v"}
    assert parse('a="p=1;q=2"; b="="; c=3') == {"a": "p=1;q=2", "b": "=", "c": "3"}


# Inside quotes, an escaped quote is a literal quote and an escaped backslash a literal backslash.
# Source: "Inside quotes, \" is a literal quote and \\ a literal backslash"
def test_escapes_inside_quotes():
    assert parse(r'a="say \"hi\""') == {"a": 'say "hi"'}
    assert parse(r'a="c:\\dir"') == {"a": "c:\\dir"}
    assert parse(r'a="\\"; b=1') == {"a": "\\", "b": "1"}


# Whitespace inside quotes is kept, while whitespace around the pair is ignored.
# Source: "quotes are removed and whitespace inside them kept"
def test_whitespace_inside_quotes_kept():
    assert parse('a="  x  " ; b=1') == {"a": "  x  ", "b": "1"}
    assert parse(' a = " x;y " ; b = 2 ') == {"a": " x;y ", "b": "2"}


# A quote that is never closed raises ValueError, including when the last quote is escaped.
# Source: "An unterminated quote raises ValueError."
def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse('a="x')
    with pytest.raises(ValueError):
        parse('a="x; b=2')
    with pytest.raises(ValueError):
        parse(r'a="x\"')


# Any value, once quoted with escaped quotes and backslashes, parses back to itself alongside other pairs.
# Source: "Support double-quoted values that may contain ';' and '='. Inside quotes, \" is a literal quote and \\ a literal backslash; quotes are removed and whitespace inside them kept."
@given(
    st.lists(
        st.text(alphabet='ab ;="\\\t', max_size=12),
        min_size=1,
        max_size=4,
    )
)
def test_quoted_values_round_trip(values):
    keys = [f"k{i}" for i in range(len(values))]
    text = "; ".join(f"{k}={quote(v)}" for k, v in zip(keys, values))
    assert parse(text) == dict(zip(keys, values))


# Text without double quotes parses exactly as it did before.
# Source: "Everything that parses today must parse the same."
@given(st.text(alphabet="ab1 ;=\\\t_-.", max_size=30))
def test_unquoted_text_parses_as_before(text):
    assert parse(text) == baseline_parse(text)


# The baseline examples keep their results.
# Source: baseline behaviour, not asked to change: parse("a=1; b=two") and skipping empty segments
def test_baseline_examples():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
    assert parse("a") == {"a": ""}
