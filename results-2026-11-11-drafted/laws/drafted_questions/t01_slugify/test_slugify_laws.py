import re
import string

from hypothesis import given, settings, strategies as st

from textutil import slugify


# The example from the request collapses separator runs and strips them from both ends.
# Source: "slugify('  Hello,  World! ') gives '--hello---world--'. It should give 'hello-world'"
def test_request_example():
    assert slugify("  Hello,  World! ") == "hello-world"


# The sep parameter keeps working: the collapsed separator is the given sep.
# Source: "Keep the `sep` parameter working."
def test_sep_parameter_is_used():
    assert slugify("  Hello,  World! ", sep="_") == "hello_world"
    assert slugify("a--b..c", sep=".") == "a.b.c"


# Text with nothing alphanumeric gives the empty string.
# Source: Q1 answer A: "the empty string ''"
def test_nothing_alphanumeric_gives_empty_string():
    assert slugify("!!! ???") == ""
    assert slugify("") == ""
    assert slugify("   ") == ""


# For ASCII text, the slug is the lowercased alphanumeric runs joined by exactly one sep.
# Source: "collapse every run of non-alphanumerics into one separator and strip separators from both ends"
@given(st.text(alphabet=string.printable, max_size=40), st.sampled_from(["-", "_", "."]))
def test_ascii_text_is_runs_joined_by_one_sep(text, sep):
    expected = sep.join(re.findall(r"[a-z0-9]+", text.lower()))
    assert slugify(text, sep=sep) == expected


# For any text, the default slug has no leading or trailing '-', no '--', and only [a-z0-9-].
# Source: "collapse every run of non-alphanumerics into one separator and strip separators from both ends"
@given(st.text(max_size=40))
def test_any_text_has_no_separator_runs_or_ends(text):
    out = slugify(text)
    assert re.fullmatch(r"[a-z0-9-]*", out)
    assert "--" not in out
    assert not out.startswith("-")
    assert not out.endswith("-")


# Slugs are lowercase and accents are folded to ASCII.
# Source: baseline behaviour, not asked to change: lowercasing and accent folding
def test_lowercase_and_accent_folding_kept():
    assert slugify("Hello") == "hello"
    assert slugify("Crème brûlée") == "creme-brulee"
