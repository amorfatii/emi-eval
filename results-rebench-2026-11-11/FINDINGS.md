# Trial C findings: eight real projects, 2026-11-11

EMI at `amorfatii/EMI` commit `5eccf77` (release build), sandboxed with
bubblewrap on every check. Inputs fixed before the run in `inputs-rebench/`.
Generated tables: `report.md`. Raw rows: `results.jsonl`, `workspaces.jsonl`,
`instances.jsonl`, `run.log`.

## Against the pass marks

| Question | Pass mark | Result | Verdict |
| --- | --- | --- | --- |
| Works on real projects | A real answer on at least 6 of 8 | 7 of 8 (sqlparse: "incomplete" on every check) | **Pass** |
| Fast enough | At most 3x the project's own run, and under 5 minutes | Every check under 11 s; but 3.9x to 11x a test run of under 1 s | **Fail on the ratio, pass on the time.** The mark does not fit tiny suites (below) |
| Leaves honest work alone | At least 90% of correct changes finish | 12 of 23 (52%) overall; 12 of 12 where a right fix can pass the old tests and EMI can check | **Fail as written**, for two reasons below, neither of them a wrong block by EMI's own logic |
| Beats the script | — (trial E) | Same decision as the script on 66 of 66 checks outside sqlparse | Not better, not worse |

## What happened

**1. EMI decided exactly as the small script did, everywhere it could check.**
66 of 66 checks outside sqlparse. On the four tasks where right and wrong can
be told apart (ansi, sparse_list, dacite, packageurl), both let all 12 correct
changes through. Both caught 4 of 7 wrong ones with only the project's tests,
and 7 of 7 with the hidden tests as laws. This repeats the Nov 11 rerun on
real code: the checker adds nothing over the script on these tasks, and
person-stated rules do the catching.

**2. In 3 of 8 real tasks the correct fix fails the project's existing tests.**
cognitive_complexity, esper and gast change behaviour that old tests assert,
and the developers rewrote those tests in the same change. A right fix that
leaves the old tests alone fails them. EMI and the script both reject it,
and both read the evidence correctly. An agent that edits the old tests
instead goes to a person under EMI (`ask_person`). This is common in real
work, it is what drives the honest-work rate down, and the toy tasks never
had it. It argues for the plan's "questions before coding": a person stating
up front that a behaviour changes turns this into an approved edit rather
than a block.

**3. sqlparse: an EMI false alarm.**
Every sqlparse check ends "incomplete": "the tests would not import the code
being checked: formatter from …/python3.9/formatter.py". The project has a
module `sqlparse/formatter.py`, and Python 3.9's standard library still has a
`formatter` module. EMI's import check appears to resolve the module by its
short name to the standard library's (not yet confirmed in the code), so it concludes the tests would not
import the project's code. They do: the script and the grader both run the
project's code. It surfaced because sqlparse needed Python 3.9 (it fails
under 3.13), and the standard library dropped `formatter` in 3.10. Any
project with a module named like a standard-library module would hit the same
thing. Fix candidate in `emi-python` (import check), with an eval case.

**4. Speed: a fixed cost of about 3 seconds.**
EMI's check takes 1.9 s to 10.7 s. The projects' own runs of the same tests
take 0.35 s to 6.2 s, so the ratio is 4x to 11x for sub-second suites, and
1.6x to 2.2x where the suite takes about 2 s or more. Laws add about 3 to 4 s more
(the baseline run of the laws). The warm-up, paid once per baseline, is 1.4 s
to 14.5 s. "3x the project's own run" punishes small suites for a constant
cost; "under 5 minutes" is met everywhere with a wide margin. Suggest
restating the mark as "at most 3x, or under 10 seconds, whichever is larger".

**5. Determinism held.** The developers' fix, checked twice from fresh state,
gave the identical decision on all 16 checks.

**6. Ground truth.** Re-grading matched the dataset's labels on 30 of 31
agent patches; the 31st does not apply to the base commit here.

## Repairs made to get environments running (all recorded)

- sqlparse (2016) and gast (2020) run on Python 3.9; under 3.13 their tests
  fail with the developers' fix (`inputs-rebench/environment.json`).
- dacite needed `pytest-benchmark`, which its own pytest settings require.
  Its first run is kept in `superseded-dacite-missing-plugin.jsonl`: every
  check failed on pytest's command line, for EMI and the script alike.
- packageurl: one dataset test id (`test_packageurl.python_safe_name`) names
  no test at the baseline nor with the fix; it is left out of grading and
  listed in `instances.jsonl`.

## Limits

- 8 tasks, 31 agent patches, 15 wrong ones. Every rate has a wide margin.
- The test command is narrowed to the task's own test files, except in the
  `full_suite` condition (developers' fix only).
- All eight are small pure-Python libraries, run with plain pytest. Nothing
  here covers tox, make, wrapper scripts or tests that need the network.
- The agent patches come from SWE-agent, not Claude Code or Codex, and only 4
  of 31 touch tests.
- The script arm and EMI see the same narrowed command; the script is the
  suites' `restore` gate.
