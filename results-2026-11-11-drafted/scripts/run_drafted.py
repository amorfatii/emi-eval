"""Run the discrimination suite under a drafted-laws condition.

The condition (`drafted_no_questions` or `drafted_questions`, defined in
emi_evals/model.py) is the `laws` condition with different laws installed.
Tasks, candidates, oracles and labels are the suite's own; only the `laws`
field of each task is swapped, in memory, for the drafted files in
laws/<condition>/<task>/. The truth pass then runs the restore_laws gate with
the same drafted laws.

Usage (from the repository root):
  python results-2026-11-11-drafted/scripts/run_drafted.py drafted_questions \
      --emi $(which emi) --work /tmp/work/dq --out results-2026-11-11-drafted/raw/drafted_questions
"""
import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from emi_evals.runner import Run  # noqa: E402
from suites import DISCRIMINATION  # noqa: E402


def drafted_laws(cond: str, task_id: str) -> dict[str, str]:
    d = HERE / "laws" / cond / task_id
    return {p.name: p.read_text() for p in sorted(d.glob("*.py"))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("condition", choices=["drafted_no_questions", "drafted_questions"])
    ap.add_argument("--emi", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--candidates", nargs="*", help="only these candidate ids (the timing pass)")
    ap.add_argument("--no-truth", action="store_true", help="skip the oracle and gates (the timing pass)")
    a = ap.parse_args()
    tasks = []
    for t in DISCRIMINATION:
        if a.only and t.id not in a.only:
            continue
        laws = drafted_laws(a.condition, t.id)
        if not laws:
            raise SystemExit(f"no drafted laws for {t.id}")
        tasks.append(replace(t, laws=laws, conditions=(a.condition,)))
    t0 = time.monotonic()
    Run(a.work.resolve(), a.emi, a.out, jobs=a.jobs).run(tasks, truth=not a.no_truth, candidates=a.candidates)
    print(f"done in {time.monotonic() - t0:.0f}s -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
