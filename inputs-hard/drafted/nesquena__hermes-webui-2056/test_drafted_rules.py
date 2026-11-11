import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from api import config

def _setup(monkeypatch, name, model='deepseek-v4-flash', base_url='http://127.0.0.1:15721/v1'):
    monkeypatch.setitem(config.cfg, 'model', {})
    monkeypatch.setitem(config.cfg, 'custom_providers', [{'name': name, 'base_url': base_url, 'model': model}])

def test_slug_for_parenthesised_port_name_has_no_colon_after_prefix(monkeypatch):
    """The provider slug generated from 'Local (127.0.0.1:15721)' contains no ':' beyond the 'custom:' prefix."""
    _setup(monkeypatch, 'Local (127.0.0.1:15721)')
    _, provider, _ = config.resolve_model_provider('deepseek-v4-flash')
    assert ':' not in provider[len('custom:'):]
_names = st.text(alphabet=st.sampled_from(list('abcXYZ019 ()[]{}.:-_/')), min_size=1, max_size=30).filter(lambda s: s.strip() != '')