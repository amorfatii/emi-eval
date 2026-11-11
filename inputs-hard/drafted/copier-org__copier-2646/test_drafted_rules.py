import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from copier import _vcs
PREFIX = 'copier._vcs.clone.'

def _clones(root: Path):
    return [p for p in root.iterdir() if p.name.startswith(PREFIX)]

def _git(cwd, *args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd, check=True, capture_output=True)

def _make_template(path: Path) -> Path:
    path.mkdir()
    (path / 'copier.yml').write_text('name:\n  type: str\n  default: x\n')
    (path / 'f.txt.jinja').write_text('{{ name }}\n')
    _git(path, 'init', '-q')
    _git(path, 'add', '-A')
    _git(path, 'commit', '-qm', 'init')
    _git(path, 'tag', 'v1.0.0')
    return path

@pytest.fixture
def tmproot(tmp_path, monkeypatch):
    root = tmp_path / 'tmproot'
    root.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(root))
    return root

def _run_killed(tmp_path, tmproot, sig_name):
    tpl = _make_template(tmp_path / 'tpl')
    dst = tmp_path / 'dst'
    dst.mkdir()
    script = textwrap.dedent(f'\n        import os, signal, sys\n        import copier\n        from copier import _main\n\n        def boom(self, *a, **k):\n            os.kill(os.getpid(), signal.{sig_name})\n            import time; time.sleep(30)\n\n        _main.Worker._render_template = boom\n        copier.run_copy({str(tpl)!r}, {str(dst)!r}, vcs_ref="v1.0.0",\n                        data={{"name": "a"}}, defaults=True, quiet=True,\n                        unsafe=True)\n        ')
    env = dict(os.environ, TMPDIR=str(tmproot))
    subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, timeout=60)
    return _clones(tmproot)