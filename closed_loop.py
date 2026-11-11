"""Closed-loop track: a real agent, with and without the EMI hook.

This is the controlled experiment the EMI README says has not been run.
It reuses the discrimination tasks (each has a prompt, a baseline project,
laws and a hidden oracle) and runs Claude Code headless on each:

  arm A  no EMI. A Stop hook only snapshots the tree and lets the agent stop.
  arm B  `emi hook install --harness claude-code`, plus the same snapshot hook.

Every stop attempt is snapshotted, so each of EMI's interventions is labelled
automatically against the hidden oracle instead of by hand:

  useful   EMI blocked a stop on a tree the oracle says is incorrect
  wrong    EMI blocked a stop on a tree the oracle says is correct
  missed   EMI let the agent stop on an incorrect tree

Per run: final oracle verdict, whether the agent claimed done, number of stop
attempts and repair rounds, tokens and cost (from Claude Code's JSON output),
wall time. Pre-registered comparisons (B vs A, paired by task and seed):

  H1 false completion rate (claimed done, oracle fails) is lower in B
  H2 solve rate (oracle passes at the end) is not lower in B (margin 5 points)
  H3 median token overhead of B over A is below 30%

NOT EXECUTED in the session that wrote it: it calls a paid model and needs a
logged-in `claude` CLI. Run it where that is intended:

  python -m tracks.closed_loop --emi $(which emi) --work W --out OUT \\
      --seeds 3 --condition laws --max-turns 40
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

SNAPSHOT = r'''#!/usr/bin/env python3
"""Stop hook: copy the tree at this stop attempt, then allow the stop."""
import json, os, shutil, subprocess, sys, time
repo = os.getcwd()
dest = os.path.join(os.environ["EVAL_SNAPSHOTS"], "%03d" % len(os.listdir(os.environ["EVAL_SNAPSHOTS"])))
files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=repo,
                       capture_output=True, text=True).stdout.split()
for f in files:
    os.makedirs(os.path.dirname(os.path.join(dest, f)) or dest, exist_ok=True)
    shutil.copy2(os.path.join(repo, f), os.path.join(dest, f))
with open(os.path.join(dest, ".stop.json"), "w") as fh:
    fh.write(json.dumps({"t": time.time(), "hook_input": sys.stdin.read()[:4000]}))
sys.exit(0)
'''


def settings_with_snapshot(repo: Path, script: Path) -> None:
    path = repo / ".claude" / "settings.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    stop = data.setdefault("hooks", {}).setdefault("Stop", [])
    stop.insert(0, {"hooks": [{"type": "command", "command": f"python3 {script}"}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def run_one(task, arm: str, seed: int, args) -> dict:
    cond = CONDITIONS[args.condition]
    root = args.work / "closed_loop" / f"{task.id}__{arm}__{seed}"
    venv = ensure_venv(args.work / "venv", task.pip)
    ws = Workspace(root, args.emi, venv)
    ws.build(task.files, task.laws if cond.laws else None, cond.config, setup=task.setup)
    snaps = root / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    script = root / "snapshot.py"
    script.write_text(SNAPSHOT)
    env = {**os.environ, "XDG_STATE_HOME": str(root / "state"), "EVAL_SNAPSHOTS": str(snaps)}
    if arm == "B":
        subprocess.run([args.emi, "hook", "install", "--harness", "claude-code"], cwd=ws.repo, env=env, check=True)
    settings_with_snapshot(ws.repo, script)
    t0 = time.monotonic()
    proc = subprocess.run(
        ["claude", "-p", task.prompt, "--output-format", "json", "--max-turns", str(args.max_turns),
         "--permission-mode", "acceptEdits", "--allowedTools", "Bash,Edit,Write,Read,Glob,Grep"],
        cwd=ws.repo, env=env, capture_output=True, text=True, timeout=args.timeout)
    wall = time.monotonic() - t0
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"raw": proc.stdout[-2000:]}
    python = venv / "bin" / "python"
    attempts = []
    for snap in sorted(p for p in snaps.iterdir() if p.is_dir()):
        verdict = gates.run_oracle(snap, python, task.oracle, task.python_path)
        attempts.append({"snapshot": snap.name, "correct": verdict["correct"]})
    final = gates.run_oracle(ws.repo, python, task.oracle, task.python_path)
    journal = None
    if arm == "B":
        j = subprocess.run([args.emi, "journal", "report"], cwd=ws.repo, env=env, capture_output=True, text=True)
        journal = j.stdout[-4000:]
    # Stop attempts the hook blocked are followed by another attempt; the last one is allowed.
    labels = []
    if arm == "B":
        for a in attempts[:-1]:
            labels.append("useful" if not a["correct"] else "wrong")
        if attempts and not attempts[-1]["correct"]:
            labels.append("missed")
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    return {"task": task.id, "arm": arm, "seed": seed, "condition": args.condition,
            "claimed_done": bool(attempts), "final_correct": final["correct"],
            "false_completion": bool(attempts) and not final["correct"],
            "stop_attempts": len(attempts), "interventions": labels,
            "tokens_in": usage.get("input_tokens"), "tokens_out": usage.get("output_tokens"),
            "cost_usd": result.get("total_cost_usd") if isinstance(result, dict) else None,
            "num_turns": result.get("num_turns") if isinstance(result, dict) else None,
            "wall_s": round(wall, 1), "journal": journal}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emi", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results-closed-loop"))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--condition", default="laws", choices=["tests_only", "strict", "laws", "laws_adequacy"])
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if not shutil.which("claude"):
        raise SystemExit("needs the `claude` CLI, logged in")
    args.work = args.work.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in DISCRIMINATION if t.kind != "refactor" and (not args.only or t.id in args.only)]
    for seed in range(args.seeds):
        for task in tasks:
            for arm in ("A", "B") if seed % 2 == 0 else ("B", "A"):  # alternate order against drift
                row = run_one(task, arm, seed, args)
                with open(args.out / "runs.jsonl", "a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"{task.id} arm={arm} seed={seed} final_correct={row['final_correct']} "
                      f"stops={row['stop_attempts']} interventions={row['interventions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
