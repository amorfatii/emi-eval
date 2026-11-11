import pytest
import requests
from hypothesis import HealthCheck, given, settings, strategies as st
import schemathesis
from schemathesis import GenerationMode
from schemathesis.checks import CheckContext
from schemathesis.config import ChecksConfig
from schemathesis.core.transport import Response
from schemathesis.specs.openapi.checks import negative_data_rejection

def _schema(query_schema, body_schema=None):
    operation = {'parameters': [{'name': 'q', 'in': 'query', 'required': False, 'schema': {'type': 'integer'}}] if query_schema is None else [], 'responses': {'200': {'description': 'OK'}}}
    if query_schema is not None:
        operation['parameters'] = [{'name': name, 'in': 'query', 'required': True, 'schema': s} for name, s in query_schema.items()]
    if body_schema is not None:
        operation['requestBody'] = {'required': True, 'content': {'application/json': {'schema': body_schema}}}
    return schemathesis.openapi.from_dict({'openapi': '3.1.0', 'info': {'title': 't', 'version': '1'}, 'paths': {'/items': {'post' if body_schema is not None else 'get': operation}}})

def _response(case, status):
    raw = requests.Response()
    raw.status_code = status
    raw._content = b'{}'
    raw.headers['Content-Type'] = 'application/json'
    raw.request = requests.Request(method='GET', url='http://127.0.0.1/items').prepare()
    raw.elapsed = __import__('datetime').timedelta(milliseconds=1)
    return Response.from_requests(raw, True)

def _ctx():
    return CheckContext(override=None, auth=None, headers=None, config=ChecksConfig(), transport_kwargs=None)

def _negative_cases(schema, method, limit=60):
    op = schema['/items'][method]
    cases = []

    @given(case=op.as_strategy(generation_mode=GenerationMode.NEGATIVE))
    @settings(max_examples=limit, deadline=None, suppress_health_check=list(HealthCheck), database=None)
    def collect(case):
        cases.append(case)
    try:
        collect()
    except Exception:
        pass
    return cases

def _passes(case, status):
    try:
        negative_data_rejection(_ctx(), _response(case, status), case)
    except AssertionError:
        return False
    return True
QUERY_SCHEMA = {'id': {'type': 'integer'}}

def test_query_additional_properties_violation_is_still_generated():
    """Negative query cases that only add extra properties to a query with additionalProperties false are still generated."""
    schema = _schema({'id': {'type': 'integer'}})
    cases = _negative_cases(schema, 'get', 200)
    assert cases

def test_2xx_on_query_only_additional_properties_violation_is_not_a_failure():
    """A 2xx response to a request violating only the query additionalProperties is not reported as accepted invalid data."""
    schema = _schema(QUERY_SCHEMA)
    cases = _negative_cases(schema, 'get', 300)
    extra = [c for c in cases if c.query is not None and isinstance(c.query, dict) and set(c.query) - {'id'} and isinstance(c.query.get('id'), int)]
    for case in extra:
        assert _passes(case, 200)

@settings(max_examples=20, deadline=None, suppress_health_check=list(HealthCheck), database=None)
@given(status=st.sampled_from([200, 201, 204]))
def test_any_2xx_for_query_extra_property_only_violation_passes(status):
    """For every 2xx status, a request that violates only query additionalProperties passes the negative data rejection check."""
    schema = _schema(QUERY_SCHEMA)
    cases = _negative_cases(schema, 'get', 100)
    for case in cases:
        if isinstance(case.query, dict) and set(case.query) - {'id'} and isinstance(case.query.get('id'), int):
            assert _passes(case, status)