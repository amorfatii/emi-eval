"""Measurement 2: what mypy and pyright, with default settings, say about each
candidate that they did not already say about its baseline.

For each task, the baseline tree and every candidate tree are written to a
scratch folder (product code and tests, no laws), and both checkers run on the
whole tree. An error is identified by (checker, file, error code, message),
not by line number, because lines move between versions. A candidate
"introduces" an error when that identity occurs more often than at the
baseline.

Usage (from the repository root, with mypy and pyright on PATH in a venv that
also has pytest and hypothesis):
  python results-2026-11-11-drafted/scripts/typecheck.py /tmp/work/typecheck \
      > results-2026-11-11-drafted/raw/typecheck.jsonl
"""
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from emi_evals.workspace import write_files  # noqa: E402
from suites import DISCRIMINATION  # noqa: E402

MYPY_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+): error: (?P<msg>.*?)(?:  \[(?P<code>[\w-]+)\])?$")


def mypy(tree: Path) -> list[dict]:
    out = subprocess.run(["mypy", "--no-incremental", "--cache-dir", "/dev/null", "."], cwd=tree,
                         capture_output=True, text=True)
    errs = []
    for line in out.stdout.splitlines():
        m = MYPY_LINE.match(line)
        if m:
            errs.append({"checker": "mypy", "file": m["file"], "line": int(m["line"]),
                         "code": m["code"] or "", "message": m["msg"]})
    return errs


def pyright(tree: Path) -> list[dict]:
    out = subprocess.run(["pyright", "--outputjson", "."], cwd=tree, capture_output=True, text=True)
    data = json.loads(out.stdout)
    return [{"checker": "pyright", "file": str(Path(d["file"]).relative_to(tree.resolve())),
             "line": d["range"]["start"]["line"] + 1, "code": d.get("rule", ""), "message": d["message"]}
            for d in data.get("generalDiagnostics", []) if d["severity"] == "error"]


def key(e: dict) -> tuple:
    return (e["checker"], e["file"], e["code"], e["message"])


def tree_for(task, edits, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    write_files(dest, dict(task.files))
    write_files(dest, dict(edits))
    return dest


def main() -> int:
    work = Path(sys.argv[1])
    for t in DISCRIMINATION:
        base_tree = tree_for(t, {}, work / t.id / "_baseline")
        base = mypy(base_tree) + pyright(base_tree)
        print(json.dumps({"task": t.id, "candidate": "<baseline>", "errors": base}), flush=True)
        base_count = Counter(map(key, base))
        for c in t.candidates:
            tree = tree_for(t, c.edits, work / t.id / c.id)
            errs = mypy(tree) + pyright(tree)
            have = Counter(map(key, errs))
            new_keys = have - base_count
            new = [e for e in errs if key(e) in new_keys]
            print(json.dumps({"task": t.id, "candidate": c.id, "label": c.label, "errors": errs,
                              "new_errors": new,
                              "new_by_checker": dict(Counter(e["checker"] for e in new))}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
