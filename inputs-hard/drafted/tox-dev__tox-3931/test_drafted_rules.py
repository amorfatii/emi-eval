import json
from pathlib import Path
import pytest
from hypothesis import given, strategies as st
import tox
from tox.session.cmd.schema import _process_type
from tox.tox_env.python.pip.req_file import PythonDeps
jsonschema = pytest.importorskip('jsonschema')
SCHEMA_FILE = Path(tox.__file__).parent / 'tox.schema.json'

def _validator(subschema):
    full = json.loads(SCHEMA_FILE.read_text(encoding='utf-8'))
    wrapped = {**subschema, 'definitions': full.get('definitions', {})}
    return jsonschema.Draft7Validator(wrapped)

def _generated_deps():
    return _process_type(PythonDeps)

def _published_deps():
    full = json.loads(SCHEMA_FILE.read_text(encoding='utf-8'))
    return full['properties']['env_run_base']['properties']['deps']

@pytest.fixture(params=['generated', 'published'])
def deps_validator(request):
    sub = _generated_deps() if request.param == 'generated' else _published_deps()
    return _validator(sub)