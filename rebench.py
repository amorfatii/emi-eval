"""Real-world track: real repositories, real issues, real agent patches.

Tasks come from nebius/SWE-bench-extra (real GitHub issues with the fix and
its hidden tests: FAIL_TO_PASS, PASS_TO_PASS). Candidates are the gold
patch and patches real agents produced for the same task
(nebius/SWE-agent-trajectories), chosen so each task has both resolved and
unresolved attempts.

Ground truth is re-graded here, in the same environment EMI runs in: the
task's hidden test patch is applied to the candidate and FAIL_TO_PASS plus
PASS_TO_PASS are run; resolved means all pass. Agreement with the dataset's
own label is reported, so environment drift is visible rather than hidden.

Conditions:
  visible     what a project has before the task: its own tests, EMI defaults.
  spec_laws   the person wrote the acceptance tests first: the test files the
              hidden test patch touches are committed as laws (FAIL_TO_PASS
              tests become open laws, PASS_TO_PASS ones laws that hold).
              This is the ceiling: EMI given the grader's own spec.

Usage:
  python -m tracks.rebench prepare --shard traj0.parquet --ids ID... --work W
  python -m tracks.rebench run --emi PATH --work W --out OUT
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from emi_evals import receipt  # noqa: E402
from emi_evals.workspace import GIT_ID, git  # noqa: E402

DEFAULT_IDS = [
    "tehmaze__ansi", "johnsyweb__python_sparse_list", "konradhalas__dacite",
    "Melevir__cognitive_complexity", "package-url__packageurl-python", "benmoran56__esper",
    "andialbrecht__sqlparse", "serge-sans-paille__gast",
]
PER_LABEL = 2  # agent patches kept per label (resolved / unresolved) per task


def _get(url: str, tries: int = 3) -> dict:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3)
    raise RuntimeError("unreachable")


def fetch_task(instance_id: str) -> dict:
    where = urllib.parse.quote(f"\"instance_id\"='{instance_id}'")
    url = (f"https://datasets-server.huggingface.co/filter?dataset=nebius/SWE-bench-extra"
           f"&config=default&split=train&where={where}")
    rows = _get(url)["rows"]
    if not rows:
        raise LookupError(instance_id)
    return rows[0]["row"]


def _ids(field) -> list[str]:
    return list(field) if isinstance(field, list) else ast.literal_eval(field)


def sh(cmd, cwd=None, timeout=900, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def pytest_ids(py: Path, repo: Path, ids: list[str], timeout=900) -> dict[str, str]:
    """Outcome per test id, via a junit report (names without exact ids fall back to files)."""
    report = repo.parent / (repo.name + "-junit.xml")
    files = sorted({i.split("::")[0] for i in ids})
    # import the tree under test, never the checkout an editable install points at
    roots = [str(repo / "src")] if (repo / "src").is_dir() else []
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": os.pathsep.join([*roots, str(repo)])}
    sh([str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", f"--junitxml={report}", *files],
       cwd=repo, timeout=timeout, env=env)
    out: dict[str, str] = {}
    if report.exists():
        import xml.etree.ElementTree as ET
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


def touched_files(patch: str) -> list[str]:
    return sorted(set(re.findall(r"^\+\+\+ b/(\S+)", patch, flags=re.M)))


class Instance:
    def __init__(self, work: Path, task: dict, attempts: list[dict]):
        self.task, self.attempts = task, attempts
        self.id = task["instance_id"]
        self.root = work / "rebench" / self.id
        self.src = self.root / "src"
        self.venv = self.root / "venv"
        self.f2p, self.p2p = _ids(task["FAIL_TO_PASS"]), _ids(task["PASS_TO_PASS"])

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
            sh(["python3", "-m", "venv", "--clear", str(self.venv)])
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
        f2p_ok = all(res[i] == "passed" for i in self.f2p)
        p2p_ok = all(res[i] == "passed" for i in self.p2p)
        return {"applies": True, "resolved": f2p_ok and p2p_ok, "f2p_ok": f2p_ok, "p2p_ok": p2p_ok,
                "failed": [i for i in self.f2p + self.p2p if res[i] != "passed"][:8]}

    def validate(self, py: Path) -> dict:
        before = self.grade(py, None, "validate-base")
        after = self.grade(py, self.task["patch"], "validate-gold")
        base_f2p_fail = before.get("applies") and not before.get("f2p_ok")
        ok = bool(base_f2p_fail and after.get("resolved"))
        return {"ok": ok, "baseline": before, "gold": after,
                "why": "" if ok else "environment does not reproduce the task (F2P must fail before, all pass with gold)"}

    # -- EMI workspaces -------------------------------------------------------
    def workspace(self, emi: str, cond: str) -> tuple[Path, Path]:
        root = self.root / "emi" / cond
        if root.exists():
            shutil.rmtree(root)
        repo = root / "repo"
        shutil.copytree(self.src, repo, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        shutil.rmtree(repo / ".git")
        git(repo, "init", "-q", "-b", "main")
        gi = repo / ".gitignore"
        gi.write_text((gi.read_text() if gi.exists() else "") + "\n.venv\n__pycache__/\n*.egg-info/\n")
        os.symlink(self.venv, repo / ".venv") if not (repo / ".venv").exists() else None
        if cond == "spec_laws":
            t = self.tree("spec", [self.task["test_patch"]])
            laws = repo / ".emi/laws"
            laws.mkdir(parents=True)
            for f in touched_files(self.task["test_patch"]):
                if f.endswith(".py") and os.path.basename(f).startswith("test"):
                    flat = "test_" + f.replace("/", "__").removeprefix("test_")
                    shutil.copy(t / f, laws / os.path.basename(flat))
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
        # the tests the task concerns, as the baseline has them (bounded runtime)
        files = sorted({i.split("::")[0] for i in self.f2p + self.p2p if (repo / i.split("::")[0]).exists()})
        if files:
            cfg["tests"]["command"] = [*cfg["tests"]["command"], *files]
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "Configure EMI")
        git(repo, "switch", "-q", "-c", "task")
        sh([emi, "done", "--warm"], cwd=repo, env=env, timeout=3600)
        return repo, state

    def check(self, emi: str, repo: Path, state: Path, patch: str, name: str) -> dict:
        git(repo, "reset", "-q", "--hard", "main")
        git(repo, "clean", "-q", "-fd")
        if not apply_patch(repo, patch):
            return {"action": "not_applied"}
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
        return s


def choose(attempts: list[dict]) -> list[dict]:
    res = [a for a in attempts if a["target"] == "True"][:PER_LABEL]
    unres = [a for a in attempts if a["target"] == "False"][:PER_LABEL]
    return res + unres


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "run"])
    ap.add_argument("--mixed", type=Path, required=True, help="mixed.json: instance -> agent attempts")
    ap.add_argument("--repos", nargs="*", default=DEFAULT_IDS)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results-rebench"))
    ap.add_argument("--emi", default="emi")
    args = ap.parse_args(argv)
    mixed = json.loads(args.mixed.read_text())
    chosen = {}
    for prefix in args.repos:
        ids = sorted(k for k in mixed if k.rsplit("-", 1)[0] == prefix)
        if ids:
            chosen[ids[0]] = mixed[ids[0]]
    args.out.mkdir(parents=True, exist_ok=True)
    for iid, attempts in chosen.items():
        try:
            task = fetch_task(iid)
        except Exception as e:
            print(f"  ! {iid}: task not found ({e})")
            continue
        inst = Instance(args.work.resolve(), task, choose(attempts))
        v = inst.prepare()
        print(f"  {iid}: environment {'ok' if v['ok'] else 'REJECTED: ' + v.get('why', '')}")
        if args.command == "prepare" or not v["ok"]:
            with open(args.out / "instances.jsonl", "a") as fh:
                fh.write(json.dumps({"instance": iid, "valid": v["ok"], "validation": v}, sort_keys=True) + "\n")
            continue
        py = inst.venv / "bin" / "python"
        cands = [{"name": "gold", "model": "gold", "target": "True", "patch": task["patch"]}]
        cands += [{"name": f"agent{i}", **a} for i, a in enumerate(inst.attempts)]
        for c in cands:
            c["grade"] = inst.grade(py, c["patch"], c["name"])
        for cond in ("visible", "spec_laws"):
            try:
                repo, state = inst.workspace(args.emi, cond)
            except Exception as e:
                print(f"  ! {iid}/{cond}: {e}")
                continue
            for c in cands:
                s = inst.check(args.emi, repo, state, c["patch"], c["name"])
                g = c["grade"]
                row = {"instance": iid, "repo": task["repo"], "condition": cond, "candidate": c["name"],
                       "model": c["model"], "dataset_label": c["target"] == "True",
                       "resolved": g.get("resolved"), "applies": g.get("applies"),
                       "touches_tests": any("test" in f for f in touched_files(c["patch"])),
                       "files": touched_files(c["patch"]), "emi": s}
                with open(args.out / "results.jsonl", "a") as fh:
                    fh.write(json.dumps(row, sort_keys=True) + "\n")
                print(f"    {cond:<10} {c['name']:<7} resolved={g.get('resolved')!s:<5} (dataset {c['target']}) -> "
                      f"{s.get('action')} ({s.get('seconds')}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
