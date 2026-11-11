"""Project shapes: does EMI work on the layouts real Python projects have?

Each shape is a small project with one realistic structural feature, and
two candidates: `gold` (a fix with a proving test: the right answer is
stop) and `regress` (breaks an old test: the right answer is repair).
What is measured is whether EMI reaches the right answer at all, or ends
in incomplete, a usage error or a crash, and how long it takes.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from emi_evals.model import CORRECT as OK, INCORRECT as BAD, Candidate as C, Task, sub
from .common import PYTEST_INI, RAISES

CORE = '''def tax(amount: float, rate: float = 0.2) -> float:
    """Tax on `amount`, rounded to cents.

    >>> tax(10)
    2.0
    """
    if amount < 0:
        raise ValueError("negative amount")
    return round(amount * rate, 2)


def gross(amount: float, rate: float = 0.2) -> float:
    """Amount plus tax.

    >>> gross(10)
    12.0
    """
    return round(amount + tax(amount, rate), 2)
'''
# the task: a zero amount must be allowed and a negative rate rejected
CORE_FIX = sub(CORE, '    if amount < 0:\n        raise ValueError("negative amount")\n',
               '    if amount < 0:\n        raise ValueError("negative amount")\n    if rate < 0:\n        raise ValueError("negative rate")\n')
CORE_BROKEN = sub(CORE_FIX, "    return round(amount + tax(amount, rate), 2)\n", "    return round(amount + tax(amount, rate) + 0.01, 2)\n")

ORACLE = RAISES + '''
def _mod():
    import importlib
    for name in ("shop.core", "core", "app.core", "lib.core"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    raise ImportError("no core module")

def test_rate_rejected():
    m = _mod()
    assert raises(ValueError, m.tax, 10, -0.1)

def test_old():
    m = _mod()
    assert m.tax(10) == 2.0 and m.gross(10) == 12.0
    assert raises(ValueError, m.tax, -1)
'''


def tests_for(mod: str) -> str:
    return f'''import pytest
from {mod} import tax, gross


def test_tax():
    assert tax(10) == 2.0


def test_gross():
    assert gross(10) == 12.0


def test_negative_amount():
    with pytest.raises(ValueError):
        tax(-1)
'''


def new_test(mod: str) -> str:
    return f"import pytest\nfrom {mod} import tax\n\n\ndef test_negative_rate():\n    with pytest.raises(ValueError):\n        tax(10, -0.1)\n"


def shape(sid, title, files, core_path, mod, new_test_path="tests/test_rate.py", extra_gold=None, **kw):
    gold = {core_path: CORE_FIX, new_test_path: new_test(mod), **(extra_gold or {})}
    return Task(
        id=f"s_{sid}", title=title, kind="bugfix",
        prompt="tax() accepts a negative rate; it must raise ValueError for one.",
        files=files, oracle={"check_core.py": ORACLE},
        candidates=[
            C("gold", OK, "gold", gold, expect_actions=("stop",)),
            C("regress", BAD, "regress_covered", {core_path: CORE_BROKEN, new_test_path: new_test(mod)},
              expect_actions=("repair",)),
        ],
        conditions=("tests_only",), tags=("shapes",), **kw)


def _pip_editable(repo: str) -> None:
    subprocess.run([os.path.join(repo, ".venv/bin/python"), "-m", "pip", "install", "-q", "--no-deps",
                    "--no-build-isolation", "-e", repo], check=True, capture_output=True)


def _version_file(repo: str) -> None:
    Path(repo, "shop/_version.py").write_text('version = "1.2.3"\n')


def _symlinked_venv(repo: str) -> None:
    # replace the in-repo copy with a symlink to a venv outside the repository,
    # as a central virtualenv manager (poetry, pyenv-virtualenv, uv with a
    # shared env) would leave it
    venv = Path(repo, ".venv")
    outside = Path(repo).parent.parent / "central-venv"
    if not outside.exists():
        subprocess.run(["cp", "-al", str(venv), str(outside)], check=True)
    subprocess.run(["rm", "-rf", str(venv)], check=True)
    venv.symlink_to(outside)


LARGE_TESTS = {f"tests/test_bulk_{i:02d}.py": "import pytest\nfrom core import tax\n\n\n@pytest.mark.parametrize('n', range(30))\n"
               f"def test_many_{i}(n):\n    assert tax(n * 10) == round(n * 10 * 0.2, 2)\n" for i in range(20)}

TASKS = [
    shape("flat", "Flat module, pytest.ini", {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core")},
          "core.py", "core"),
    shape("src_editable", "src layout installed in editable mode",
          {"pyproject.toml": '[build-system]\nrequires = ["setuptools>=61"]\nbuild-backend = "setuptools.build_meta"\n\n'
           '[project]\nname = "shop"\nversion = "0.1.0"\n\n[tool.setuptools.packages.find]\nwhere = ["src"]\n\n'
           '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
           "src/shop/__init__.py": "", "src/shop/core.py": CORE, "tests/test_core.py": tests_for("shop.core")},
          "src/shop/core.py", "shop.core", setup=_pip_editable, pip=("setuptools",), python_path=("src",)),
    shape("pyproject_only", "pytest configured only in pyproject.toml",
          {"pyproject.toml": '[tool.pytest.ini_options]\npythonpath = ["."]\ntestpaths = ["tests"]\naddopts = "-ra"\n',
           "core.py": CORE, "tests/test_core.py": tests_for("core")}, "core.py", "core"),
    shape("tests_in_package", "tests inside the package, *_test.py naming",
          {"pytest.ini": PYTEST_INI + "python_files = *_test.py\n", "app/__init__.py": "", "app/core.py": CORE,
           "app/tests/__init__.py": "", "app/tests/core_test.py": tests_for("app.core")},
          "app/core.py", "app.core", new_test_path="app/tests/rate_test.py"),
    shape("unittest_classes", "unittest.TestCase classes in test/",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "test/test_core.py": '''import unittest
from core import tax, gross


class TaxTest(unittest.TestCase):
    def test_tax(self):
        self.assertEqual(tax(10), 2.0)

    def test_gross(self):
        self.assertEqual(gross(10), 12.0)

    def test_negative(self):
        with self.assertRaises(ValueError):
            tax(-1)
'''}, "core.py", "core", new_test_path="test/test_rate.py"),
    shape("inherited_tests", "test base class run under two subclasses",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": '''from core import tax, gross


class Base:
    rate = 0.2

    def test_tax(self):
        assert tax(10, self.rate) == round(10 * self.rate, 2)

    def test_gross(self):
        assert gross(10, self.rate) == round(10 + 10 * self.rate, 2)


class TestStandard(Base):
    rate = 0.2


class TestReduced(Base):
    rate = 0.05
'''}, "core.py", "core"),
    shape("doctests", "doctests collected through addopts",
          {"pytest.ini": PYTEST_INI + "addopts = --doctest-modules\ntestpaths = core.py tests\n", "core.py": CORE,
           "tests/test_core.py": "from core import tax\n\n\ndef test_tax():\n    assert tax(10) == 2.0\n"}, "core.py", "core"),
    shape("conftest_data", "conftest fixtures and a data file the product reads",
          {"pytest.ini": PYTEST_INI, "core.py": CORE + '''

def rates():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "rates.json").read_text())
''', "rates.json": '{"standard": 0.2}\n',
           "tests/conftest.py": "import pytest\nfrom core import rates\n\n\n@pytest.fixture\ndef standard():\n    return rates()['standard']\n",
           "tests/test_core.py": tests_for("core") + "\n\ndef test_rate_file(standard):\n    assert standard == 0.2\n"},
          "core.py", "core", extra_gold={"core.py": CORE_FIX + '''

def rates():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "rates.json").read_text())
'''}),
    shape("weird_param_ids", "parametrize ids with brackets, unicode, backslashes and '::'",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core") + '''

@pytest.mark.parametrize("amount,expected", [(10, 2.0), (0, 0.0), (5, 1.0)],
                         ids=["ten [EUR]", "zero::nothing", "f\\u00fcnf \\\\ back"])
def test_param(amount, expected):
    assert tax(amount) == expected
'''}, "core.py", "core"),
    shape("subprocess_tmp_path", "tests that spawn the interpreter and write to tmp_path",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core") + '''

def test_cli(tmp_path):
    import subprocess, sys
    out = tmp_path / "out.txt"
    subprocess.run([sys.executable, "-c", f"from core import gross; open({str(out)!r}, 'w').write(str(gross(10)))"],
                   check=True)
    assert out.read_text() == "12.0"
'''}, "core.py", "core"),
    shape("generated_ignored_module", "package imports a git-ignored generated _version.py",
          {"pytest.ini": PYTEST_INI, ".gitignore": ".venv\n__pycache__/\nshop/_version.py\n",
           "shop/__init__.py": "from ._version import version\n", "shop/core.py": CORE,
           "tests/test_core.py": tests_for("shop.core")}, "shop/core.py", "shop.core", setup=_version_file),
    shape("network_test", "an old test that needs the network (fails in any sandbox)",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core") + '''

def test_reaches_the_internet():
    import urllib.request
    urllib.request.urlopen("https://example.com", timeout=5)
'''}, "core.py", "core"),
    shape("hypothesis_in_suite", "Hypothesis properties in the ordinary test suite",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core") + '''

from hypothesis import given, strategies as st


@given(st.floats(0, 1e6))
def test_gross_is_amount_plus_tax(a):
    assert gross(a) == round(a + tax(a), 2)
'''}, "core.py", "core"),
    shape("venv_outside_repo", "the .venv is a symlink to a virtualenv outside the repository",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core")}, "core.py", "core",
          setup=_symlinked_venv),
    shape("large_suite", "600 tests over 21 files (latency)",
          {"pytest.ini": PYTEST_INI, "core.py": CORE, "tests/test_core.py": tests_for("core"), **LARGE_TESTS}, "core.py", "core"),
]
