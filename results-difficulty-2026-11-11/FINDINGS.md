# Difficulty check for trial E, 2026-11-11

Question: do the harder tasks leave an unaided agent wrong often enough for
trial E to compare setups? Go-ahead mark: at least 3 of 10 wrong.

**Answer: yes. 6 of 14 tasks ended wrong (43%).**

Agent: Claude Code headless, `claude-sonnet-5-5`, no checker, once per task,
at most 40 turns and $3. It may edit only in its task folder and run only
the project's tests, `git status` and `git diff`, as in the pilot. Tasks:
`inputs-hard/`, 16 recent SWE-rebench leaderboard issues (24 April to 12 May
2026), chosen by a rule fixed before any run.

## Environments: 14 of 16 usable

anyio-1134 and opensandbox-816 were rejected. Every hidden test in the files
their fixes are graded on fails to collect in this environment, at the
baseline and with the fix alike, so there is nothing to grade
(`inputs-hard/environments.jsonl`).

## Results

| Task | Ended | Turns | Cost |
| --- | --- | --- | --- |
| apache/iceberg-python-3295 | correct | 7 | $0.11 |
| astronomy-commons/lsdb-1349 | correct | 14 | $0.23 |
| copier-org/copier-2646 | correct | 8 | $0.08 |
| cs-si/eodag-2176 | **wrong** | 6 | $0.05 |
| databricks/dbt-databricks-1428 | **wrong** | 16 | $0.15 |
| graphistry/pygraphistry-1277 | correct | 24 | $0.21 |
| hkuds/openharness-217 | **wrong** | 7 | $0.06 |
| nesquena/hermes-webui-2056 | **wrong** | 8 | $0.06 |
| python-wheel-build/fromager-1124 | **wrong** | 17 | $0.14 |
| raullenchai/rapid-mlx-289 | correct | 14 | $0.15 |
| schemathesis/schemathesis-4087 | **wrong** (ran out of turns) | 41 | $0.66 |
| tox-dev/tox-3931 | correct | 6 | $0.06 |
| youssofal/mtplx-21 | correct | 10 | $0.07 |
| zarr-developers/virtualizarr-979 | correct | 23 | $0.14 |

The 14 runs cost $2.17 (mean $0.16, max $0.66). No agent read the lab.

## Checks on the grading

- **Every task's known-correct fix grades correct** under the same grading.
  So the six wrong results are the agent's, not the grader's.
- **Grading was fixed once, and every run graded again.** The first
  grading applied the hidden test patch over the agent's tree. Where the
  agent had edited the same test files, the patch did not apply and the
  run counted as wrong (pygraphistry, virtualizarr). Grading now puts those
  files back to the baseline first, as SWE-bench does. All 14 runs were
  graded again from their saved trees, with no new agent runs; both runs
  are now correct. The first grading is kept in `runs-before-regrade.jsonl`.
- **Refused commands do not explain the failures.** Every run had 1 to 3
  shell commands refused by the restriction, right and wrong runs alike. One
  wrong run (eodag) says it could not verify its fix because a command was
  refused, so the restriction may cost the agent a little.

## Next: the full trial on these 14

1. Draft rules for setup 4 from each task's issue text. `tracks/draft_rules.py`
   needs a small extension for real projects: the author answers from the
   hidden test patch, and the teeth check makes the modules the rules import
   useless.
2. Run the 4 setups × 3 runs on the 14 tasks, 168 runs. At this cost, about
   $25 to $40; runs that are sent back cost more.
3. Report against the proposal's pass marks. The 6 tasks the agent got wrong
   unaided are where the setups can differ; the other 8 measure whether a
   checker blocks right work.
