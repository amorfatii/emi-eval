"""Setup 4's rules: drafted from the task before any code is written.

The work proposal's flow, steps 2 to 4, with a model in each role a model
can play and the person's approval simulated:

  1. questions  a drafter reads the task and the project and asks 3 to 5
                questions about cases the task does not settle, each with
                choices and "doesn't matter" (none for a one-line fix).
  2. answers    the task's author answers by picking one choice per
                question. The author's intent is the task's hidden checks,
                so the answerer is shown them, but may only pick a choice:
                what reaches the rules is bounded by the drafter's questions.
  3. draft      the drafter writes the rules as one pytest file: examples and
                Hypothesis properties, each test's docstring the sentence it
                came from.
  4. teeth      every rule is run against useless versions of the product
                (every function body `raise NotImplementedError`, and every
                body `return None`); a rule that passes on either is dropped.
  5. approval   not simulated beyond this: the kept rules are committed at the
                baseline as the person's laws. Recorded as a limit.

Drafted once per task and committed under `inputs-closed-loop/drafted/`,
so every run of setup 4 is held to the same rules.

usage: python -m tracks.draft_rules --work W --out inputs-closed-loop/drafted --only t01_slugify ...
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from emi_evals.workspace import ensure_venv, write_files  # noqa: E402
from suites import DISCRIMINATION  # noqa: E402

RULES_FILE = "test_drafted_rules.py"


def claude(prompt: str, cwd: Path, model: str, tools: str = "", budget: float = 2.0,
           timeout: int = 900) -> dict:
    """One headless Claude Code call with only the project's own settings."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD"}
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", model,
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--disable-slash-commands", "--no-chrome", "--no-session-persistence",
           "--max-budget-usd", str(budget), "--max-turns", "20"]
    cmd += ["--tools", tools] if tools else ["--tools", ""]
    out = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"result": "", "error": (out.stdout + out.stderr)[-1500:], "total_cost_usd": 0}


def json_in(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        raise ValueError(f"no JSON in: {text[:300]!r}")
    return json.loads(m.group(0))


def python_in(text: str) -> str:
    m = re.search(r"```python\n(.*?)```", text or "", flags=re.S)
    if not m:
        raise ValueError(f"no python block in: {text[:300]!r}")
    return m.group(1)


QUESTIONS = """You are helping a person pin down a coding task before an AI agent writes the code.

The task, as the person wrote it:
---
{prompt}
---

Read the project in this directory. Then ask 3 to 5 questions about cases the task does not settle,
where the answer changes what correct code must do (edge cases, inputs, errors, interactions with
existing behaviour). Each question has 2 to 4 short choices; "doesn't matter" is always added for you.
If the task is a one-line fix with nothing left to settle, ask no questions.

Reply with only JSON: {{"questions": [{{"q": "...", "choices": ["...", "..."]}}]}}"""

ANSWERS = """You wrote this coding task:
---
{prompt}
---

What you want is fixed by these acceptance checks, which are private: never quote them, never
mention them.
---
{oracle}
---

An assistant asks you these questions. For each, pick exactly one of its choices, copied word for
word, or "doesn't matter" when your checks do not settle it.

{questions}

Reply with only JSON: {{"answers": [{{"q": "...", "choice": "..."}}]}}"""

DRAFT = """You are writing the acceptance rules for a coding task before an AI agent writes the code.
A person will approve them; the agent cannot change them; the code is accepted only if they pass.

The task:
---
{prompt}
---

The person's answers to your questions:
{answers}

Read the project in this directory. Write the rules as one pytest file:
- example tests for the cases the task and the answers state, and Hypothesis properties
  (`from hypothesis import given, strategies as st`) where a rule holds for every input;
- each test function's docstring is the plain sentence it enforces;
- only rules the task or the answers state; nothing about how the code is written;
- import from the project's modules by their names as they are now (the file runs from
  `.emi/laws/` with the project root on the import path).

Reply with only the file, in one ```python block."""


def useless(src: str, body: str) -> str:
    """`src` with every function body replaced by `body`."""
    tree = ast.parse(src)
    stmt = ast.parse(body).body
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.body = list(stmt)
    return ast.unparse(tree)


def passing(repo: Path, py: Path, rules: Path) -> set[str]:
    report = repo.parent / (repo.name + "-junit.xml")
    report.unlink(missing_ok=True)
    roots = [str(repo / "src")] if (repo / "src").is_dir() else []
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([*roots, str(repo)]), "PYTHONHASHSEED": "0",
           "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                    f"--junitxml={report}", str(rules)], cwd=repo, env=env, capture_output=True, timeout=600)
    out = set()
    if report.exists():
        for tc in ET.parse(report).getroot().iter("testcase"):
            if not any(ch.tag in ("failure", "error", "skipped") for ch in tc):
                owner = tc.get("classname", "").rsplit(".", 1)[-1]
                name = tc.get("name", "").split("[")[0]
                # module-level tests carry the module as classname, methods their class
                out.add(name if owner == rules.stem else f"{owner}.{name}")
    return out


def drop(src: str, names: set[str]) -> str:
    """`src` without the test functions (or Class.method) named."""
    tree = ast.parse(src)
    def keep(node, owner=""):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return True
        return (f"{owner}.{node.name}" if owner else node.name) not in names
    tree.body = [n for n in tree.body if keep(n)]
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            n.body = [m for m in n.body if keep(m, n.name)] or [ast.Pass()]
    return ast.unparse(tree)


class SyntheticSource:
    """A discrimination task, for drafting."""

    def __init__(self, task):
        self.id, self.issue, self.task = task.id, task.prompt, task
        self.oracle = "\n\n".join(task.oracle.values())

    def lay(self, dest: Path, fix: bool = False) -> None:
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        gold = next(c for c in self.task.candidates if c.id == "gold").edits if fix else {}
        write_files(dest, {**self.task.files, **gold})

    def product(self, dest: Path, rules_src: str) -> list[Path]:
        return [dest / k for k in self.task.files
                if k.endswith(".py") and not os.path.basename(k).startswith("test") and "tests/" not in k]


class RealSource:
    """A real-project task, for drafting: its issue text, its hidden test patch."""

    def __init__(self, task):
        self.task, self.id = task, task.id
        self.issue, self.oracle = task.task["problem_statement"], task.task["test_patch"]
        self.py = task.venv / "bin" / "python"

    def lay(self, dest: Path, fix: bool = False) -> None:
        from tracks.rebench import apply_patch
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(self.task.src, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info"))
        if fix and not apply_patch(dest, self.task.task["patch"]):
            raise RuntimeError(f"{self.id}: the fix does not apply")

    def product(self, dest: Path, rules_src: str) -> list[Path]:
        """The project's files for the modules the rules import."""
        out = []
        for node in ast.walk(ast.parse(rules_src)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
            for mod in names:
                rel = Path(*mod.split("."))
                for base in (dest, dest / "src"):
                    for cand in (base / rel.with_suffix(".py"), base / rel / "__init__.py"):
                        if cand.is_file() and cand not in out:
                            out.append(cand)
        return out


def place(repo: Path, rules_src: str) -> Path:
    """Where EMI runs laws, and where the drafter was told they run."""
    path = repo / ".emi" / "laws" / RULES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rules_src)
    return path


def teeth(source, rules_src: str, work: Path, py: Path) -> tuple[str, list[str], list[str]]:
    no_teeth: set[str] = set()
    for name, body in (("raise", "raise NotImplementedError"), ("none", "return None")):
        repo = work / f"useless-{name}"
        source.lay(repo)
        for f in source.product(repo, rules_src):
            try:
                f.write_text(useless(f.read_text(), body))
            except SyntaxError:
                continue
        no_teeth |= passing(repo, py, place(repo, rules_src))
    kept_src = drop(rules_src, no_teeth)
    kept = sorted(n.name for n in ast.walk(ast.parse(kept_src))
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
    return kept_src, sorted(no_teeth), kept


def draft(source, work: Path, model: str, py: Path, earlier: dict | None = None) -> dict:
    if earlier:
        return finish(source, work, py, earlier)
    proj = work / "project"
    source.lay(proj)
    cost = 0.0
    q = claude(QUESTIONS.format(prompt=source.issue), proj, model, tools="Read,Glob,Grep")
    cost += q.get("total_cost_usd") or 0
    questions = json_in(q.get("result", "")).get("questions", [])
    for item in questions:
        item["choices"] = [*item.get("choices", []), "doesn't matter"]
    answers = []
    if questions:
        a = claude(ANSWERS.format(prompt=source.issue, oracle=source.oracle,
                                  questions=json.dumps(questions, indent=1)), work, model)
        cost += a.get("total_cost_usd") or 0
        answers = json_in(a.get("result", "")).get("answers", [])
    d = claude(DRAFT.format(prompt=source.issue, answers=json.dumps(answers, indent=1) if answers else "(none asked)"),
               proj, model, tools="Read,Glob,Grep")
    cost += d.get("total_cost_usd") or 0
    rules_src = python_in(d.get("result", ""))
    ast.parse(rules_src)  # a rules file that does not parse is no rule
    return finish(source, work, py, {"task": source.id, "model": model, "questions": questions,
                                     "answers": answers, "drafted": rules_src, "cost_usd": round(cost, 4)})


def finish(source, work: Path, py: Path, rec: dict) -> dict:
    """The teeth check, and how the kept rules fare on the starting code and
    on the developers' fix (measured, never used to choose rules)."""
    kept_src, dropped, kept = teeth(source, rec["drafted"], work, py)
    seen = {}
    for name, fix in (("baseline", False), ("fix", True)):
        tree = work / f"check-{name}"
        source.lay(tree, fix=fix)
        seen[name] = sorted(passing(tree, py, place(tree, kept_src)))
    # approval, simulated: a careful person who knows the behaviour they want
    # accepts a rule only if it holds on that behaviour, here the developers'
    # fix. An optimistic stand-in for step 4 of the proposal's flow; the
    # rules it rejects are kept in the record.
    rejected = sorted(set(kept) - {n.rsplit(".", 1)[-1] for n in seen["fix"]})
    approved_src = drop(kept_src, set(rejected) | {f"{c}.{n}" for c in classes(kept_src) for n in rejected})
    return {**rec, "passing_on_baseline": seen["baseline"], "passing_on_fix": seen["fix"],
            "rules": kept_src, "dropped_no_teeth": dropped, "kept": kept,
            "rejected_at_approval": rejected, "approved": approved_src,
            "approved_count": len(kept) - len(rejected)}


def classes(src: str) -> list[str]:
    return [n.name for n in ast.parse(src).body if isinstance(n, ast.ClassDef)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("inputs-closed-loop/drafted"))
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--recheck", action="store_true", help="redo the teeth check on drafts already made")
    ap.add_argument("--hard", type=Path, help="inputs-hard: draft for its validated real-project tasks")
    args = ap.parse_args(argv)
    if args.hard:
        from tracks.real_tasks import load
        sources = [RealSource(t) for t in load(args.hard, args.work)]
    else:
        sources = [SyntheticSource(t) for t in DISCRIMINATION if t.kind != "refactor"]
    for source in sources:
        if args.only and source.id not in args.only:
            continue
        py = source.py if isinstance(source, RealSource) else ensure_venv(args.work.resolve() / "venv") / "bin" / "python"
        task = source
        out = args.out / task.id
        earlier = json.loads((out / "record.json").read_text()) if (out / "record.json").exists() else None
        if earlier and not args.recheck:
            print(f"{task.id}: already drafted")
            continue
        try:
            rec = draft(task, args.work.resolve() / "draft" / task.id, args.model, py, earlier)
        except Exception as e:  # recorded, never dropped
            print(f"{task.id}: drafting failed: {type(e).__name__}: {str(e)[:300]}")
            continue
        out.mkdir(parents=True, exist_ok=True)
        (out / RULES_FILE).write_text(rec.get("approved", rec["rules"]))
        (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(f"{task.id}: {len(rec['questions'])} questions, kept {len(rec['kept'])} rules, "
              f"dropped {len(rec['dropped_no_teeth'])} without teeth; passing on baseline "
              f"{len(rec['passing_on_baseline'])}, on the fix {len(rec['passing_on_fix'])}; "
              f"approved {rec['approved_count']}; ${rec['cost_usd']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
