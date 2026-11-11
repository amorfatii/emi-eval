import re
from hypothesis import given, strategies as st
from textutil import slugify
SEPS = st.sampled_from(['-', '_', '.', '~', '+'])

def test_task_example():
    """slugify('  Hello,  World! ') returns 'hello-world'."""
    assert slugify('  Hello,  World! ') == 'hello-world'

def test_runs_of_non_alphanumerics_collapse_to_one_separator():
    """A run of several non-alphanumerics between words becomes a single separator."""
    assert slugify('a !!!   b') == 'a-b'
    assert slugify('one,,,two...three') == 'one-two-three'

def test_leading_and_trailing_separators_are_stripped():
    """Separators at the start and end of the result are removed."""
    assert slugify('---abc---') == 'abc'
    assert slugify('!!hi!!') == 'hi'

def test_custom_sep_is_used_for_collapsing_and_stripping():
    """A custom sep joins words once per run and is stripped from both ends."""
    assert slugify('  Hello,  World! ', sep='_') == 'hello_world'
    assert slugify('  Hello,  World! ', sep='.') == 'hello.world'

def test_no_alphanumerics_gives_empty_string():
    """Input with no alphanumerics gives an empty string."""
    assert slugify('') == ''
    assert slugify('!!!') == ''
    assert slugify('  \t\n ') == ''
    assert slugify('!!!', sep='_') == ''

def test_lowercases_and_folds_accents():
    """Letters are lowercased and accents are folded to their ASCII base."""
    assert slugify('Hello') == 'hello'
    assert slugify('Crème brûlée') == 'creme-brulee'

def test_digits_are_kept():
    """Digits are alphanumerics and are kept."""
    assert slugify('Room 101, Floor 2') == 'room-101-floor-2'

@given(st.text(), SEPS)
def test_result_has_no_leading_or_trailing_sep(text, sep):
    """The result never starts or ends with the separator."""
    out = slugify(text, sep=sep)
    assert not out.startswith(sep)
    assert not out.endswith(sep)

@given(st.text(), SEPS)
def test_result_has_no_repeated_sep(text, sep):
    """The result never contains two separators in a row."""
    assert sep + sep not in slugify(text, sep=sep)

@given(st.text(), SEPS)
def test_result_only_alphanumerics_and_sep(text, sep):
    """The result contains only lowercase ASCII letters, digits and the separator."""
    out = slugify(text, sep=sep)
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789') | {sep}
    assert set(out) <= allowed

@given(st.text(alphabet=st.characters(blacklist_characters='-_.~+', max_codepoint=127)), SEPS)
def test_ascii_words_split_on_non_alphanumerics(text, sep):
    """For ASCII input, the result is the lowercase alphanumeric words joined by single separators."""
    words = re.findall('[a-z0-9]+', text.lower())
    assert slugify(text, sep=sep) == sep.join(words)