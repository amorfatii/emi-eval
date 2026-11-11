# Drafted skeletons on three real tasks — 2026-11-11

**Question.** In the "Skeleton Coding" paper (arXiv 2610.38214), skeletons
roughly halved agent error, but they were written from the finished
solution, and nothing checked that the agent kept to them. Does a skeleton
drafted **before** anyone knows the answer still help?

**Short answer.** Drafted skeletons did no harm here, and on one task in three
they made the difference. With the skeleton, all 6 of 6 runs passed the hidden
tests; with the bug report alone, 4 of 6 passed. Both failures were on
the same task (esper). That task is the only one where the bug report alone
left room to miss part of the fix. All three drafted skeletons named the same
functions the developers changed. One (esper) also named two functions the
developers left alone. The sample is three tasks with two runs each, so this
shows only that the idea is plausible. It is not a measurement.

Built on branch `trial-c-rebench` (trial C: eight real projects). Its tasks,
labels and results were not changed. Everything new is in this folder.

## The three tasks, and why

The task asked for three trial C tasks whose developers' fix touches more
than one function. **Only two of the eight do:**

| Task | Developers' fix | Picked because |
| --- | --- | --- |
| `benmoran56__esper-81` | `World.create_entity` and `World.add_component` (moves "create the entity" from one to the other) | two functions, and a change of responsibility between them |
| `serge-sans-paille__gast-50` | four new `visit_Assign` methods in two files, plus the `Assign` entry of the node table in a third | five places, three files |
| `package-url__packageurl-python-29` | adds `PackageURL.__hash__` | **substitute**: one function only. The other five fixes each change a single line or function too. This one was picked because its fix *adds a public method*, which is exactly what a skeleton names. The others change a body only (cognitive_complexity, sparse_list, sqlparse, dacite) or a parameter that the bug report already spells out (ansi) |

The environments are trial C's own. Each was built with
`python -m tracks.rebench prepare`, using the interpreters and packages in
`inputs-rebench/environment.json` (gast on Python 3.9). All three passed
trial C's check again: the hidden tests fail at the base commit and pass with
the developers' fix.

## The three drafted skeletons

Each skeleton was written by a **Drafter**: a separate headless `claude`
run (Opus 5.5, effort medium) with fresh context. It saw only the bug report
and a copy of the code at the base commit, with no git history. Its tools were
read-only plus writing `SKELETON.md`, and no Drafter changed code. It ran under
bubblewrap, with the eval repo, all of `/tmp` and the Claude transcript folder
hidden. It never saw the fix, the hidden tests or any agent attempt. The files
are saved unedited in `skeletons/`.

**esper-81**
```
- CHANGE World.create_entity(self, *components: _C) -> int — always registers the new entity (as empty if no components), then attaches any components
- CHANGE World.add_component(self, entity, component_instance, type_alias=None) -> None — adds to an existing entity only; raises KeyError if never created
- CHANGE World.remove_component(self, entity, component_type) -> int — keeps the entity registered even when it has no components left
- CHANGE World.entity_exists(self, entity) -> bool — True for any created, not-deleted entity, including empty ones
- RULE World.add_component may not create entries in World._entities — only create_entity registers entities
```

**gast-50**
```
- TYPE gast/gast.py::Assign — node table entry gains a type_comment field
- ADD gast/ast3.py::Ast3ToGAst.visit_Assign(self, node) -> gast.Assign — (for Python < 3.8) build gast Assign with type_comment=None
- ADD gast/ast3.py::GAstToAst3.visit_Assign(self, node) -> ast.Assign — (for Python < 3.8) build ast Assign, dropping type_comment
- ADD gast/ast2.py::Ast2ToGAst.visit_Assign(self, node) -> gast.Assign — build gast Assign with type_comment=None
- ADD gast/ast2.py::GAstToAst2.visit_Assign(self, node) -> ast.Assign — build Python 2 Assign, dropping type_comment
```

**packageurl-29**
```
- ADD src/packageurl/__init__.py::PackageURL.__hash__(self) -> int — hash of the canonical purl string (to_string())
```

Drafting took 14 to 31 seconds and cost $0.10 to $0.17 per task ($0.42 for all three).

## How close each skeleton was to the developers' fix

| Task | Verdict | Detail |
| --- | --- | --- |
| esper-81 | **Same functions, plus two extra** | `create_entity` and `add_component`, and the rule, match the fix exactly; the fix keeps to the rule. It also lists `remove_component` (keep an emptied entity) and `entity_exists`. The developers changed neither. `entity_exists` gets the new behaviour for free, so that line is harmless. The `remove_component` line is a **real behaviour change the developers did not make**. The hidden tests do not exercise it, so it cost no passes, but it is an over-reach that a person would need to catch |
| gast-50 | **Same functions** | All five places match. Small slip: two descriptions say "for Python < 3.8", but the developers put only `Ast3ToGAst.visit_Assign` under a version test. `GAstToAst3.visit_Assign` is unconditional in the fix |
| packageurl-29 | **Same function, same idea** | Identical to the fix, down to hashing `to_string()` |

None was wrong. The developers' fix, checked with the same script as the
agents (below), stays inside its drafted skeleton on all three tasks.

## Implementation runs (12, as budgeted)

Each implementer is the headless `claude` CLI, Opus 5.5, effort medium. It ran
on a fresh copy of the base commit in bubblewrap, with the same hiding as the
Drafter. Its tools were Read/Edit/Write/Glob/Grep/Bash; web tools and subagents
were disallowed. Arm (a) got the bug report. Arm (b) got the bug report plus
the skeleton and "keep to it". I audited every Bash command in the logs: none
used the network, git history, pip, or any path outside the workspace.

### Hidden tests (trial C's grader: hidden test patch applied, all FAIL_TO_PASS and PASS_TO_PASS must pass)

| Task | (a) report only | (b) report + skeleton |
| --- | --- | --- |
| esper-81 | **0 of 2** | **2 of 2** |
| gast-50 | 2 of 2 | 2 of 2 |
| packageurl-29 | 2 of 2 | 2 of 2 |
| **All** | **4 of 6** | **6 of 6** |

Both esper failures are the same miss. The agent made `create_entity` register
empty entities but left `add_component` creating unknown entities, so
`add_component(123, …)` still succeeds. The hidden test
`test_adding_component_to_not_existing_entity_raises_error` expects
`KeyError`. The bug report does say this ("Imo should raise KeyError"), but as
an aside after the main bug. The skeleton turned it into an explicit
`add_component` line and a rule, and both (b) runs did it.

**Grading note.** On esper and gast, all eight runs in both arms also edited
the project's old test file, which the hidden test patch rewrites. The full
diff then conflicts with the hidden tests, so those runs were graded on their
non-test files only. Trial C's agent patches had no such conflict. The fallback
applies to both arms alike and is recorded per run in `grades.jsonl`
(`graded: source_only`).

### Did the result stay inside the skeleton? (`check_skeleton.py`, a throwaway script)

For each named function, the script checks that it exists after the change
with the stated parameter names, and the return annotation where the code has
one. It looks for any public function, method or class added, removed or
re-signed that the skeleton does not name. It checks the RULE line; the only
rule (esper) is about writes, not calls, so it is checked as "no write to
`self._entities[...]` inside `add_component`".

| Arm | Inside the skeleton | Notes |
| --- | --- | --- |
| **(b) with skeleton** | **6 of 6** | No unnamed public additions, no rule broken. Both esper (b) runs also made the over-reaching `remove_component` change, because the skeleton asked for it |
| (a) without (for reference) | 4 of 6 | gast and packageurl happen to match. Both esper (a) runs **break the rule**, which is the same miss the hidden tests caught |

No run, in either arm, added a public function the skeleton did not name.
Signatures of named functions matched in every run.

### Cost and time per run (as the CLI reports them, list prices)

| Task | Arm | Run 1 | Run 2 |
| --- | --- | --- | --- |
| esper-81 | a | 37 s, $0.20 | 43 s, $0.19 |
| esper-81 | b | 39 s, $0.24 | 33 s, $0.20 |
| gast-50 | a | 39 s, $0.27 | 73 s, $0.36 |
| gast-50 | b | 57 s, $0.30 | 54 s, $0.30 |
| packageurl-29 | a | 18 s, $0.12 | 18 s, $0.13 |
| packageurl-29 | b | 17 s, $0.11 | 13 s, $0.10 |

Averages: arm (a) 38 s and $0.21 per run; arm (b) 36 s and $0.21 per run. The
skeleton did not add cost. Whole trial: $2.49 implementing plus $0.42
drafting, under $3. Tasks ran three at a time, which may stretch the times a
little.

## Honest limits

- **Three tasks, two runs each.** The whole difference is one task (esper),
  where arm (a) missed the same thing twice. That is consistent with "the
  skeleton helps when the report buries part of the fix". It is equally
  consistent with chance on one task. No rate here has a usable margin.
- **The tasks were easy for this agent.** Arm (a) already passed 4 of 6. The
  paper's halving was measured where agents often fail; this sample had little
  room to show it.
- **Only two of the three tasks have multi-function fixes**, because only two
  of trial C's eight do. packageurl is a one-method substitute, and there the
  skeleton could only confirm what the agent did anyway.
- **The bug reports were good.** The gast report spells out the node-table
  change, and the esper report names `add_component`. With vaguer reports the
  Drafter would have less to go on, and so would arm (a).
- **The Drafter is the same model as the implementer.** A person drafting the
  skeleton is the product idea; here a model played the person. Its esper
  skeleton over-reached (`remove_component`), and arm (b) faithfully copied the
  over-reach. Following the skeleton reproduces its mistakes, so a person
  still has to read it.
- **The conformance check is a throwaway script.** It checks names, parameter
  names, annotations and one hand-coded rule, not behaviour. "Inside the
  skeleton" means the shape matched, not that the code is right.
- **Who played which role.** Drafter: headless `claude`, Opus 5.5, medium,
  read-only, isolated. Implementers: headless `claude`, Opus 5.5, medium,
  isolated. Grader: trial C's code (`tracks/rebench.py`). Conformance check
  and this report: the orchestrating session, on Opus 5.5 at medium effort;
  its first turn ran on a different model before it was switched. That
  session had seen the developers' fixes, but it wrote no skeleton or
  prompt content beyond the fixed templates in `trial.py`.

## Is it worth a larger trial?

Yes, but a different one, not just more of the same.

1. Pick tasks where agents fail without help. Trial C's real-world pool is
   mostly one-line fixes that this agent already solves.
2. Draw on a larger pool with more multi-function fixes, enough to say
   something about each arm, for example 15 to 20 tasks with 3 runs per arm.
3. Have a person, or a deliberately weaker model, draft some skeletons, to see
   how often drafted skeletons are wrong and what following a wrong one costs.
   The esper `remove_component` line is the first example.

The cost is small: about $0.21 per run and $0.14 per draft.

## Files

- `trial.py`: draft, implement and grade (prompts included)
- `check_skeleton.py`: the throwaway conformance check
- `skeletons/`: the three drafted skeletons, as written
- `drafts.jsonl`, `runs.jsonl`: time, cost and turns per Drafter and implementer run
- `patches/`: each run's diff against the base commit
- `grades.jsonl`: hidden-test results per run
- `skeleton_checks.jsonl`: conformance results per run
- `logs/`: full stream-json transcripts of every agent run
