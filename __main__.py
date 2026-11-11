"""python -m emi_evals <command> ...

  validate   run the hidden oracles only: every label must agree with its
             oracle, and every oracle must fail at the baseline (or pass, for
             a refactor). Run this after editing a suite.
  run        run EMI on every task × condition × candidate, plus the oracles
             and comparison gates; write results.jsonl and truth.jsonl.
  determinism | adversarial | shapes   the other suites.
  report     score a results directory into report.md and summary.json.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path


def _tasks(suite: str, only: list[str] | None):
    if suite == "discrimination":
        from suites import DISCRIMINATION as tasks
    elif suite == "adversarial":
        from suites.adversarial import TASKS as tasks
    elif suite == "shapes":
        from suites.shapes import TASKS as tasks
    else:
        raise SystemExit(f"unknown suite {suite}")
    return [t for t in tasks if not only or any(o in t.id for o in only)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="emi_evals")
    ap.add_argument("command", choices=["validate", "run", "determinism", "report"])
    ap.add_argument("--suite", default="discrimination")
    ap.add_argument("--emi", default=os.environ.get("EMI_BIN", "emi"))
    ap.add_argument("--work", type=Path, default=Path("work"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--conditions", nargs="*")
    ap.add_argument("--candidates", nargs="*", help="only these candidate ids")
    ap.add_argument("--fresh", action="store_true", help="delete previous results in --out first")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    args.work = args.work.resolve()
    if args.command != "report" and not shutil.which(args.emi) and not Path(args.emi).exists():
        raise SystemExit(f"emi binary not found: {args.emi} (pass --emi or set EMI_BIN)")
    emi = str(Path(args.emi).resolve()) if Path(args.emi).exists() else shutil.which(args.emi)

    if args.command == "report":
        from .report import write_report
        write_report(args.out)
        return 0

    out = args.out
    if args.fresh and out.exists():
        shutil.rmtree(out)
    t0 = time.monotonic()
    if args.command == "determinism":
        from suites.determinism import run as run_det
        run_det(args.work, emi, out, jobs=args.jobs)
    else:
        from .runner import Run
        tasks = _tasks(args.suite, args.only)
        r = Run(args.work, emi, out, jobs=args.jobs)
        if args.command == "validate":
            r.run(tasks, conditions=[], truth=True)
        else:
            r.run(tasks, conditions=args.conditions, truth=True, candidates=args.candidates)
    print(f"done in {time.monotonic() - t0:.0f}s -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
