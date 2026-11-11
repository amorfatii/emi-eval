"""Git workspaces that look like a real project mid-task.

Layout per (task, condition):

    <work>/ws/<task>__<cond>/repo          the repository (baseline on main,
                                            work on branch `task`)
    <work>/ws/<task>__<cond>/state-warm    EMI state after `emi done --warm`
    <work>/ws/<task>__<cond>/state/<cand>  a fresh copy of it per candidate

Each candidate gets its own copy of the warmed state: the baseline's
recorded runs are reused (as they would be in a session), but nothing one
candidate taught EMI (approvals, remembered counterexamples) leaks into the
next. Suites that study memory on purpose share a state directory instead.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

GIT_ID = ["-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "-c", "commit.gpgsign=false"]
GITIGNORE = ".venv\n__pycache__/\n.pytest_cache/\n*.pyc\n.hypothesis/\n"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    out = subprocess.run(["git", *GIT_ID, *args], cwd=repo, capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(f"git {args}: {out.stderr.strip()}")
    return out


def write_files(repo: Path, files: dict) -> None:
    """Values: text; None to delete; ("symlink", target); or a callable that
    takes the file's current text and returns the new text."""
    for rel, text in files.items():
        path = repo / rel
        if callable(text):
            text = text(path.read_text(encoding="utf-8"))
        if isinstance(text, tuple) and text[0] == "symlink":
            if path.exists() or path.is_symlink():
                path.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(text[1], path)
            continue
        if text is None:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def ensure_venv(path: Path, extra: tuple[str, ...] = ()) -> Path:
    """A virtualenv with the versions EMI's own suite tests against."""
    marker = path / (".ready" + "".join("-" + e.replace("/", "_") for e in sorted(extra)))
    if marker.exists():
        return path
    if not (path / "bin" / "python").exists():
        subprocess.run(["python3", "-m", "venv", str(path)], check=True)
    pkgs = ["pytest>=8,<9", "coverage>=7.9,<8", "hypothesis>=6,<7", *extra]
    subprocess.run([str(path / "bin/python"), "-m", "pip", "install", "-q", *pkgs], check=True)
    marker.write_text("ok\n")
    return path


def link_venv(template: Path, repo: Path) -> None:
    """Hard-link copy: an in-repo .venv as `python3 -m venv .venv` would make,
    without paying for a pip install per workspace."""
    dest = repo / ".venv"
    if dest.exists():
        return
    subprocess.run(["cp", "-al", str(template), str(dest)], check=True)


class Workspace:
    def __init__(self, root: Path, emi: str, venv: Path):
        self.root = root
        self.repo = root / "repo"
        self.emi = emi
        self.venv = venv
        self.warm_state = root / "state-warm"

    # -- building ---------------------------------------------------------
    def build(self, files: dict[str, str], laws: dict[str, str] | None, config: dict,
              setup=None, link=True) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.repo.mkdir(parents=True)
        git(self.repo, "init", "-q", "-b", "main")
        write_files(self.repo, {".gitignore": GITIGNORE, **files})
        if laws:
            write_files(self.repo, {f".emi/laws/{k}": v for k, v in laws.items()})
        if link:
            link_venv(self.venv, self.repo)
        if setup:
            setup(str(self.repo))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "baseline")
        init = self.run_emi(["init", "--yes"], state=self.warm_state)
        if init.returncode != 0:
            raise RuntimeError(f"emi init failed: {init.stdout}\n{init.stderr}")
        cfg_path = self.repo / ".emi/config.json"
        cfg = merge(json.loads(cfg_path.read_text()), config)
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "Configure EMI")
        git(self.repo, "switch", "-q", "-c", "task")

    def warm(self) -> subprocess.CompletedProcess:
        return self.run_emi(["done", "--warm"], state=self.warm_state, timeout=1800)

    def config(self) -> dict:
        return json.loads(git(self.repo, "show", "main:.emi/config.json").stdout)

    # -- candidates -------------------------------------------------------
    def reset(self) -> None:
        git(self.repo, "switch", "-q", "task", check=False)
        git(self.repo, "reset", "-q", "--hard", "main")
        git(self.repo, "clean", "-q", "-fd")  # keeps ignored files (.venv)

    def apply(self, edits: dict[str, str | None], commit: bool = False) -> None:
        write_files(self.repo, edits)
        if commit:
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-q", "--allow-empty", "-m", "candidate")

    def fresh_state(self, name: str) -> Path:
        dest = self.root / "state" / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.warm_state.exists():
            shutil.copytree(self.warm_state, dest, symlinks=True)
        else:
            dest.mkdir()
        return dest

    # -- running ----------------------------------------------------------
    def run_emi(self, args: list[str], state: Path, env: dict | None = None,
                timeout: int = 1800, cwd: Path | None = None) -> subprocess.CompletedProcess:
        e = {k: v for k, v in os.environ.items() if not k.startswith("EMI_")}
        e.update({"XDG_STATE_HOME": str(state), "EMI_HOOK_WARM": "0"})
        if env:
            e.update(env)
        try:
            return subprocess.run([self.emi, *args], cwd=cwd or self.repo, env=e,
                                  capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as t:
            return subprocess.CompletedProcess(args, -9, t.stdout or "", f"harness timeout after {timeout}s")

    def tracked_and_untracked(self) -> list[str]:
        """What the project is on disk: tracked and untracked files, including
        ignored ones (a generated _version.py), but not caches or the venv."""
        out = git(self.repo, "ls-files", "-co", "--exclude=.venv", "--exclude=__pycache__",
                  "--exclude=.pytest_cache", "--exclude=.hypothesis", "--exclude=*.egg-info").stdout
        return [p for p in out.splitlines() if p and not p.startswith(".venv")]

    def snapshot(self, dest: Path) -> Path:
        """Copy of the candidate tree (what git sees, plus untracked files)."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for rel in self.tracked_and_untracked():
            src = self.repo / rel
            if src.is_symlink() or src.is_file():
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / rel, follow_symlinks=False)
        return dest

    def baseline_text(self, rel: str) -> str | None:
        out = git(self.repo, "show", f"main:{rel}", check=False)
        return out.stdout if out.returncode == 0 else None

    def baseline_files(self) -> list[str]:
        return [p for p in git(self.repo, "ls-tree", "-r", "--name-only", "main").stdout.splitlines() if p]
