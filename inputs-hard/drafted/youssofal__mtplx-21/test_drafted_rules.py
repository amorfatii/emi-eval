import json
from hypothesis import given, settings, strategies as st
from mtplx.server.openai import _ToolAwareContentStreamTranslator
TOOLS = [{'type': 'function', 'function': {'name': 'grep', 'parameters': {'type': 'object', 'properties': {}}}}, {'type': 'function', 'function': {'name': 'glob', 'parameters': {'type': 'object', 'properties': {}}}}]
CALL_GREP = '<tool_call>\n<function=grep>\n<parameter=pattern>\nmountain\n</parameter>\n</function>\n</tool_call>'
CALL_GLOB = '<tool_call>\n<function=glob>\n<parameter=pattern>\nsrc/*.ts\n</parameter>\n</function>\n</tool_call>'
PREAMBLE = "I'll investigate the implementation systematically.\n\n"

def _run(chunks, tools=TOOLS):
    tr = _ToolAwareContentStreamTranslator(tools=tools, argument_chunk_chars=8)
    deltas = []
    for c in chunks:
        deltas.extend(tr.feed('content', c))
    deltas.extend(tr.finish())
    return (tr, deltas)

def _content(deltas):
    return ''.join((d.get('content', '') for d in deltas if 'content' in d))

def _tool_names(deltas):
    names = []
    for d in deltas:
        for tc in d.get('tool_calls', []) or []:
            fn = tc.get('function', {})
            if fn.get('name'):
                names.append(fn['name'])
    return names

def _split(text, sizes):
    out, i = ([], 0)
    for s in sizes:
        if i >= len(text):
            break
        out.append(text[i:i + s])
        i += s
    if i < len(text):
        out.append(text[i:])
    return out

def test_preamble_then_tool_call_emits_tool_calls():
    """A response of preamble text followed by a tool call produces tool_calls deltas."""
    tr, deltas = _run([PREAMBLE + CALL_GREP])
    assert _tool_names(deltas) == ['grep']
    assert tr.has_tool_calls

def test_preamble_text_is_streamed_as_content():
    """The text before the first tool call is sent as delta.content."""
    _, deltas = _run([PREAMBLE + CALL_GREP])
    assert _content(deltas).strip() == PREAMBLE.strip()

def test_no_tool_call_markup_leaks_into_content():
    """Raw tool_call markup never appears in delta.content when tool calls are emitted."""
    _, deltas = _run([PREAMBLE + CALL_GREP + '\n' + CALL_GLOB])
    assert '<tool_call' not in _content(deltas)
    assert '</tool_call>' not in _content(deltas)
    assert '<function=' not in _content(deltas)

def test_preamble_content_comes_before_tool_calls():
    """Content deltas for the preamble are sent before the tool_calls deltas."""
    _, deltas = _run([PREAMBLE + CALL_GREP])
    first_tool = next((i for i, d in enumerate(deltas) if 'tool_calls' in d))
    last_content = max((i for i, d in enumerate(deltas) if 'content' in d))
    assert last_content < first_tool

def test_multiple_tool_calls_after_preamble():
    """Several tool calls after preamble text are all emitted in order."""
    _, deltas = _run([PREAMBLE + CALL_GREP + '\n' + CALL_GLOB])
    assert _tool_names(deltas) == ['grep', 'glob']

def test_tool_call_arguments_are_parsed_after_preamble():
    """Tool call arguments after preamble text are delivered as the JSON arguments."""
    _, deltas = _run([PREAMBLE + CALL_GREP])
    args = ''.join((tc['function'].get('arguments', '') for d in deltas for tc in d.get('tool_calls', []) or []))
    assert json.loads(args) == {'pattern': 'mountain'}

def test_tool_only_response_still_works():
    """A response that starts with a tool call still yields tool calls and no content."""
    tr, deltas = _run([CALL_GREP])
    assert _tool_names(deltas) == ['grep']
    assert _content(deltas).strip() == ''

def test_text_only_response_is_content():
    """A response with no tool call is emitted entirely as content with no tool calls."""
    tr, deltas = _run(['Hello ', 'there, ', 'friend.'])
    assert _content(deltas) == 'Hello there, friend.'
    assert not tr.has_tool_calls
    assert _tool_names(deltas) == []

def test_marker_split_across_chunks_after_preamble():
    """A tool_call marker split across chunk boundaries after content is still recognised."""
    _, deltas = _run([PREAMBLE + '<tool_c', 'all>\n' + CALL_GREP[len('<tool_call>\n'):]])
    assert _tool_names(deltas) == ['grep']
    assert '<tool_c' not in _content(deltas)

def test_partial_marker_prefix_held_back():
    """A chunk ending in a possible marker prefix is not emitted as content until resolved."""
    tr = _ToolAwareContentStreamTranslator(tools=TOOLS, argument_chunk_chars=8)
    out = tr.feed('content', 'Some text <tool_c')
    assert '<tool_c' not in _content(out)
    assert '<' not in _content(out).replace('<', '', 0) or '<tool_c' not in _content(out)

def test_false_partial_marker_is_released_as_content():
    """A held-back partial marker that turns out not to be a marker is emitted as content."""
    tr, deltas = _run(['Compare a <tool_c', 'ar> thing and done.'])
    assert _content(deltas) == 'Compare a <tool_car> thing and done.'
    assert not tr.has_tool_calls

def test_trailing_partial_marker_at_end_is_content():
    """A partial marker still held when the stream ends is emitted as content."""
    _, deltas = _run(['Ends with <tool_c'])
    assert _content(deltas) == 'Ends with <tool_c'

def test_no_tools_passes_text_through():
    """When the request has no tools, text containing tool_call markup passes through as content."""
    text = PREAMBLE + CALL_GREP
    _, deltas = _run([text], tools=[])
    assert _content(deltas) == text
    assert _tool_names(deltas) == []

@settings(max_examples=60, deadline=None)
@given(sizes=st.lists(st.integers(min_value=1, max_value=12), min_size=1, max_size=40))
def test_chunking_does_not_change_result_for_mixed_response(sizes):
    """Splitting a preamble-plus-tool-call response at any chunk boundaries gives the same content and tool calls."""
    text = PREAMBLE + CALL_GREP + '\n' + CALL_GLOB
    _, deltas = _run(_split(text, sizes))
    assert _tool_names(deltas) == ['grep', 'glob']
    assert _content(deltas).strip() == PREAMBLE.strip()
    assert '<tool_call' not in _content(deltas)

@settings(max_examples=60, deadline=None)
@given(text=st.text(alphabet=st.characters(blacklist_characters='<', blacklist_categories=('Cs',)), min_size=1, max_size=80), sizes=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=20))
def test_plain_text_is_preserved_under_any_chunking(text, sizes):
    """Text without any marker is emitted unchanged as content however it is chunked."""
    tr, deltas = _run(_split(text, sizes))
    assert _content(deltas) == text
    assert not tr.has_tool_calls

@settings(max_examples=60, deadline=None)
@given(pre=st.text(alphabet=st.characters(blacklist_characters='<', blacklist_categories=('Cs',)), min_size=1, max_size=60), sizes=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=30))
def test_any_preamble_then_tool_call_dispatches_tool(pre, sizes):
    """For any marker-free preamble text, a following tool call is dispatched and the preamble is preserved."""
    _, deltas = _run(_split(pre + CALL_GREP, sizes))
    assert _tool_names(deltas) == ['grep']
    assert _content(deltas).strip() == pre.strip()
    assert '<tool_call' not in _content(deltas)