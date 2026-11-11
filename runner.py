"""Run tasks × conditions × candidates and record what EMI and the gates said.

One JSON line per (task, condition, candidate) in results.jsonl, plus one
line per (task, candidate) with the ground truth and comparison gates in
truth.jsonl. Workspaces for different (task, condition) pairs run side by
side; candidates within one workspace run one after another on a fresh
copy of the warmed state.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import gates, receipt
from .model import CONDITIONS, CORRECT, Candidate, Condition, Task
from .taxonomy import family
from .workspace import Workspace, ensure_venv

_lock = threading.Lock()


class Run:
    def __init__(self, work: Path, emi: str, out: Path, jobs: int = 2, log=print):
        self.work = work
        self.emi = emi
        self.out = out
        self.jobs = jobs
        self.log = log
        out.mkdir(parents=True, exist_ok=True)

    def venv(self, task: Task) -> Path:
        name = "venv" + "".join("-" + p.split("=")[0].split("<")[0].split(">")[0] for p in sorted(task.pip))
        with _lock:
            return ensure_venv(self.work / name, task.pip)

    def emit(self, name: str, row: dict) -> None:
        with _lock, open(self.out / name, "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    # -- one workspace ----------------------------------------------------
    def workspace(self, task: Task, cond: Condition) -> Workspace:
        ws = Workspace(self.work / "ws" / f"{task.id}__{cond.id}", self.emi, self.venv(task))
        ws.build(task.files, task.laws if cond.laws else None, cond.config, setup=task.setup)
        return ws

    def check(self, ws: Workspace, task: Task, cond: Condition, cand: Candidate,
              state: Path | None = None, env: dict | None = None) -> dict:
        ws.reset()
        enforced = cond.setting == "enforced"
        ws.apply(cand.edits, commit=enforced or cand.committed)
        state = state or ws.fresh_state(cand.id)
        for agent_args in cand.agent_emi:  # what the agent ran itself, with the same state
            ws.run_emi(list(agent_args), state=state, env=env)
        args = ["done", "--format", "json", *cond.done_args]
        if enforced:
            args += ["--setting", "enforced", "--baseline", "main", "--candidate", "HEAD"]
        elif cand.committed:
            args += ["--candidate", "HEAD"]
        t0 = time.monotonic()
        try:
            out = ws.run_emi(args, state=state, env=env)
        finally:
            for rel in cand.cleanup:
                p = ws.repo / rel
                if p.is_file() or p.is_symlink():
                    p.unlink()
        secs = round(time.monotonic() - t0, 2)
        raw = receipt.parse(out.stdout)
        s = receipt.summarize(out.returncode, raw, out.stderr)
        s["seconds"] = secs
        if raw is not None:  # the whole receipt, for reading a surprising row later
            s["raw"] = {k: raw.get(k) for k in ("regression", "change", "changed_old_tests", "laws", "ask",
                                                "repair", "this_run", "signals", "preserve", "adequacy")}
        return s

    def run_unit(self, task: Task, cond_id: str) -> None:
        cond = CONDITIONS[cond_id]
        try:
            ws = self.workspace(task, cond)
            t0 = time.monotonic()
            warm = ws.warm()
            warm_secs = round(time.monotonic() - t0, 2)
        except Exception as e:  # a workspace that cannot be built is a harness fault, recorded
            self.emit("errors.jsonl", {"task": task.id, "condition": cond_id, "error": repr(e),
                                       "trace": traceback.format_exc()[-2000:]})
            self.log(f"  ! {task.id}/{cond_id}: {e}")
            return
        for cand in task.candidates:
            try:
                s = self.check(ws, task, cond, cand)
            except Exception as e:
                s = {"action": "harness_error", "error": repr(e)}
            row = {
                "suite": task.tags[0] if task.tags else "discrimination",
                "task": task.id, "kind": task.kind, "condition": cond_id, "candidate": cand.id,
                "label": cand.label, "mode": cand.mode, "family": family(cand.mode),
                "mentions": list(cand.mentions), "expect_actions": list(cand.expect_actions),
                "warm_seconds": warm_secs, "emi": s,
            }
            self.emit("results.jsonl", row)
            self.log(f"  {task.id:<22} {cond_id:<14} {cand.id:<28} {cand.label:<9} -> {s.get('action')}"
                     f" ({s.get('seconds', '?')}s)")

    # -- truth and gates (once per candidate) -----------------------------
    def truth_unit(self, task: Task) -> None:
        cond = CONDITIONS["laws"] if task.laws else CONDITIONS["tests_only"]
        try:
            ws = Workspace(self.work / "truth" / task.id, self.emi, self.venv(task))
            ws.build(task.files, task.laws or None, {}, setup=task.setup)
        except Exception as e:
            self.emit("errors.jsonl", {"task": task.id, "condition": "truth", "error": repr(e)})
            return
        python = ws.venv / "bin" / "python"
        ws.reset()
        base = run_oracle_for(ws, task, python, "baseline")
        base_ok = (not base["correct"]) if task.oracle_fails_at_baseline else base["correct"]
        self.emit("truth.jsonl", {"task": task.id, "candidate": "<baseline>", "oracle": base,
                                  "valid": base_ok})
        for cand in task.candidates:
            ws.reset()
            ws.apply(cand.edits)
            snap = ws.snapshot(self.work / "snap" / task.id / cand.id)
            oracle = gates.run_oracle(snap, python, task.oracle, task.python_path)
            truth = CORRECT if oracle["correct"] else "incorrect"
            if cand.truth_by_construction:
                truth = cand.label
            g = gates.comparison_gates(ws, snap, python, bool(task.laws))
            for rel in cand.cleanup:
                if (ws.repo / rel).is_file():
                    (ws.repo / rel).unlink()
            row = {"task": task.id, "candidate": cand.id, "label": cand.label, "truth": truth,
                   "label_ok": truth == cand.label, "oracle": oracle, "gates": g, "mode": cand.mode,
                   "by_construction": cand.truth_by_construction}
            self.emit("truth.jsonl", row)
            flag = "" if row["label_ok"] else "   <-- LABEL DISAGREES WITH ORACLE"
            self.log(f"  truth {task.id:<22} {cand.id:<28} {truth}{flag}")

    def run(self, tasks: list[Task], conditions: list[str] | None = None, truth: bool = True,
            candidates: list[str] | None = None) -> None:
        if candidates:
            from dataclasses import replace
            tasks = [replace(t, candidates=[c for c in t.candidates if c.id in candidates]) for t in tasks]
        units: list = []
        for t in tasks:
            if truth:
                units.append(("truth", t, None))
            for c in t.conditions:
                if conditions is None or c in conditions:
                    units.append(("emi", t, c))
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            futs = [pool.submit(self.truth_unit if kind == "truth" else self.run_unit,
                                *((t,) if kind == "truth" else (t, c))) for kind, t, c in units]
            for f in as_completed(futs):
                f.result()


def run_oracle_for(ws: Workspace, task: Task, python: Path, name: str) -> dict:
    snap = ws.snapshot(ws.root.parent.parent / "snap" / task.id / name)
    return gates.run_oracle(snap, python, task.oracle, task.python_path)
