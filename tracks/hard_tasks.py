"""Harder tasks for trial E: recent real issues from the SWE-rebench leaderboard.

The pilot's synthetic tasks were solved by an unaided agent every time, so
they cannot compare setups. These come from nebius/SWE-rebench-leaderboard:
recent GitHub issues (2025-2026, after most training data, which lowers the
chance the agent has seen the fix) that frontier models are scored on each
month. Each has the developers' fix, hidden tests (FAIL_TO_PASS,
PASS_TO_PASS) and its own install recipe.

Selection rule, fixed before any agent run (`select`):
  1. tested with pytest, installed with pip only (no system packages, no
     conda, no pre-install steps);
  2. the fix touches 1 to 4 source files (not tests, not docs); the hidden
     tests touch 1 to 3 test files;
  3. not an `_interface` variant (those hand the agent an interface the
     problem text does not include);
  4. newest first, one task per repository, the first N.

`prepare` clones each at its base commit, builds a virtualenv with the
task's Python and install recipe (plus pytest, coverage and Hypothesis,
which EMI's runs need), and keeps a task only if its hidden tests fail
before the fix and all pass with it. Rejected tasks are recorded with why.

usage:
  python -m tracks.hard_tasks select --parquet LEADERBOARD.parquet --out inputs-hard --n 16
  python -m tracks.hard_tasks prepare --inputs inputs-hard --work W --uv UV
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from emi_evals.workspace import git  # noqa: E402
from tracks.rebench import Instance, sh, touched_files  # noqa: E402

DOC = re.compile(r"(^|/)(docs?|doc|changelog|changes|news)(/|\.|$)|\.(md|rst|txt)$", re.I)


def is_test_path(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    return "test" in path.split("/")[0].lower() or base.startswith("test_") or base.endswith("_test.py") \
        or "/tests/" in path or "/test/" in path


def config(task: dict) -> dict:
    ic = task["install_config"]
    return ic if isinstance(ic, dict) else json.loads(ic or "{}")


def pip_only(install: str) -> bool:
    steps = [s.strip() for s in (install or "").split("&&") if s.strip()]
    return bool(steps) and all(s.startswith(("pip install", "python -m pip install")) for s in steps)


def eligible(task: dict) -> str:
    """'' when the task meets the rule, else the first reason it does not."""
    ic = config(task)
    source = [f for f in touched_files(task["patch"]) if not is_test_path(f) and not DOC.search(f)]
    tests = [f for f in touched_files(task["test_patch"]) if f.endswith(".py")]
    checks = [
        (ic.get("log_parser") == "parse_log_pytest" and str(ic.get("test_cmd", "")).startswith("pytest"),
         "not plain pytest"),
        (not ic.get("pre_install") and not ic.get("env_yml_path") and not ic.get("docker_specs"),
         "needs system packages or conda"),
        (str(ic.get("packages") or "") in ("", "requirements.txt"), "conda packages"),
        (pip_only(ic.get("install", "")), "install is not pip only"),
        (1 <= len(source) <= 4, f"fix touches {len(source)} source files"),
        (1 <= len(tests) <= 3, f"hidden tests touch {len(tests)} test files"),
        (bool(task["FAIL_TO_PASS"]), "no FAIL_TO_PASS"),
        (not task.get("interface") and not task["instance_id"].endswith("_interface"), "interface variant"),
    ]
    return next((why for ok, why in checks if not ok), "")


def select(parquet: Path, out: Path, n: int) -> int:
    import pyarrow.parquet as pq
    rows = pq.read_table(parquet).to_pylist()
    rows.sort(key=lambda r: (r["created_at"], r["instance_id"]), reverse=True)
    chosen, seen_repos, reasons = {}, set(), {}
    for r in rows:
        why = eligible(r) or ("repository already chosen" if r["repo"] in seen_repos else "")
        reasons[why or "eligible"] = reasons.get(why or "eligible", 0) + 1
        if why or len(chosen) >= n:
            continue
        seen_repos.add(r["repo"])
        row = {k: v for k, v in r.items() if k not in ("harbor_cpus", "harbor_memory", "harbor_storage",
                                                        "harbor_verifier_timeout_sec")}
        row["install_config"] = config(r)
        row["FAIL_TO_PASS"], row["PASS_TO_PASS"] = list(r["FAIL_TO_PASS"]), list(r["PASS_TO_PASS"] or [])
        chosen[r["instance_id"]] = row
    out.mkdir(parents=True, exist_ok=True)
    (out / "tasks.json").write_text(json.dumps(chosen, indent=1, sort_keys=True, default=str) + "\n")
    (out / "choice.json").write_text(json.dumps({
        "source": "nebius/SWE-rebench-leaderboard, split test",
        "rule": __doc__.split("Selection rule")[1].split("`prepare`")[0].strip(),
        "pool": len(rows), "reasons": reasons,
        "chosen": [{"instance_id": k, "repo": v["repo"], "created_at": str(v["created_at"])} for k, v in chosen.items()],
    }, indent=1) + "\n")
    for k, v in chosen.items():
        print(f"  {v['created_at']}  {k}")
    print(f"{len(chosen)} chosen; reasons over the pool: {reasons}")
    return 0


class HardInstance(Instance):
    """A leaderboard task: its own Python and install recipe."""

    def __init__(self, work: Path, task: dict, uv: str):
        super().__init__(work, task, [], python="python3")
        self.ic, self.uv = task["install_config"], uv
        self.root = work / "hard" / self.id
        self.src, self.venv = self.root / "src", self.root / "venv"

    def prepare(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.src / ".git").exists():
            self.src.mkdir(parents=True, exist_ok=True)
            git(self.src, "init", "-q")
            got = sh(["git", "fetch", "-q", "--depth", "1", f"https://github.com/{self.task['repo']}",
                      self.task["base_commit"]], cwd=self.src, timeout=1200)
            if got.returncode != 0:
                return {"ok": False, "why": "fetch: " + got.stderr[-300:]}
            git(self.src, "checkout", "-q", "FETCH_HEAD")
        py = self.venv / "bin" / "python"
        if not (self.venv / ".ready").exists():
            version = str(self.ic.get("python") or "3.11")
            sh([self.uv, "python", "install", version], timeout=600)
            interp = sh([self.uv, "python", "find", version]).stdout.strip()
            if not interp:
                return {"ok": False, "why": f"no Python {version}"}
            sh([interp, "-m", "venv", "--clear", str(self.venv)])
            steps = [[str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                     [str(py), "-m", "pip", "install", "-q", "pytest", "coverage>=7.9,<8", "hypothesis>=6,<7",
                      *(self.ic.get("pip_packages") or [])]]
            for req in self.ic.get("reqs_path") or []:
                steps.append([str(py), "-m", "pip", "install", "-q", "-r", req])
            for step in str(self.ic.get("install") or "").split("&&"):
                words = shlex.split(step.strip())
                if words[:2] == ["python", "-m"]:
                    words = words[2:]
                if words[:2] == ["pip", "install"]:
                    steps.append([str(py), "-m", "pip", "install", "-q", *[w for w in words[2:] if w != "--quiet"]])
            for cmd in steps:
                done = sh(cmd, cwd=self.src, timeout=1800)
                if done.returncode != 0:
                    return {"ok": False, "why": f"{' '.join(cmd[3:6])}...: " + done.stderr[-300:]}
            (self.venv / ".ready").write_text("ok\n")
        return self.validate(py)


def prepare(inputs: Path, work: Path, uv: str, only: list[str] | None) -> int:
    tasks = json.loads((inputs / "tasks.json").read_text())
    out = inputs / "environments.jsonl"
    for iid, task in sorted(tasks.items()):
        if only and iid not in only:
            continue
        inst = HardInstance(work.resolve(), task, uv)
        try:
            v = inst.prepare()
        except Exception as e:  # recorded, never dropped
            v = {"ok": False, "why": f"{type(e).__name__}: {e}"[:400]}
        print(f"  {iid}: {'ok' if v['ok'] else 'REJECTED: ' + v.get('why', '')[:200]}", flush=True)
        with open(out, "a") as fh:
            fh.write(json.dumps({"instance": iid, "valid": v["ok"], "validation": v}, sort_keys=True, default=str) + "\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["select", "prepare"])
    ap.add_argument("--parquet", type=Path)
    ap.add_argument("--inputs", type=Path, default=Path("inputs-hard"))
    ap.add_argument("--out", type=Path, default=Path("inputs-hard"))
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--uv", default="uv")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if args.command == "select":
        return select(args.parquet, args.out, args.n)
    return prepare(args.inputs, args.work, args.uv, args.only)


if __name__ == "__main__":
    sys.exit(main())
