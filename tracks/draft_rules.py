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
    report = repo / "junit.xml"
    report.unlink(missing_ok=True)
    env = {**os.environ, "PYTHONPATH": str(repo), "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
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
        name = f"{owner}.{node.name}" if owner else getattr(node, "name", "")
        return not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and name in names)
    tree.body = [n for n in tree.body if keep(n)]
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            n.body = [m for m in n.body if keep(m, n.name)] or [ast.Pass()]
    return ast.unparse(tree)


def teeth(task, rules_src: str, work: Path, py: Path) -> tuple[str, list[str], list[str]]:
    product = {k: v for k, v in task.files.items()
               if k.endswith(".py") and not os.path.basename(k).startswith("test") and "tests/" not in k}
    no_teeth: set[str] = set()
    for name, body in (("raise", "raise NotImplementedError"), ("none", "return None")):
        repo = work / f"useless-{name}"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True)
        write_files(repo, {**task.files, **{k: useless(v, body) for k, v in product.items()}})
        (repo / RULES_FILE).write_text(rules_src)
        no_teeth |= passing(repo, py, repo / RULES_FILE)
    kept_src = drop(rules_src, no_teeth)
    kept = sorted(n.name for n in ast.walk(ast.parse(kept_src))
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
    return kept_src, sorted(no_teeth), kept


def draft(task, work: Path, model: str, py: Path) -> dict:
    proj = work / "project"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    write_files(proj, task.files)
    cost = 0.0
    q = claude(QUESTIONS.format(prompt=task.prompt), proj, model, tools="Read,Glob,Grep")
    cost += q.get("total_cost_usd") or 0
    questions = json_in(q.get("result", "")).get("questions", [])
    for item in questions:
        item["choices"] = [*item.get("choices", []), "doesn't matter"]
    answers = []
    if questions:
        oracle = "\n\n".join(task.oracle.values())
        a = claude(ANSWERS.format(prompt=task.prompt, oracle=oracle,
                                  questions=json.dumps(questions, indent=1)), work, model)
        cost += a.get("total_cost_usd") or 0
        answers = json_in(a.get("result", "")).get("answers", [])
    d = claude(DRAFT.format(prompt=task.prompt, answers=json.dumps(answers, indent=1) if answers else "(none asked)"),
               proj, model, tools="Read,Glob,Grep")
    cost += d.get("total_cost_usd") or 0
    rules_src = python_in(d.get("result", ""))
    ast.parse(rules_src)  # a rules file that does not parse is no rule
    kept_src, dropped, kept = teeth(task, rules_src, work, py)
    return {"task": task.id, "model": model, "questions": questions, "answers": answers,
            "drafted": rules_src, "rules": kept_src, "dropped_no_teeth": dropped, "kept": kept,
            "cost_usd": round(cost, 4)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("inputs-closed-loop/drafted"))
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    py = ensure_venv(args.work.resolve() / "venv") / "bin" / "python"
    for task in DISCRIMINATION:
        if task.kind == "refactor" or (args.only and task.id not in args.only):
            continue
        out = args.out / task.id
        if (out / RULES_FILE).exists():
            print(f"{task.id}: already drafted")
            continue
        rec = draft(task, args.work.resolve() / "draft" / task.id, args.model, py)
        out.mkdir(parents=True, exist_ok=True)
        (out / RULES_FILE).write_text(rec["rules"])
        (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(f"{task.id}: {len(rec['questions'])} questions, kept {len(rec['kept'])} rules, "
              f"dropped {len(rec['dropped_no_teeth'])} without teeth, ${rec['cost_usd']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
