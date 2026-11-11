# Trial E pilot: 3 tasks, 4 setups, once each (2026-11-11)

Agent: Claude Code 2.1.322 headless, `claude-sonnet-5-5`, at most 40 turns and
$3 per run. EMI: `amorfatii/EMI` commit `5eccf77`, release build. Tasks:
t01_slugify, t04_order_cancel and t06_lru_recency. Setup 4's rules are in
`inputs-closed-loop/drafted/`. Tables: `report.md`. Raw rows: `runs.jsonl`.

## What the pilot was for

To confirm that the setup works and to measure the real cost of a run.

- **The setup works.** All four setups ran. EMI's hook and the script's hook
  fired on every stop, and every stop was snapshotted and graded. No agent
  read the lab, where the hidden checks live.
- **Cost per run is much lower than estimated.** The mean was $0.04 and the
  highest $0.09, against the 21 cents assumed. The 12 runs cost $0.46 in all,
  and drafting the rules for the three tasks cost $0.22. At this rate, 20
  tasks × 4 setups × 3 runs would cost about $10. Harder tasks will cost more
  per run.

## What it showed

**These tasks are too easy to compare setups.** All 12 runs ended correct,
the 3 with no checker included, and no run was sent back. Every agent
stopped exactly once, in 5 to 13 turns. This is the image's "why harder
tasks" risk, confirmed: on these tasks every setup scores the same.

**One send-to-a-person on correct work.** In t04_order_cancel with drafted
rules, the agent added its tests to the existing test file. EMI flags any
edit to an old test file for a person (`ask_person`, `changed_old_test`),
so correct work was not accepted without a person. In the same task under
EMI without rules, the agent put its tests in a new file and was accepted.
This is the same friction trial C found: honest work that touches an
existing test file waits for a person. It is not counted as a wrong "done";
the report shows it as not accepted.

**Tokens.** The EMI setups used a median of 41,000 to 43,000 tokens against
35,000 without EMI, with nothing sent back in any run. With three runs this
is noise from how the agent explored, not a measured overhead.

## How the agent was limited

This session's safety check refused an unrestricted agent. The agent here
may edit files in its own task folder and run only
`.venv/bin/python -m pytest`, `git status` and `git diff`; any other shell
command is refused. 11 of 12 runs had at least one command refused (mostly
`python -c` probes or piped commands). Every run still finished. The
limit applies equally to all four setups, but it makes the agent less
capable than a normal Claude Code session. On a machine where the agent
may run any command, set `ALLOWED` in `tracks/closed_loop.py` to the full
tool list.

## Before the full trial

1. **Harder tasks.** Use tasks where an unaided agent is wrong often enough to
   compare against: the trial C projects (real issues, with agent attempts
   known to fail), or harder synthetic ones. Check the difficulty first by
   running only the no-checker setup.
2. Draft rules for the remaining tasks (`python -m tracks.draft_rules`, which
   skips tasks already drafted).
3. Decide whether the limited shell stays. It keeps the comparison fair but
   understates what a real agent does.
