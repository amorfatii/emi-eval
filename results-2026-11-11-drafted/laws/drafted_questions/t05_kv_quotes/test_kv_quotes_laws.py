import pytest
from hypothesis import given, strategies as st

from kvparse import parse


def _baseline_parse(text):
    out = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, _, value = part.partition("=")
        out[key.strip()] = value.strip()
    return out


def _quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# A double-quoted value may contain ';' without being split.
# Source: "parse('a="x;y"; b=2') splits inside the quotes. Support double-quoted values that may contain ';' and '='."
def test_request_example():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}


# A double-quoted value may contain '=' and several ';', and the quotes are removed.
# Source: "Support double-quoted values that may contain ';' and '='. ... quotes are removed"
def test_quoted_value_with_equals_and_semicolons():
    assert parse('a="k=v"') == {"a": "k=v"}
    assert parse('a="x=1;y=2;"; b="z"') == {"a": "x=1;y=2;", "b": "z"}
    assert parse('a=""; b=1') == {"a": "", "b": "1"}


# Inside quotes, \" is a literal quote and \\ a literal backslash.
# Source: "Inside quotes, \" is a literal quote and \\ a literal backslash"
def test_escapes_inside_quotes():
    assert parse(r'a="say \"hi\""') == {"a": 'say "hi"'}
    assert parse(r'a="c:\\dir"; b=2') == {"a": "c:\\dir", "b": "2"}
    assert parse(r'a="\\"; b="\";"') == {"a": "\\", "b": '";'}


# Whitespace inside quotes is kept.
# Source: "quotes are removed and whitespace inside them kept"
def test_whitespace_inside_quotes_is_kept():
    assert parse('a="  x  "; b=1') == {"a": "  x  ", "b": "1"}
    assert parse('a= " x ;y "') == {"a": " x ;y "}


# An unterminated quote raises ValueError, including when the last quote is escaped.
# Source: "An unterminated quote raises ValueError."
def test_unterminated_quote_raises():
    for text in ['a="x;y', 'a="', 'a=1; b="open', r'a="abc\"', 'a="x; b=2']:
        with pytest.raises(ValueError):
            parse(text)


# Any string written as a quoted value (escaping \ and ") parses back to exactly that string.
# Source: "Support double-quoted values that may contain ';' and '='. Inside quotes, \" is a literal quote and \\ a literal backslash; quotes are removed and whitespace inside them kept."
@given(st.text(max_size=30), st.text(alphabet='ab;= \\"x', max_size=15))
def test_quoted_values_round_trip(v1, v2):
    text = "k=" + _quote(v1) + "; m=" + _quote(v2) + "; n=3"
    assert parse(text) == {"k": v1, "m": v2, "n": "3"}


# Text without any double quote parses exactly as the baseline did.
# Source: "Everything that parses today must parse the same."
@given(st.text(alphabet="ab1 =;\t\\x", max_size=30))
def test_unquoted_text_parses_as_before(text):
    assert parse(text) == _baseline_parse(text)


# The baseline examples still parse the same.
# Source: baseline behaviour, not asked to change: pairs, whitespace stripping and skipped empty segments
def test_baseline_examples_kept():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
    assert parse("  a  =  1  ") == {"a": "1"}
    assert parse("") == {}
    assert parse("flag") == {"flag": ""}
