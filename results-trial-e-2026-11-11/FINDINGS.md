# Trial E: a real agent, four ways (2026-11-11)

**152 of 168 planned runs.** The trial was stopped by request before the last
16 finished: all 12 openharness runs and 4 of 12 pygraphistry runs. So 13 of
the 14 tasks are measured, 12 of them completely.

Agent: Claude Code headless, `claude-sonnet-5-5`, at most 40 turns and $3 a
run, limited to editing in its task folder and running the project's tests,
`git status` and `git diff`. EMI: `amorfatii/EMI` commit `5eccf77`, release
build, sandboxed with bubblewrap. Tasks: `inputs-hard/`, 14 recent SWE-rebench
leaderboard issues (24 April to 12 May 2026). Setup 4's rules:
`inputs-hard/drafted/`, approved by a simulated approver that accepts only
rules that hold on the developers' fix (optimistic). Tables: `report.md`.
Raw rows: `runs.jsonl`. Cost: $19.08 for the runs, $1.95 for drafting.

## Against the pass marks

| Question | Pass mark | Result | Verdict |
| --- | --- | --- | --- |
| EMI beats the script | Wrong "done" accepted at least a third less often, no fewer solved, at most 30% more tokens | Accepted wrong work 7 vs 15 (paired, 37 runs); solved 18 vs 17; tokens −11% | **Met on paper, not in substance.** The gap comes from EMI being unable to check, not from catching (below) |
| Drafted rules help | Setup 4 beats setup 3 | Wrong accepted 9 vs 7; solved 16 vs 17 | **No** |

## What happened

**1. EMI could not check 4 of the 14 projects, in any run.** It reported
"incomplete" on every hermes-webui, fromager, rapid-mlx and virtualizarr
check. Two of these (hermes-webui, fromager) are among the six tasks an
unaided agent gets wrong. The agent was let stop, with the person told
nothing was verified. Three different EMI faults, each reproduced by hand:

- **Import check confuses a project module with an installed package of the
  same name.** rapid-mlx has a module `mcp` and the `mcp` package is
  installed; virtualizarr has a module `xarray` and `xarray` is installed.
  EMI concludes "the tests would not import the code being checked", which
  is false. This is the third project with this fault, after sqlparse in
  trial C (`formatter`).
- **fromager: "pytest did not understand its command line".** The project's
  own command runs, and so does that command with EMI's pytest options
  added. The cause is something EMI adds on top, probably its own pytest
  plugin; not established.
- **hermes-webui: "the baseline lists no tests to hold".** The same command
  collects 53 tests when run with pytest directly; EMI's listing finds none.

**2. Where EMI could check, it was close to the script.** On the 10 projects
EMI could check, over 26 runs each: accepted wrong work 7 (EMI) vs 9
(script) vs 12 (no checker); ended correct 12 vs 13 vs 11.

**3. On the hard tasks EMI could check, it caught nothing.** On eodag,
dbt-databricks and schemathesis, no setup ever ended correct. EMI accepted
wrong work in 6 of 9 runs. The other 3 were schemathesis runs where the
agent ended without claiming done (2 ran out of turns), which is not a catch.
The script accepted wrong work in 9 of 9.

**4. Only the script's send-backs led to fixes.** In 7 runs the script sent
wrong work back, and 3 of those ended correct. EMI sent wrong work back in 3
runs, setup 4 in 3, and none of those ended correct. EMI never sent correct
work back. The script did 9 times, in 3 runs, because the original tests
fail when a correct fix changes behaviour they assert (as in trial C). All 3
of those runs still ended correct.

**5. Friction on correct work.** Correct work went unaccepted in 6 script
runs, 7 EMI runs and 6 setup-4 runs. For EMI this was mostly "incomplete" on
rapid-mlx and virtualizarr (6 runs). Every time EMI sent work to a person,
the agent had edited an existing test file (pygraphistry 4, schemathesis 3).

**6. Drafted rules did not help, even with an optimistic approver.**
Approval left rules for 10 of 14 tasks; 4 drafts had no rule that held on
the fix. Where rules were laid, the agent did not end correct more often
(16 vs 17), and accepted wrong work slightly more often (9 vs 7). Rules
that would catch the bug existed for dbt-databricks, openharness,
hermes-webui and fromager. But EMI could not check hermes-webui or fromager,
and openharness was not run. That leaves only dbt-databricks with
bug-catching rules that EMI could enforce, and setup 4 caught none of its
wrong runs. The cause was not looked into.

**7. Nothing else went wrong.** No agent read the lab, no run timed out, 2
runs ran out of turns.

## What it means

- **EMI's first job is to run on real projects.** Three faults made it
  absent from 4 of 14 projects, and from 2 of the 6 hard tasks. Until those
  are fixed, a trial measures how often EMI fails to start, not whether it
  catches more. Each fault deserves an eval case.
- **Catching and steering are different.** Even the script's crude
  send-backs, which quote pytest's failure lines, turned wrong work right 3
  times. EMI's send-backs never did. What EMI tells the agent when it sends
  it back is worth a look.
- **Rules drafted from the issue text did not catch these bugs.** Even
  approved, the rules for the hard tasks either passed on the buggy code
  (eodag, schemathesis) or sat on projects EMI could not check. Drafting
  from issue text alone may be too weak; trial B's design should test that
  before building the simple layer.

## Limits

- 152 of 168 runs; openharness missing entirely, pygraphistry partly.
- 3 runs per task and setup; 13 tasks. Wide margins on every rate.
- Restricted shell for the agent (all setups alike).
- One agent model; agents from other vendors may respond to send-backs
  differently.
- Approval is simulated by checking rules against the developers' fix, which
  a person would not have.
- EMI `5eccf77`, not the three-fix branch.
