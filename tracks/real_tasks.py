"""Real-project tasks for the closed-loop track (trial E).

A task from `inputs-hard/` whose environment `tracks.hard_tasks prepare`
validated: the agent gets the issue text as its prompt and the project at
its base commit; the hidden tests (the developers' test patch, FAIL_TO_PASS
plus PASS_TO_PASS) grade every stop. The project's test command, for EMI and
the small script alike, is narrowed to the hidden tests' files as the
baseline has them, as in trial C, so runs stay bounded.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from emi_evals.workspace import git
from tracks.rebench import IGNORED, apply_patch, pytest_ids, sh, touched_files

NOTE = ("\n\nThe project's virtualenv is .venv; run tests with `.venv/bin/python -m pytest <files>`. "
        "Fix the issue in the project's code. When the task is done, stop.")


class RealTask:
    def __init__(self, task: dict, work: Path, unmatched: list[str]):
        self.task, self.id = task, task["instance_id"]
        self.prompt = task["problem_statement"] + NOTE
        self.src = work / "hard" / self.id / "src"
        self.venv = work / "hard" / self.id / "venv"
        self.ids = [i for i in task["FAIL_TO_PASS"] + task["PASS_TO_PASS"] if i not in unmatched]
        files = sorted({i.split("::")[0] for i in self.ids})
        self.test_args = ["-q", *[f for f in files if (self.src / f).exists()]]

    def build(self, root: Path, emi: str, laws: dict | None, work: Path) -> Path:
        if root.exists():
            shutil.rmtree(root)
        repo = root / "repo"
        shutil.copytree(self.src, repo, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info"))
        git(repo, "init", "-q", "-b", "main")
        gi = repo / ".gitignore"
        gi.write_text((gi.read_text() if gi.exists() else "") + IGNORED)
        os.symlink(self.venv, repo / ".venv")
        for name, text in (laws or {}).items():
            (repo / ".emi/laws" / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / ".emi/laws" / name).write_text(text)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "baseline")
        env = {k: v for k, v in os.environ.items() if not k.startswith("EMI_")}
        env.update({"XDG_STATE_HOME": str(root / "state-init"), "EMI_HOOK_WARM": "0"})
        init = sh([emi, "init", "--yes"], cwd=repo, env=env)
        cfg_path = repo / ".emi/config.json"
        if not cfg_path.exists():
            raise RuntimeError("emi init: " + (init.stdout + init.stderr)[-400:])
        cfg = json.loads(cfg_path.read_text())
        cfg["tests"]["command"] = [*cfg["tests"]["command"], *self.test_args[1:]]
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "Configure EMI")
        git(repo, "switch", "-q", "-c", "task")
        return repo

    def env(self, repo: Path) -> dict:
        # the agent's and the script's pytest import the workspace, never the
        # checkout the virtualenv's editable install points at
        roots = [str(repo / "src")] if (repo / "src").is_dir() else []
        return {"PYTHONPATH": os.pathsep.join([*roots, str(repo)])}

    def grade(self, tree: Path) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "tree"
            shutil.copytree(tree, dest, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", ".emi", ".claude"))
            # as SWE-bench grades: the files the hidden test patch touches are
            # put back to the baseline first, so an agent's own edits to them
            # cannot keep the hidden tests from applying
            for rel in touched_files(self.task["test_patch"]):
                base = self.src / rel
                if base.is_file():
                    (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(base, dest / rel)
                elif (dest / rel).exists():
                    (dest / rel).unlink()
            if not apply_patch(dest, self.task["test_patch"]):
                return {"correct": False, "failed": {"<test patch>": "does not apply"}}
            res = pytest_ids(self.venv / "bin" / "python", dest, self.ids)
        failed = {i: s for i, s in res.items() if s != "passed"}
        return {"correct": not failed, "failed": failed}


def load(inputs: Path, work: Path) -> list[RealTask]:
    tasks = json.loads((inputs / "tasks.json").read_text())
    valid = {}
    for line in (inputs / "environments.jsonl").read_text().splitlines():
        r = json.loads(line)
        valid[r["instance"]] = r  # the latest validation of each task counts
    return [RealTask(tasks[i], work.resolve(), r["validation"].get("unmatched_ids") or [])
            for i, r in sorted(valid.items()) if r["valid"]]


def regrade(out: Path, inputs: Path, work: Path) -> None:
    """Grade every recorded run again from its saved trees (the final tree and
    each stop's snapshot), rewriting runs.jsonl; no agent runs again."""
    tasks = {t.id: t for t in load(inputs, work)}
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines() if line.strip()]
    for r in rows:
        task = tasks[r["task"]]
        root = work.resolve() / "closed_loop" / f"{r['task']}__{r['setup']}__{r['run']}"
        snaps = sorted(p for p in (root / "snapshots").iterdir() if p.is_dir() and not p.name.endswith("-oracle"))
        r["stops_correct"] = [task.grade(s)["correct"] for s in snaps]
        final = task.grade(root / "repo")
        r["final_correct"], r["oracle_failed"] = final["correct"], sorted(final["failed"])[:6]
        r["wrong_done"] = r["accepted"] and not r["final_correct"]
        r["regraded"] = True
    (out / "runs.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


if __name__ == "__main__":
    import sys
    regrade(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
