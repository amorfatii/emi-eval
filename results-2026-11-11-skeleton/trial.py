"""Drafted-skeleton trial: three real tasks from trial C, two arms, two runs each.

  draft      one Drafter per task: bug report + code at the base commit only,
             read-only tools, writes SKELETON.md. Never sees the fix, the
             hidden tests or any agent attempt.
  implement  arm a = bug report only; arm b = bug report + the drafted
             skeleton. 2 runs per arm per task (12 in all).
  grade      the trial C grader (tracks/rebench.py Instance.grade): hidden test
             patch applied, FAIL_TO_PASS + PASS_TO_PASS must all pass.

Every agent is the headless `claude` CLI (Opus 5.5, effort medium) inside
bubblewrap: the eval repo, /tmp (other workspaces, skeletons, scratch) and
the Claude transcript folder are hidden; it sees its own workspace copy and the
project's virtualenv. Web tools are disallowed; Bash commands are logged and
audited afterwards for network use.

Usage (from the repo root, environments already prepared with
`python -m tracks.rebench prepare --work W ...`):
  python results-2026-11-11-skeleton/trial.py draft --work W
  python results-2026-11-11-skeleton/trial.py implement --work W [--only ID] [--arm a|b] [--run 1|2]
  python results-2026-11-11-skeleton/trial.py grade --work W
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from tracks import rebench  # noqa: E402

TASKS = ["benmoran56__esper-81", "serge-sans-paille__gast-50", "package-url__packageurl-python-29"]
MODEL, EFFORT = "claude-opus-5-5", "medium"
WS = Path("/tmp/skelws")
BUDGET_USD = "8"

DRAFT_PROMPT = """You are the Drafter. A person owns a "skeleton" of this program: its data types,
function names with inputs and outputs and a one-line description, and which part
may call which. Your job: read the bug report below and the code in this directory,
and write the SKELETON CHANGE that a fix should make. Do NOT write the fix itself.

Write it to the file SKELETON.md in this directory, in exactly this form:

# Skeleton change
- CHANGE `path/to/file.py::Qualified.name(arg, arg2=default) -> ReturnType` — one-line description of what it does after the change
- ADD `path/to/file.py::Qualified.name(args) -> ReturnType` — one-line description
- REMOVE `path/to/file.py::Qualified.name` — why
- RULE `path/to/file.py::A` may not call `path/to/file.py::B` — why
- TYPE `path/to/file.py::Name` — a data type or table entry that changes, one line

Rules: keep it coarse. Name only the functions, methods, types or table entries
whose interface or responsibility changes; give inputs and outputs, never bodies,
never step-by-step logic. Usually 1 to 6 lines. Add a RULE line only if the
report implies one. Signatures: Python style; use the same file paths and
qualified names as the code (ClassName.method). Then stop.

Bug report:
---
{report}
---
"""

IMPL_PROMPT = """Fix the issue described in the bug report below, in the repository in the
current directory. Python and the project's dependencies are in .venv
(run tests with `.venv/bin/python -m pytest`). Do not use the network.
When the fix is done, stop.

Bug report:
---
{report}
---
"""

SKEL_ADDENDUM = """
The person who owns this code has drafted a skeleton of the change: the
functions and types the fix should add or change, with their inputs, outputs
and one-line descriptions, and any calls that are not allowed. Keep to it: do
not add public functions, methods or types it does not name, and do not make
a call it forbids.

{skeleton}
"""


def instance(work: Path, iid: str) -> rebench.Instance:
    tasks = json.loads((ROOT / "inputs-rebench/tasks.json").read_text())
    envs = json.loads((ROOT / "inputs-rebench/environment.json").read_text())
    python = "python3"
    if iid in envs.get("python", {}):
        python = rebench.sh(["uv", "python", "find", envs["python"][iid]["version"]]).stdout.strip()
    pk = envs.get("packages", {}).get(iid, {}).get("install", [])
    return rebench.Instance(work.resolve(), tasks[iid], [], python, pk)


def make_workspace(inst: rebench.Instance, name: str) -> Path:
    ws = WS / name
    if ws.exists():
        shutil.rmtree(ws)
    shutil.copytree(inst.src, ws, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info"))
    os.symlink(inst.venv, ws / ".venv")
    rebench.git(ws, "init", "-q", "-b", "main")
    (ws / ".git/info/exclude").write_text(".venv\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\n.hypothesis/\n")
    rebench.git(ws, "add", "-A")
    rebench.git(ws, "commit", "-q", "-m", "base")
    return ws


def agent(ws: Path, venv: Path, prompt: str, tools: list[str], log: Path) -> dict:
    hidden = ["/home/user/emi-eval", "/tmp", str(Path.home() / ".claude/projects")]
    cmd = ["bwrap", "--dev-bind", "/", "/"]
    for h in hidden:
        cmd += ["--tmpfs", h]
    cmd += ["--bind", str(ws), str(ws), "--ro-bind", str(venv), str(venv), "--chdir", str(ws)]
    cmd += ["claude", "-p", prompt, "--model", MODEL, "--effort", EFFORT,
            "--output-format", "stream-json", "--verbose", "--max-budget-usd", BUDGET_USD,
            "--allowedTools", *tools, "--disallowedTools", "WebFetch", "WebSearch", "Agent", "--"]
    roots = [str(ws / "src")] if (ws / "src").is_dir() else []
    env = rebench.pinned_env({"PYTHONPATH": os.pathsep.join([*roots, str(ws)])})
    t0 = time.monotonic()
    out = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, env=env, timeout=3600)
    secs = round(time.monotonic() - t0, 1)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(out.stdout)
    result = {}
    for line in out.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            result = ev
    return {"seconds": secs, "exit": out.returncode, "cost_usd": result.get("total_cost_usd"),
            "turns": result.get("num_turns"), "terminal": result.get("terminal_reason") or result.get("subtype"),
            "stderr": out.stderr[-500:]}


def diff_of(ws: Path) -> str:
    rebench.git(ws, "add", "-A")
    return rebench.sh(["git", "diff", "--cached", "main", "--", ".", ":(exclude)SKELETON.md"], cwd=ws).stdout


def source_only(patch: str) -> str:
    parts = re.split(r"(?m)^(?=diff --git )", patch)
    keep = [p for p in parts if p.strip() and not rebench.is_test_file(
        re.match(r"diff --git a/(\S+)", p).group(1)) and "/tests/" not in re.match(r"diff --git a/(\S+)", p).group(1)]
    return "".join(keep)


def cmd_draft(work: Path) -> None:
    for iid in TASKS:
        inst = instance(work, iid)
        ws = make_workspace(inst, f"draft-{iid}")
        r = agent(ws, inst.venv, DRAFT_PROMPT.format(report=inst.task["problem_statement"]),
                  ["Read", "Glob", "Grep", "Write"], HERE / "logs" / f"draft-{iid}.jsonl")
        skel = ws / "SKELETON.md"
        (HERE / "skeletons").mkdir(exist_ok=True)
        if skel.exists():
            shutil.copy2(skel, HERE / "skeletons" / f"{iid}.md")
        other = diff_of(ws)
        r.update({"task": iid, "role": "drafter", "wrote_skeleton": skel.exists(), "touched_code": bool(other.strip())})
        with open(HERE / "drafts.jsonl", "a") as fh:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
        print(iid, r["seconds"], r["cost_usd"], skel.exists())


def cmd_implement(work: Path, only: list[str] | None, arms: list[str], runs: list[int]) -> None:
    for iid in TASKS:
        if only and iid not in only:
            continue
        inst = instance(work, iid)
        skeleton = (HERE / "skeletons" / f"{iid}.md").read_text()
        for run in runs:
            for arm in arms:
                name = f"{iid}-{arm}{run}"
                prompt = IMPL_PROMPT.format(report=inst.task["problem_statement"])
                if arm == "b":
                    prompt += SKEL_ADDENDUM.format(skeleton=skeleton)
                ws = make_workspace(inst, name)
                r = agent(ws, inst.venv, prompt, ["Read", "Glob", "Grep", "Edit", "Write", "Bash"],
                          HERE / "logs" / f"{name}.jsonl")
                patch = diff_of(ws)
                (HERE / "patches").mkdir(exist_ok=True)
                (HERE / "patches" / f"{name}.diff").write_text(patch)
                r.update({"task": iid, "arm": arm, "run": run, "name": name, "patch_lines": len(patch.splitlines())})
                with open(HERE / "runs.jsonl", "a") as fh:
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
                print(name, r["seconds"], r["cost_usd"], r["patch_lines"], flush=True)


def cmd_grade(work: Path) -> None:
    out = HERE / "grades.jsonl"
    out.unlink(missing_ok=True)
    for iid in TASKS:
        inst = instance(work, iid)
        v = inst.prepare()  # re-validates and records malformed dataset ids, as trial C did
        py = inst.venv / "bin/python"
        for p in sorted((HERE / "patches").glob(f"{iid}-*.diff")):
            patch = p.read_text()
            g = inst.grade(py, patch, "skel-" + p.stem) if patch.strip() else {"applies": False}
            graded = "full"
            if not g.get("applies") and source_only(patch).strip():
                g = inst.grade(py, source_only(patch), "skel-" + p.stem)
                graded = "source_only"
            g.pop("outcomes", None)
            row = {"name": p.stem, "task": iid, "graded": graded, "env_ok": v["ok"], **g}
            with open(out, "a") as fh:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
            print(p.stem, graded, g.get("resolved"), g.get("failed"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["draft", "implement", "grade"])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--arm", nargs="*", default=["a", "b"])
    ap.add_argument("--run", nargs="*", type=int, default=[1, 2])
    a = ap.parse_args()
    if a.command == "draft":
        cmd_draft(a.work)
    elif a.command == "implement":
        cmd_implement(a.work, a.only, a.arm, a.run)
    else:
        cmd_grade(a.work)


if __name__ == "__main__":
    main()
