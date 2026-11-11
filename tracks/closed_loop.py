"""Closed-loop track (trial E): a real agent, four ways.

Each task is given to the same agent (Claude Code, headless) under four setups:

  none      no checker: the agent stops when it thinks it is done.
  script    the small script: on each stop it puts back the baseline's test
            files and runner configuration, reruns the tests, and sends the
            agent back with pytest's own failure lines while they fail.
  emi       EMI as it is: `emi hook install`, the project's tests, no laws.
  emi_rules EMI with rules drafted from the task before coding starts
            (`tracks/draft_rules.py`, committed under inputs-closed-loop/),
            laid at the baseline as the person's laws.

The script and EMI both send the agent back at most 3 times (EMI's default
repair_rounds); after that the stop is let through and counted as not
accepted. Every stop attempt is snapshotted and graded by the task's hidden
checks, so each send-back is labelled automatically: useful (the tree was
wrong) or wrong (the tree was already right).

Per run: did the agent end "done" on wrong work with the setup accepting it,
did it end correct, how many times it was sent back, turns, tokens, cost,
wall time. Every run's full transcript is kept, and is searched for any
read of this lab (where the hidden checks live); a run that touched it is
flagged.

Comparisons (paired by task and run):
  emi vs script      wrong "done" at least a third less often, solving no
                     fewer tasks, at most 30% more tokens
  emi_rules vs emi   do drafted rules help a real agent?

usage:
  python -m tracks.closed_loop --emi PATH --work W --out OUT --runs 1 --only t01_slugify ...
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from emi_evals import gates  # noqa: E402
from emi_evals.model import CONDITIONS  # noqa: E402
from emi_evals.workspace import Workspace, ensure_venv, git  # noqa: E402
from suites import DISCRIMINATION  # noqa: E402

LAB = Path(__file__).resolve().parent.parent
SETUPS = ("none", "script", "emi", "emi_rules")
ROUNDS = 3
RULES_FILE = "test_drafted_rules.py"
TOOLS = "Bash,Edit,Write,Read,Glob,Grep"
# what the agent may do without asking: edit files in its task folder, run the
# project's tests, look at git. Any other shell command is refused.
ALLOWED = ("Edit,Write,Read,Glob,Grep,Bash(.venv/bin/python -m pytest:*),"
           "Bash(git status:*),Bash(git diff:*)")
NOTE = ("\n\nThe project's virtualenv is .venv; run its tests with `.venv/bin/python -m pytest`. "
        "When the task is done, stop.")

SNAPSHOT = r'''#!/usr/bin/env python3
"""Stop hook: copy the tree at this stop attempt, then allow the stop."""
import json, os, shutil, subprocess, sys, time
repo = os.getcwd()
snaps = os.environ["EVAL_SNAPSHOTS"]
dest = os.path.join(snaps, "%03d" % len(os.listdir(snaps)))
files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=repo,
                       capture_output=True, text=True).stdout.split("\n")
for f in filter(None, files):
    src = os.path.join(repo, f)
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(os.path.join(dest, f)) or dest, exist_ok=True)
        shutil.copy2(src, os.path.join(dest, f))
os.makedirs(dest, exist_ok=True)
with open(os.path.join(dest, ".stop.json"), "w") as fh:
    fh.write(json.dumps({"t": time.time(), "hook_input": sys.stdin.read()[:4000]}))
sys.exit(0)
'''

SCRIPT = r'''#!/usr/bin/env python3
"""Stop hook, the small script: put back the baseline's tests and runner
configuration, rerun the tests, send the agent back while they fail (at most
ROUNDS times). Each verdict is appended to EVAL_SCRIPT_LOG."""
import json, os, shutil, subprocess, sys, tempfile
RUNNER = {"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", "conftest.py", "sitecustomize.py", "usercustomize.py"}
ROUNDS = %d
repo = os.getcwd()
log = os.environ["EVAL_SCRIPT_LOG"]
past = [json.loads(l) for l in open(log)] if os.path.exists(log) else []
def is_test(rel):
    b = os.path.basename(rel)
    return b.endswith(".py") and (b.startswith("test_") or b.endswith("_test.py") or b == "conftest.py")
with tempfile.TemporaryDirectory() as tmp:
    dest = os.path.join(tmp, "tree")
    shutil.copytree(repo, dest, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__", ".emi", ".venv"))
    os.symlink(os.path.join(repo, ".venv"), os.path.join(dest, ".venv"))
    base = set(subprocess.run(["git", "ls-tree", "-r", "--name-only", "main"], cwd=repo,
                              capture_output=True, text=True).stdout.split("\n")) - {""}
    for rel in base:
        if not rel.startswith((".emi/", ".claude/")) and (is_test(rel) or os.path.basename(rel) in RUNNER):
            blob = subprocess.run(["git", "show", "main:" + rel], cwd=repo, capture_output=True).stdout
            os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
            open(os.path.join(dest, rel), "wb").write(blob)
    for root, _, files in os.walk(dest):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), dest)
            if f in RUNNER and rel not in base and not rel.startswith(".venv"):
                os.unlink(os.path.join(root, f))
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST", "PYTHON"))}
    roots = [os.path.join(dest, "src")] if os.path.isdir(os.path.join(dest, "src")) else []
    env.update({"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join(roots + [dest])})
    args = json.loads(os.environ.get("EVAL_TEST_ARGS", '["-q"]'))
    out = subprocess.run([os.path.join(dest, ".venv/bin/python"), "-m", "pytest", "-p", "no:cacheprovider", *args],
                         cwd=dest, env=env, capture_output=True, text=True, timeout=900)
ok = out.returncode == 0
blocks = sum(1 for p in past if p["blocked"])
block = not ok and blocks < ROUNDS
with open(log, "a") as fh:
    fh.write(json.dumps({"passed": ok, "blocked": block, "exit": out.returncode}) + "\n")
if block:
    tail = "\n".join(out.stdout.strip().splitlines()[-25:])
    print(json.dumps({"decision": "block", "reason": "The tests fail (the original test files, as they were before "
                      "your change, were run):\n" + tail}))
sys.exit(0)
''' % ROUNDS


def hooks_settings(repo: Path, root: Path, setup: str, emi: str, env: dict) -> None:
    """The setup's Stop hooks, committed at the baseline so they are not part of the change."""
    if setup in ("emi", "emi_rules"):
        subprocess.run([emi, "hook", "install", "--harness", "claude-code"], cwd=repo, env=env, check=True,
                       capture_output=True)
    path = repo / ".claude" / "settings.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    stop = data.setdefault("hooks", {}).setdefault("Stop", [])
    snap = root / "snapshot.py"
    snap.write_text(SNAPSHOT)
    stop.insert(0, {"hooks": [{"type": "command", "command": f"python3 {snap}"}]})
    if setup == "script":
        script = root / "script.py"
        script.write_text(SCRIPT)
        stop.append({"hooks": [{"type": "command", "command": f"python3 {script}", "timeout": 600}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    git(repo, "switch", "-q", "main")
    git(repo, "add", "-A")
    # a project may ignore .claude/; the hooks are committed all the same
    git(repo, "add", "-f", ".claude/settings.json")
    git(repo, "commit", "-q", "--allow-empty", "-m", "Agent harness hooks")
    git(repo, "switch", "-q", "task")
    git(repo, "reset", "-q", "--hard", "main")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def emi_checks(state: Path) -> list[dict]:
    rows = []
    for j in sorted(state.rglob("journal.jsonl")):
        rows += [r for r in read_jsonl(j) if r.get("kind") == "check"]
    return rows


def transcript_result(lines: list[str]) -> tuple[dict, list[dict]]:
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    return result, events


def touched_lab(events: list[dict]) -> bool:
    """Whether any tool call names this lab's directory (where the hidden checks live)."""
    marker = str(LAB)
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in (e.get("message") or {}).get("content") or []:
            if block.get("type") == "tool_use" and marker in json.dumps(block.get("input")):
                return True
    return False


class Synthetic:
    """A discrimination task: a small project, plain-python hidden checks."""

    def __init__(self, task):
        self.task, self.id, self.prompt = task, task.id, task.prompt + NOTE
        self.test_args = ["-q"]

    def build(self, root: Path, emi: str, laws: dict | None, work: Path) -> Path:
        self.venv = ensure_venv(work / "venv", self.task.pip)
        ws = Workspace(root, emi, self.venv)
        ws.build(self.task.files, laws, CONDITIONS["tests_only"].config, setup=self.task.setup)
        return ws.repo

    def env(self, repo: Path) -> dict:
        return {}

    def grade(self, tree: Path) -> dict:
        return gates.run_oracle(tree, self.venv / "bin" / "python", self.task.oracle, self.task.python_path)


def run_one(task, setup: str, run: int, args) -> dict:
    root = args.work / "closed_loop" / f"{task.id}__{setup}__{run}"
    laws = None
    if setup == "emi_rules":
        rules = args.drafted / task.id / RULES_FILE
        if not rules.exists():
            raise SystemExit(f"{task.id}: no drafted rules; run tracks.draft_rules first")
        laws = {RULES_FILE: rules.read_text()}
    repo = task.build(root, args.emi, laws, args.work)
    snaps, state = root / "snapshots", root / "state"
    snaps.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("EMI_") and k != "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD"}
    env.update({"XDG_STATE_HOME": str(state), "EVAL_SNAPSHOTS": str(snaps),
                "EVAL_SCRIPT_LOG": str(root / "script.jsonl"), "EMI_HOOK_WARM": "0",
                "EVAL_TEST_ARGS": json.dumps(task.test_args), **task.env(repo)})
    hooks_settings(repo, root, setup, args.emi, env)
    cmd = ["claude", "-p", task.prompt, "--output-format", "stream-json", "--verbose",
           "--model", args.model, "--max-turns", str(args.max_turns), "--max-budget-usd", str(args.budget),
           "--permission-mode", "dontAsk", "--tools", TOOLS, "--allowedTools", ALLOWED,
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--disable-slash-commands", "--no-chrome", "--no-session-persistence"]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=args.timeout)
        lines, timed_out = proc.stdout.splitlines(), False
    except subprocess.TimeoutExpired as e:
        lines, timed_out = (e.stdout or b"").decode(errors="replace").splitlines(), True
    wall = time.monotonic() - t0
    (root / "transcript.jsonl").write_text("\n".join(lines) + "\n")
    result, events = transcript_result(lines)
    stops = [task.grade(snap)["correct"] for snap in sorted(p for p in snaps.iterdir() if p.is_dir())]
    final = task.grade(repo)
    # what the setup's checker said at each stop
    if setup == "script":
        verdicts = read_jsonl(root / "script.jsonl")
        blocked = [v["blocked"] for v in verdicts]
        accepted = bool(verdicts) and verdicts[-1]["passed"]
        last_action = "pass" if accepted else ("fail" if verdicts else None)
    elif setup in ("emi", "emi_rules"):
        checks = emi_checks(state)
        blocked = [c.get("reaction") == "block" for c in checks]
        last_action = checks[-1].get("action") if checks else None
        accepted = last_action == "stop"
    else:
        blocked, last_action = [False] * len(stops), "none"
        accepted = bool(stops)
    sent_back = sum(blocked)
    labels = []
    for i, was_blocked in enumerate(blocked):
        if was_blocked and i < len(stops):
            labels.append("useful" if not stops[i] else "wrong")
    usage = result.get("usage") or {}
    return {"task": task.id, "setup": setup, "run": run, "model": args.model,
            "models_used": sorted((result.get("modelUsage") or {}).keys()),
            "final_correct": final["correct"], "oracle_failed": sorted(final["failed"])[:6],
            "stopped": bool(stops), "accepted": accepted, "last_checker_action": last_action,
            "wrong_done": accepted and not final["correct"],
            "sent_back": sent_back, "send_backs": labels, "stop_attempts": len(stops),
            "stops_correct": stops,
            "turns": result.get("num_turns"), "cost_usd": result.get("total_cost_usd"),
            "tokens_in": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
                         + (usage.get("cache_creation_input_tokens") or 0),
            "tokens_out": usage.get("output_tokens"), "terminal": result.get("subtype") or result.get("terminal_reason"),
            "timed_out": timed_out, "touched_lab": touched_lab(events), "wall_s": round(wall, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emi", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results-closed-loop"))
    ap.add_argument("--drafted", type=Path, default=Path("inputs-closed-loop/drafted"))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--setups", nargs="*", default=list(SETUPS), choices=SETUPS)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--budget", type=float, default=3.0, help="per run, in USD")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--hard", type=Path, help="inputs-hard: run its validated real-project tasks instead")
    args = ap.parse_args(argv)
    if not shutil.which("claude"):
        raise SystemExit("needs the `claude` CLI, logged in")
    args.work = args.work.resolve()
    args.drafted = args.drafted.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.hard:
        from tracks.real_tasks import load
        tasks = [t for t in load(args.hard, args.work) if not args.only or t.id in args.only]
    else:
        tasks = [Synthetic(t) for t in DISCRIMINATION
                 if t.kind != "refactor" and (not args.only or t.id in args.only)]
    for run in range(args.runs):
        for task in tasks:
            # rotate the setup order per task and run, against drift in the model service
            k = (run + tasks.index(task)) % len(args.setups)
            for setup in args.setups[k:] + args.setups[:k]:
                row = run_one(task, setup, run, args)
                with open(args.out / "runs.jsonl", "a") as fh:
                    fh.write(json.dumps(row, sort_keys=True) + "\n")
                print(f"{task.id:<22} {setup:<9} run={run} correct={row['final_correct']!s:<5} "
                      f"accepted={row['accepted']!s:<5} sent_back={row['sent_back']} ${row['cost_usd']} "
                      f"{row['wall_s']}s{' LAB' if row['touched_lab'] else ''}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
