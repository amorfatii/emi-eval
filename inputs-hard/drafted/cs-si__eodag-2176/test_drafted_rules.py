"""Acceptance rules: discover_queryables must merge provider and EODAG queryables
without failing on pydantic FieldInfo objects."""
from unittest import mock
from hypothesis import HealthCheck, given, settings, strategies as st
from typing_extensions import get_args
from eodag.api.provider import ProvidersDict
from eodag.config import load_default_config
from eodag.plugins.manager import PluginManager
_PLUGINS = PluginManager(ProvidersDict.from_configs(load_default_config()))

def _plugin():
    return next(_PLUGINS.get_search_plugins(provider='dedl'))

def _discover(properties):
    with mock.patch('eodag.plugins.search.qssearch.QueryStringSearch._request', autospec=True) as mock_request:
        mock_request.return_value = mock.Mock()
        mock_request.return_value.json.side_effect = [{'type': 'object', 'properties': properties}]
        return _plugin().discover_queryables(collection='CAMS_GAC_FORECAST', provider='dedl')

def test_overlapping_parameter_does_not_raise_attribute_error():
    """discover_queryables does not raise when a provider queryable overlaps an EODAG STAC queryable."""
    queryables = _discover({'start_datetime': {'title': 'Start datetime', 'type': 'string', 'format': 'date-time', 'description': 'provider start description'}, 'geometry': {'title': 'Geometry', 'description': 'provider geom'}})
    assert 'start' in queryables
    assert 'geom' in queryables

def test_overlapping_parameter_is_exposed_under_eodag_name():
    """A provider queryable overlapping an EODAG queryable is returned under the EODAG parameter name."""
    queryables = _discover({'start_datetime': {'title': 'S', 'type': 'string', 'format': 'date-time'}})
    assert 'start' in queryables
    assert 'start_datetime' not in queryables

def test_provider_only_parameter_is_kept():
    """A provider queryable that does not overlap an EODAG queryable is still returned."""
    queryables = _discover({'start_datetime': {'title': 'S', 'type': 'string'}, 'some_provider_param': {'title': 'Some param', 'type': 'integer', 'description': 'provider-only param'}})
    assert 'some_provider_param' in queryables
    args = get_args(queryables['some_provider_param'])
    assert args[0] is int
    assert args[1].description == 'provider-only param'

def test_overlapping_parameter_with_title_and_description_only():
    """An overlapping provider queryable with sparse attributes (no description or title) is still returned."""
    queryables = _discover({'start_datetime': {'type': 'string'}})
    assert 'start' in queryables

def test_overlapping_parameter_with_default_value():
    """An overlapping provider queryable carrying a default value is still returned."""
    queryables = _discover({'start_datetime': {'title': 'Start', 'type': 'string', 'format': 'date-time', 'default': '2021-01-01T00:00:00Z'}})
    assert 'start' in queryables

@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(title=st.one_of(st.none(), st.text(min_size=0, max_size=30)), description=st.one_of(st.none(), st.text(min_size=0, max_size=60)))
def test_overlapping_parameter_never_fails_for_any_title_and_description(title, description):
    """For any provider title and description (set, empty or missing), discovery of an overlapping queryable succeeds."""
    prop = {'type': 'string', 'format': 'date-time'}
    if title is not None:
        prop['title'] = title
    if description is not None:
        prop['description'] = description
    queryables = _discover({'start_datetime': prop})
    assert 'start' in queryables
    assert get_args(queryables['start'])[1] is not None

@settings(max_examples=25, deadline=None)
@given(description=st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=40))
def test_non_empty_provider_description_is_kept(description):
    """For any non-empty provider description on an overlapping queryable, the merged queryable keeps it."""
    queryables = _discover({'start_datetime': {'title': 'Start', 'type': 'string', 'format': 'date-time', 'description': description}})
    assert get_args(queryables['start'])[1].description == description