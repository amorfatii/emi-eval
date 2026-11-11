"""Pieces every synthetic project shares."""

PYTEST_INI = "[pytest]\npythonpath = .\n"

# Oracle modules run under a plain runner; this is their pytest.raises.
RAISES = '''
def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")
'''


def project(**files: str) -> dict[str, str]:
    """A flat project: files given as keyword args with '__' for '/' and
    '_dot_' for '.', e.g. tests__test_app_dot_py."""
    out = {"pytest.ini": PYTEST_INI}
    for k, v in files.items():
        out[k.replace("__", "/").replace("_dot_", ".")] = v
    return out
