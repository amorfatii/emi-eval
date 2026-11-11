"""Real-world track (trial C): real repositories, real issues, real agent patches.

Inputs are fixed before any run by `tools/build_inputs.py` and committed in
`inputs-rebench/`: one task per project from nebius/SWE-bench-extra (a real
GitHub issue, the developers' fix, and its hidden tests FAIL_TO_PASS and
PASS_TO_PASS), and agent patches for that task from
nebius/SWE-agent-trajectories with the dataset's resolved/unresolved label.
The run reads those files; it fetches only the projects (GitHub) and their
dependencies (PyPI).

Ground truth is re-graded here, in the environment EMI runs in: the hidden
test patch is applied to the candidate and FAIL_TO_PASS plus PASS_TO_PASS are
run; resolved means all pass. Agreement with the dataset's label is reported,
so environment drift is visible rather than hidden. A project whose
environment does not reproduce the task (the hidden tests must fail before
the developers' fix and all pass with it) is recorded as rejected, with why.

Conditions (EMI and the small script are both run on every candidate):
  visible     what a project has before the task: its own tests, EMI defaults,
              the test command narrowed to the task's own test files.
  spec_laws   the person wrote the acceptance tests first: the test files the
              hidden test patch touches are committed as laws, keeping their
              directory layout and the setup files beside them (conftest.py,
              __init__.py, helpers, data). This is the ceiling: EMI given the
              grader's own spec.
  full_suite  the developers' fix only, with the project's whole test suite:
              how long a check takes when the command is not narrowed.

The small script is the suites' `restore` gate: put back the baseline's test
files and runner configuration, drop added runner configuration, run the
same command, accept on exit 0 (and, with laws, the baseline's laws too).

Times: the project's own run of the same command at the baseline (one
discarded warm-up, then timed), EMI's one-time baseline warm-up, and each
check. The developers' fix is checked twice from fresh state copies; the two
decisions must be identical.

Usage:
  python -m tracks.rebench prepare --inputs inputs-rebench --work W --out OUT
  python -m tracks.rebench run --inputs inputs-rebench --emi PATH --work W --out OUT
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from emi_evals import receipt  # noqa: E402
from emi_evals.workspace import GIT_ID, git  # noqa: E402

PER_LABEL = 2  # distinct agent patches kept per label (resolved / unresolved) per task
RUNNER_CONFIG = {"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", "conftest.py",
                 "sitecustomize.py", "usercustomize.py"}
IGNORED = "\n.venv\n__pycache__/\n*.egg-info/\n.pytest_cache/\n.hypothesis/\n"


def sh(cmd, cwd=None, timeout=900, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def pinned_env(extra: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("EMI_", "PYTEST", "HYPOTHESIS", "PYTHON"))}
    env.update({"PYTHONHASHSEED": "0", "TZ": "UTC", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(extra or {})
    return env


def is_test_file(rel: str) -> bool:
    base = os.path.basename(rel)
    return base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))


def touched_files(patch: str) -> list[str]:
    return sorted(set(re.findall(r"^\+\+\+ b/(\S+)", patch, flags=re.M)))


def distinct(attempts: list[dict]) -> list[dict]:
    seen, out = set(), []
    for a in attempts:
        key = "\n".join(line.rstrip() for line in a["patch"].strip().splitlines())
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out


def choose(attempts: list[dict]) -> list[dict]:
    """The first PER_LABEL distinct patches per label, in the inputs' order."""
    res = distinct([a for a in attempts if a["target"] == "True"])[:PER_LABEL]
    unres = distinct([a for a in attempts if a["target"] == "False"])[:PER_LABEL]
    return res + unres


def pytest_ids(py: Path, repo: Path, ids: list[str], timeout=900) -> dict[str, str]:
    """Outcome per test id, via a junit report."""
    report = repo.parent / (repo.name + "-junit.xml")
    report.unlink(missing_ok=True)
    files = sorted({i.split("::")[0] for i in ids})
    env = tree_env(repo)
    sh([str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", f"--junitxml={report}", *files],
       cwd=repo, timeout=timeout, env=env)
    out: dict[str, str] = {}
    if report.exists():
        for tc in ET.parse(report).getroot().iter("testcase"):
            cls, name = tc.get("classname", ""), tc.get("name", "")
            status = "passed"
            for child in tc:
                if child.tag in ("failure", "error"):
                    status = "failed"
                elif child.tag == "skipped":
                    status = "skipped"
            out[f"{cls}::{name}"] = status
    res = {}
    for i in ids:
        path, _, rest = i.partition("::")
        mod = path[:-3].replace("/", ".")
        key = f"{mod}::{rest.replace('::', '.')}" if "::" in rest else f"{mod}::{rest}"
        # junit joins classes into classname; try both spellings
        cand = [key, f"{mod}.{rest.rsplit('::', 1)[0]}::{rest.rsplit('::', 1)[-1]}" if "::" in rest else key]
        res[i] = next((out[k] for k in cand if k in out), "missing")
    return res


def apply_patch(repo: Path, patch: str) -> bool:
    if not patch.strip():
        return False
    p = repo.parent / (repo.name + ".patch")
    p.write_text(patch if patch.endswith("\n") else patch + "\n")
    for cmd in (["git", *GIT_ID, "apply", "--whitespace=nowarn", str(p)],
                ["git", *GIT_ID, "apply", "--3way", "--whitespace=nowarn", str(p)],
                ["patch", "-p1", "--forward", "-i", str(p)]):
        if sh(cmd, cwd=repo).returncode == 0:
            return True
    return False


def lay_laws(repo: Path, spec: Path, files: list[str]) -> list[str]:
    """Copy the hidden test files into .emi/laws at their own paths, with the
    setup they need: conftest.py and __init__.py of every directory between
    the repository root and the file, and, in a test directory, the files
    beside it that are not other tests (helpers, data). The repository root's
    own files are not copied: pytest already loads its conftest.py, and a
    copy of the product beside the laws would test that copy."""
    laws = repo / ".emi/laws"
    laid = []
    for f in files:
        if not is_test_file(f) or not (spec / f).exists():
            continue
        rel = Path(f)
        (laws / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec / rel, laws / rel)
        laid.append(f)
        for d in [rel.parent, *rel.parent.parents]:
            if d == Path("."):
                break
            for name in ("conftest.py", "__init__.py"):
                if (spec / d / name).is_file():
                    shutil.copy2(spec / d / name, laws / d / name)
        here = rel.parent
        if here != Path(".") and any("test" in part for part in here.parts):
            for item in (spec / here).iterdir():
                if item.name == "__pycache__" or is_test_file(item.name) or (laws / here / item.name).exists():
                    continue
                if item.is_dir():
                    shutil.copytree(item, laws / here / item.name, symlinks=True,
                                    ignore=shutil.ignore_patterns("__pycache__", "test_*.py", "*_test.py"))
                else:
                    shutil.copy2(item, laws / here / item.name)
    return laid


def tree_env(tree: Path) -> dict:
    """Import the tree under test first, never the checkout an editable
    install points at."""
    roots = [str(tree / "src")] if (tree / "src").is_dir() else []
    return pinned_env({"PYTHONPATH": os.pathsep.join([*roots, str(tree)])})


def timed(cmd: list[str], cwd: Path, timeout: int = 3600) -> dict:
    t0 = time.monotonic()
    try:
        out = sh(cmd, cwd=cwd, timeout=timeout, env=tree_env(cwd))
        code = out.returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    return {"seconds": round(time.monotonic() - t0, 2), "exit": code}


def script_check(repo: Path, command: list[str], laws_command: list[str] | None) -> dict:
    """The small script: baseline tests and runner config put back, the same
    command run, accept on exit 0; with laws, the baseline's laws must pass too."""
    dest = repo.parent / "script-tree"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(repo, dest, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    base = set(sh(["git", "ls-tree", "-r", "--name-only", "main"], cwd=repo).stdout.split("\n")) - {""}
    for rel in base:
        restore = rel.startswith(".emi/laws/") or (not rel.startswith(".emi/") and (
            is_test_file(rel) or os.path.basename(rel) in RUNNER_CONFIG))
        if restore:
            blob = subprocess.run(["git", "show", f"main:{rel}"], cwd=repo, capture_output=True).stdout
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            (dest / rel).write_bytes(blob)
    for path in dest.rglob("*"):
        rel = str(path.relative_to(dest))
        if rel.startswith(".venv"):
            continue
        added_config = os.path.basename(rel) in RUNNER_CONFIG
        added_law = rel.startswith(".emi/laws/")
        if path.is_file() and not path.is_symlink() and (added_config or added_law) and rel not in base:
            path.unlink()
    t0 = time.monotonic()
    tests = timed(command, dest)
    accept = tests["exit"] == 0
    why = f"tests exit {tests['exit']}"
    if laws_command and accept:
        laws = timed(laws_command, dest)
        accept = laws["exit"] == 0
        why += f", laws exit {laws['exit']}"
    shutil.rmtree(dest, ignore_errors=True)
    return {"accept": accept, "why": why, "seconds": round(time.monotonic() - t0, 2)}


class Instance:
    def __init__(self, work: Path, task: dict, attempts: list[dict], python: str = "python3",
                 packages: list[str] | None = None):
        self.task, self.attempts, self.python, self.packages = task, attempts, python, packages or []
        self.id = task["instance_id"]
        self.root = work / "rebench" / self.id
        self.src = self.root / "src"
        self.venv = self.root / "venv"
        self.f2p, self.p2p = list(task["FAIL_TO_PASS"]), list(task["PASS_TO_PASS"])
        self.unmatched: list[str] = []

    # -- environment -------------------------------------------------------
    def prepare(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.src / ".git").exists():
            self.src.mkdir(parents=True, exist_ok=True)
            git(self.src, "init", "-q")
            url = f"https://github.com/{self.task['repo']}"
            got = sh(["git", "fetch", "-q", "--depth", "1", url, self.task["base_commit"]], cwd=self.src, timeout=900)
            if got.returncode != 0:
                return {"ok": False, "why": "fetch: " + got.stderr[-300:]}
            git(self.src, "checkout", "-q", "FETCH_HEAD")
        py = self.venv / "bin" / "python"
        if not (self.venv / ".ready").exists():
            sh([self.python, "-m", "venv", "--clear", str(self.venv)])
            base = sh([str(py), "-m", "pip", "install", "-q", "pytest>=8,<9", "coverage>=7.9,<8", "hypothesis>=6,<7",
                       "setuptools", "wheel"], timeout=900)
            if base.returncode != 0:
                return {"ok": False, "why": "pip base: " + base.stderr[-300:]}
            for extra in ("[test]", "[tests]", "[testing]", "[dev]", ""):
                if sh([str(py), "-m", "pip", "install", "-q", "-e", f".{extra}"], cwd=self.src, timeout=900).returncode == 0:
                    break
            for req in ("requirements-dev.txt", "requirements_dev.txt", "test-requirements.txt",
                        "requirements-test.txt", "requirements/test.txt", "requirements/dev.txt"):
                if (self.src / req).exists():
                    sh([str(py), "-m", "pip", "install", "-q", "-r", req], cwd=self.src, timeout=900)
            (self.venv / ".ready").write_text("ok\n")
        if self.packages:
            extra = sh([str(py), "-m", "pip", "install", "-q", *self.packages], timeout=900)
            if extra.returncode != 0:
                return {"ok": False, "why": "pip " + " ".join(self.packages) + ": " + extra.stderr[-300:]}
        return self.validate(py)

    def tree(self, name: str, patches: list[str]) -> Path | None:
        dest = self.root / "trees" / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.src, dest, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        for p in patches:
            if not apply_patch(dest, p):
                return None
        return dest

    def grade(self, py: Path, patch: str | None, name: str) -> dict:
        patches = [patch] if patch is not None else []
        t = self.tree(name, [*patches, self.task["test_patch"]])
        if t is None:
            return {"applies": False}
        res = pytest_ids(py, t, self.f2p + self.p2p)
        f2p = [i for i in self.f2p if i not in self.unmatched]
        p2p = [i for i in self.p2p if i not in self.unmatched]
        f2p_ok = all(res[i] == "passed" for i in f2p)
        p2p_ok = all(res[i] == "passed" for i in p2p)
        return {"applies": True, "resolved": f2p_ok and p2p_ok, "f2p_ok": f2p_ok, "p2p_ok": p2p_ok,
                "failed": [i for i in f2p + p2p if res[i] != "passed"][:8], "outcomes": res}

    def validate(self, py: Path) -> dict:
        before = self.grade(py, None, "validate-base")
        after = self.grade(py, self.task["patch"], "validate-gold")
        # a dataset id that names no test at the baseline nor with the fix is
        # malformed, not failing: it is left out of every grade, and listed
        self.unmatched = sorted(i for i in self.f2p + self.p2p
                                if before.get("outcomes", {}).get(i) == "missing"
                                and after.get("outcomes", {}).get(i) == "missing")
        if self.unmatched:
            before = self.grade(py, None, "validate-base")
            after = self.grade(py, self.task["patch"], "validate-gold")
        before.pop("outcomes", None)
        after.pop("outcomes", None)
        base_f2p_fail = before.get("applies") and not before.get("f2p_ok")
        ok = bool(base_f2p_fail and after.get("resolved"))
        return {"ok": ok, "baseline": before, "gold": after, "unmatched_ids": self.unmatched,
                "python": self.python,
                "why": "" if ok else "environment does not reproduce the task (F2P must fail before, all pass with gold)"}

    # -- EMI workspaces ------------------------------------------------------
    def workspace(self, emi: str, cond: str) -> dict:
        root = self.root / "emi" / cond
        if root.exists():
            shutil.rmtree(root)
        repo = root / "repo"
        shutil.copytree(self.src, repo, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        shutil.rmtree(repo / ".git")
        git(repo, "init", "-q", "-b", "main")
        gi = repo / ".gitignore"
        gi.write_text((gi.read_text() if gi.exists() else "") + IGNORED)
        if not (repo / ".venv").exists():
            os.symlink(self.venv, repo / ".venv")
        laid: list[str] = []
        if cond == "spec_laws":
            spec = self.tree("spec", [self.task["test_patch"]])
            if spec is None:
                raise RuntimeError("the hidden test patch does not apply")
            laid = lay_laws(repo, spec, touched_files(self.task["test_patch"]))
            if not laid:
                raise RuntimeError("no hidden test file could be laid as a law")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "baseline")
        state = root / "state"
        env = {**{k: v for k, v in os.environ.items() if not k.startswith("EMI_")},
               "XDG_STATE_HOME": str(state), "EMI_HOOK_WARM": "0"}
        init = sh([emi, "init", "--yes"], cwd=repo, env=env)
        cfg_path = repo / ".emi/config.json"
        if not cfg_path.exists():
            raise RuntimeError("emi init: " + init.stdout[-400:] + init.stderr[-400:])
        cfg = json.loads(cfg_path.read_text())
        base_command = list(cfg["tests"]["command"])
        command = base_command
        if cond != "full_suite":
            # the tests the task concerns, as the baseline has them (bounded runtime)
            files = sorted({i.split("::")[0] for i in self.f2p + self.p2p if (repo / i.split("::")[0]).exists()})
            if files:
                command = [*base_command, *files]
        cfg["tests"]["command"] = command
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "Configure EMI")
        timed(command, repo)  # warm-up, discarded
        own = timed(command, repo)
        git(repo, "clean", "-q", "-fdx", "-e", ".venv")
        git(repo, "switch", "-q", "-c", "task")
        t0 = time.monotonic()
        warm = sh([emi, "done", "--warm"], cwd=repo, env=env, timeout=3600)
        laws_dir = repo / ".emi/laws"
        return {"repo": repo, "state": state, "command": command,
                "laws_command": [*base_command, ".emi/laws"] if laws_dir.is_dir() and any(laws_dir.rglob("test*.py")) else None,
                "own": own, "warm_seconds": round(time.monotonic() - t0, 1), "warm_exit": warm.returncode,
                "laws_laid": laid}

    def check(self, emi: str, ws: dict, patch: str, name: str, script: bool) -> tuple[dict, dict | None]:
        repo, state = ws["repo"], ws["state"]
        git(repo, "reset", "-q", "--hard", "main")
        git(repo, "clean", "-q", "-fdx", "-e", ".venv")
        if not apply_patch(repo, patch):
            return {"action": "not_applied"}, None
        st = state.parent / f"state-{name}"
        if st.exists():
            shutil.rmtree(st)
        shutil.copytree(state, st, symlinks=True) if state.exists() else st.mkdir()
        env = {**{k: v for k, v in os.environ.items() if not k.startswith("EMI_")},
               "XDG_STATE_HOME": str(st), "EMI_HOOK_WARM": "0"}
        t0 = time.monotonic()
        try:
            out = sh([emi, "done", "--format", "json"], cwd=repo, env=env, timeout=3600)
            s = receipt.summarize(out.returncode, receipt.parse(out.stdout), out.stderr)
        except subprocess.TimeoutExpired:
            s = {"action": "harness_timeout"}
        s["seconds"] = round(time.monotonic() - t0, 1)
        shutil.rmtree(st, ignore_errors=True)
        gate = script_check(repo, ws["command"], ws["laws_command"]) if script else None
        return s, gate


def ws_summary(ws: dict) -> dict:
    return {k: (str(v) if isinstance(v, Path) else v) for k, v in ws.items() if k not in ("repo", "state")}


def run_instance(inst: Instance, task: dict, emi: str, out: Path) -> None:
    py = inst.venv / "bin" / "python"
    cands = [{"name": "gold", "model": "gold", "target": "True", "patch": task["patch"]}]
    cands += [{"name": f"agent{i}", **a} for i, a in enumerate(inst.attempts)]
    for c in cands:
        c["grade"] = inst.grade(py, c["patch"], c["name"])
    for cond in ("visible", "spec_laws", "full_suite"):
        try:
            ws = inst.workspace(emi, cond)
        except Exception as e:  # recorded, never dropped
            print(f"  ! {inst.id}/{cond}: {e}")
            with open(out / "workspaces.jsonl", "a") as fh:
                fh.write(json.dumps({"instance": inst.id, "condition": cond, "error": str(e)}, sort_keys=True) + "\n")
            continue
        with open(out / "workspaces.jsonl", "a") as fh:
            fh.write(json.dumps({"instance": inst.id, "condition": cond, **ws_summary(ws)}, sort_keys=True) + "\n")
        for c in cands if cond != "full_suite" else cands[:1]:
            s, gate = inst.check(emi, ws, c["patch"], c["name"], script=cond != "full_suite")
            row = {"instance": inst.id, "repo": task["repo"], "condition": cond, "candidate": c["name"],
                   "model": c["model"], "dataset_label": c["target"] == "True",
                   "resolved": c["grade"].get("resolved"), "applies": c["grade"].get("applies"),
                   "touches_tests": any("test" in f for f in touched_files(c["patch"])),
                   "files": touched_files(c["patch"]), "emi": s, "script": gate}
            if c["name"] == "gold" and cond != "full_suite":
                again, _ = inst.check(emi, ws, c["patch"], "gold-again", script=False)
                row["repeat_same_decision"] = again.get("decision_id") == s.get("decision_id")
                row["repeat_action"] = again.get("action")
            with open(out / "results.jsonl", "a") as fh:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
            print(f"    {cond:<10} {c['name']:<7} resolved={c['grade'].get('resolved')!s:<5} "
                  f"(dataset {c['target']}) -> emi {s.get('action')} ({s.get('seconds')}s), "
                  f"script {'accept' if gate and gate['accept'] else ('-' if gate is None else 'reject')}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "run"])
    ap.add_argument("--inputs", type=Path, required=True, help="directory with mixed.json and tasks.json")
    ap.add_argument("--only", nargs="*", help="instance ids to run (default: all in the inputs)")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results-rebench"))
    ap.add_argument("--emi", default="emi")
    ap.add_argument("--uv", default="uv", help="uv, to find the interpreters environment.json names")
    args = ap.parse_args(argv)
    mixed = json.loads((args.inputs / "mixed.json").read_text())
    tasks = json.loads((args.inputs / "tasks.json").read_text())
    envs = json.loads((args.inputs / "environment.json").read_text()) if (args.inputs / "environment.json").exists() else {}
    args.out.mkdir(parents=True, exist_ok=True)
    for iid in sorted(tasks):
        if args.only and iid not in args.only:
            continue
        task = tasks[iid]
        python = "python3"
        if iid in envs.get("python", {}):
            version = envs["python"][iid]["version"]
            python = sh([args.uv, "python", "find", version]).stdout.strip() or f"python{version}"
        packages = envs.get("packages", {}).get(iid, {}).get("install", [])
        inst = Instance(args.work.resolve(), task, choose(mixed.get(iid, [])), python, packages)
        v = inst.prepare()
        print(f"  {iid}: environment {'ok' if v['ok'] else 'REJECTED: ' + v.get('why', '')}")
        with open(args.out / "instances.jsonl", "a") as fh:
            fh.write(json.dumps({"instance": iid, "command": args.command, "valid": v["ok"], "validation": v,
                                 "candidates": [{"model": a["model"], "target": a["target"]} for a in inst.attempts]},
                                sort_keys=True) + "\n")
        if args.command == "run" and v["ok"]:
            run_instance(inst, task, args.emi, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
