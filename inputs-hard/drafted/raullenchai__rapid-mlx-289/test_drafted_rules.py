from hypothesis import given, strategies as st
from vllm_mlx.reasoning.gemma4_parser import Gemma4ReasoningParser
THOUGHT_OPEN = '<|channel>thought\n'
CLOSE = '<channel|>'
CONTENT_OPEN = '<|channel>content\n'
TURN_END = '<turn|>'

def _run(deltas):
    """Feed deltas through a fresh parser; return (reasoning, content, msgs)."""
    parser = Gemma4ReasoningParser()
    prev = ''
    reasoning, content, msgs = ('', '', [])
    for d in deltas:
        cur = prev + d
        msg = parser.extract_reasoning_streaming(prev, cur, d)
        prev = cur
        msgs.append(msg)
        if msg is not None:
            reasoning += msg.reasoning or ''
            content += msg.content or ''
    return (reasoning, content, msgs)

def test_straddling_delta_yields_one_message_with_both_fields():
    """A delta that ends reasoning and starts content produces a single DeltaMessage with both reasoning and content set."""
    r, c, msgs = _run([THOUGHT_OPEN + 'step one', '. Wyoming (WY)' + CLOSE + CONTENT_OPEN + '1. Alabama (AL)'])
    last = msgs[-1]
    assert last is not None
    assert last.reasoning == '. Wyoming (WY)'
    assert last.content == '1. Alabama (AL)'
    assert r == 'step one. Wyoming (WY)'
    assert c == '1. Alabama (AL)'

def test_trailing_reasoning_bytes_do_not_leak_into_content():
    """Reasoning bytes that arrive in the same delta before the close marker never appear in content."""
    r, c, _ = _run([THOUGHT_OPEN + 'abc', 'tail' + CLOSE + CONTENT_OPEN + 'answer'])
    assert 'tail' not in c
    assert c == 'answer'
    assert r == 'abctail'

def test_pure_content_without_channels_stays_content():
    """Plain text with no channel markers is routed to content."""
    r, c, _ = _run(['Hello ', 'world'])
    assert r == ''
    assert c == 'Hello world'
_text = st.text(alphabet='abcxyz .()0123', min_size=1, max_size=30)