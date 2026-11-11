"""Fix trial C's inputs before any EMI number exists.

Reads the parquet files of nebius/SWE-agent-trajectories (agent patches with
resolved/unresolved labels) and nebius/SWE-bench-extra (tasks), chooses one
task per project by the rule below, and writes the files `tracks/rebench.py`
runs from, so the run needs no network for its inputs:

  mixed.json   chosen task -> its non-empty agent patches with labels
  tasks.json   chosen task -> its SWE-bench-extra row
  choice.json  per project: the task chosen, the rule that chose it, and
               the label counts of every task it was chosen from

Rule: the first task (by instance id) that has a SWE-bench-extra row and at
least 2 resolved and 2 unresolved non-empty agent patches; failing that,
the first with at least 1 of each; failing that, the project has no task.

usage: python tools/build_inputs.py TRAJ_DIR EXTRA_PARQUET OUT_DIR
  TRAJ_DIR       directory holding the trajectory parquet shards
  EXTRA_PARQUET  the SWE-bench-extra parquet file
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

PROJECTS = [
    "tehmaze__ansi", "johnsyweb__python_sparse_list", "konradhalas__dacite",
    "Melevir__cognitive_complexity", "package-url__packageurl-python", "benmoran56__esper",
    "andialbrecht__sqlparse", "serge-sans-paille__gast",
]
COLUMNS = ["instance_id", "model_name", "target", "exit_status", "generated_patch"]


def project_of(instance_id: str) -> str:
    return instance_id.rsplit("-", 1)[0]


def attempts(traj_dir: Path) -> dict[str, list[dict]]:
    by_task: dict[str, list[dict]] = {}
    for shard in sorted(traj_dir.glob("0*.parquet")):
        for row in pq.read_table(shard, columns=COLUMNS).to_pylist():
            if project_of(row["instance_id"]) in PROJECTS:
                by_task.setdefault(row["instance_id"], []).append(row)
    return by_task


def usable(a: list[dict]) -> tuple[list[dict], list[dict]]:
    ok = [x for x in a if x["target"] and (x["generated_patch"] or "").strip()]
    bad = [x for x in a if not x["target"] and (x["generated_patch"] or "").strip()]
    return ok, bad


def choose(by_task: dict[str, list[dict]], have_row: set[str], project: str):
    ids = sorted(i for i in by_task if project_of(i) == project and i in have_row)
    for need in (2, 1):
        for iid in ids:
            ok, bad = usable(by_task[iid])
            if len(ok) >= need and len(bad) >= need:
                return iid, need
    return None, 0


def main(traj_dir: str, extra: str, out: str) -> int:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_task = attempts(Path(traj_dir))
    rows = {r["instance_id"]: r for r in pq.read_table(extra).to_pylist()}
    mixed, tasks, choice = {}, {}, {}
    for p in PROJECTS:
        iid, need = choose(by_task, set(rows), p)
        seen = {}
        for t in sorted(i for i in by_task if project_of(i) == p):
            ok, bad = usable(by_task[t])
            seen[t] = {"resolved": len(ok), "unresolved": len(bad), "in_swe_bench_extra": t in rows}
        choice[p] = {"task": iid,
                     "rule": f"first with at least {need} resolved and {need} unresolved" if iid
                     else "no task has both labels",
                     "tasks_seen": seen}
        print(f"{p:<34} -> {iid}  ({choice[p]['rule']}; {len(seen)} tasks seen)")
        if iid:
            ok, bad = usable(by_task[iid])
            mixed[iid] = [{"model": a["model_name"], "target": "True" if a["target"] else "False",
                           "exit_status": a["exit_status"], "patch": a["generated_patch"]}
                          for a in sorted(ok, key=lambda a: a["model_name"]) + sorted(bad, key=lambda a: a["model_name"])]
            row = dict(rows[iid])
            row.pop("__index_level_0__", None)
            tasks[iid] = row
    for name, data in (("mixed.json", mixed), ("tasks.json", tasks), ("choice.json", choice)):
        (out_dir / name).write_text(json.dumps(data, indent=1, sort_keys=True, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
