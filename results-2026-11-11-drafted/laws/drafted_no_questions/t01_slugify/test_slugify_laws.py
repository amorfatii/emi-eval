import re
import string

from hypothesis import given, strategies as st

from textutil import slugify, truncate


# The example from the request gives a slug with single separators and none at the ends.
# Source: "slugify('  Hello,  World! ') gives '--hello---world--'. It should give 'hello-world'"
def test_request_example():
    assert slugify("  Hello,  World! ") == "hello-world"


# For ASCII text, the slug is the lowercase alphanumeric runs joined by one separator, with no separator at either end.
# Source: "collapse every run of non-alphanumerics into one separator and strip separators from both ends"
@given(st.text(alphabet=string.printable, max_size=40))
def test_ascii_runs_collapse_and_ends_are_stripped(text):
    expected = "-".join(re.findall(r"[a-z0-9]+", text.lower()))
    assert slugify(text) == expected


# A custom separator is used in place of '-', with the same collapsing and stripping.
# Source: "Keep the `sep` parameter working."
@given(
    st.text(alphabet=string.printable, max_size=40),
    st.sampled_from(["_", ".", "+", "~"]),
)
def test_custom_sep_collapses_and_strips(text, sep):
    expected = sep.join(re.findall(r"[a-z0-9]+", text.lower()))
    assert slugify(text, sep=sep) == expected


# A custom separator works on the request example.
# Source: "Keep the `sep` parameter working."
def test_custom_sep_on_example():
    assert slugify("  Hello,  World! ", sep="_") == "hello_world"


# Text with no letters or digits gives an empty slug.
# Source: "strip separators from both ends"
def test_only_punctuation_gives_empty():
    assert slugify(" !?, -- ") == ""


# Accented letters are still folded to ASCII and the result lowercased.
# Source: baseline behaviour, not asked to change: accent folding and lowercasing in slugify
def test_accents_folded_and_lowercased():
    assert slugify("Crème  Brûlée!") == "creme-brulee"


# truncate keeps its behaviour.
# Source: baseline behaviour, not asked to change: truncate
def test_truncate_unchanged():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 5) == "hell…"
