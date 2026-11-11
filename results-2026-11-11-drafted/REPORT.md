# Drafted rules and type checkers on the 10 discrimination tasks

Run 2026-11-11. **Model note:** the owner asked for Opus 5.5 at medium effort.
The session was configured for Fable 5.2 at *high* effort. The setup (sandbox
check, EMI build, `validate`) ran on Fable 5.2; after that the session was
served by Opus 5.5, still at high effort. The five Drafter and Answerer
subagents ran on Opus at medium effort.

## In short

- A helper that **drafts rules from the request and the baseline alone** (A)
  caught **45 of 46** incorrect candidates and let **24 of 25** correct ones
  finish. The project's own tests (`tests_only`) catch 9 of 46. The
  hand-written laws (`laws`) catch 28 of 42, on the 9 tasks that have them.
- **Asking questions first** (B) also caught 45 of 46, but let only **21 of
  25** correct candidates finish. One drafted rule has an arithmetic mistake
  (`median([5, 5, 7, 9]) == 5`; the median is 6), and it blocks all three
  correct t10 candidates.
- Both A and B catch **all 10** of the candidates that slipped through
  hand-written laws.
- **Pass mark (set in advance): B catches at least 5 of the 10 slipped
  candidates and blocks no correct candidate. B did not pass.** It catches
  10 of 10, but it blocks 3 correct candidates through one wrong rule. A
  would have met the same mark.
- The questions added little. 22 of 29 answers were "doesn't matter". Every
  slipped candidate B caught, A had caught without asking. One answer led
  to a catch A missed (`t02/rounds_each_line`, rounding per line). B in turn
  missed a candidate A caught (`t01/breaks_truncate`), because the second
  Drafter wrote no rule about `truncate`. That difference is between two
  drafts, not something questions caused.
- **Type checkers** (mypy and pyright, default settings) flag 3 of 46
  incorrect and 1 of 25 correct candidates. They flag none of the 10 slipped
  candidates, and none of their messages is about the actual defect.
- Treat the drafted numbers as an upper bound, not a forecast; see "Limits"
  below. In particular, the same model family played every role, and
  possibly also wrote the suite.

## Setup

- `bwrap --ro-bind / / true` failed at first: bubblewrap was not installed.
  After `apt-get install bubblewrap` (0.9.0) it printed `sandbox-ok`.
- EMI from `https://github.com/amorfatii/EMI.git`, branch
  `claude/sweet-sagan-ynaksz`, **sha `cd14f5f06528022d190b5176ec6fc74d112c936f`**,
  Rust 1.98.1 via rustup, `cargo install --locked --path crates/emi-cli`.
- `python -m emi_evals validate --suite discrimination`: 81 rows, every
  label agrees with its oracle, every baseline is valid.
- `tests_only` and `laws` were rerun on this build for a like-for-like
  comparison. EMI's decision is the same as on 2026-11-11 for every
  candidate.
- Harness change: two conditions in `emi_evals/model.py`,
  `drafted_no_questions` and `drafted_questions`. Each is identical to `laws`
  except for which laws are installed. `scripts/run_drafted.py` swaps a
  task's laws in memory for the drafted files. Tasks, candidates, oracles,
  labels, existing laws and existing conditions are unchanged.
- `tracks/rebench.py` and `tracks/closed_loop.py` were not run.

## Measurement 1: questions and drafted rules

### How the roles were kept apart

Each role was a separate subagent with fresh context.

- **Drafter A** (two agents, tasks 1–5 and 6–10) saw only
  `roles/drafter_no_questions.md`, `roles/laws_format.md` and
  `inputs/drafter/<task>.md`: the request and the baseline files.
- **Drafter B, questions** (one agent) saw the same, with
  `roles/drafter_questions.md`. It asked 29 questions; for t06 and t08 it
  asked none, because it found nothing the request left open.
- **Answerer** (one agent) saw `roles/answerer.md`,
  `inputs/answerer/<task>.md` (the request and the hidden oracle) and the
  questions. It was told to pick a letter only when the oracle requires that
  behaviour, and otherwise to answer "doesn't matter".
- **Drafter B, rules** (two fresh agents) saw the request, the baseline, the
  questions and the answers.
- **Runner** (this session) saw everything and wrote no rules.

The subagents could technically have used every tool. They were told to read
only the named files. Their transcripts show they did: only `Read` calls on
those files, and `Write`/`Edit` calls inside their own output folder. There
were no shell, search or listing calls. Two B Drafters edited their own rule
files after writing them (comment escaping in t05, one t08 fix); one of them
said so.

### Catch and accept

| condition | tasks | catch (incorrect stopped) | accept (correct let finish) | restore_laws gate catch | gate accept |
|---|---|---|---|---|---|
| tests_only | all 10 | 9/46 | 24/25 | (restore: 9/46) | (24/25) |
| laws (hand-written) | 9 with laws | 28/42 | 22/23 | 30/42 | 22/23 |
| **A** drafted_no_questions | all 10 | **45/46** | **24/25** | 45/46 | 24/25 |
| A | 9 with laws | 41/42 | 22/23 | 41/42 | 22/23 |
| **B** drafted_questions | all 10 | **45/46** | **21/25** | 45/46 | 21/25 |
| B | 9 with laws | 41/42 | 19/23 | 41/42 | 19/23 |

With drafted laws, EMI's decision equals the `restore_laws` gate's decision
on every candidate. That gate restores the baseline's tests and runs them
plus the same laws with pytest.

The one incorrect candidate A lets through is `t02/rounds_each_line`; the
one B lets through is `t01/breaks_truncate`.

The correct candidate that every condition blocks, including `tests_only`,
is `t07/gold_updates_old_test`. It changes an old test, so EMI asks a person
to approve that change. No rule is involved.

### The 10 slipped candidates

| candidate | laws | A | rule in A that catches it | B | rule in B that catches it |
|---|---|---|---|---|---|
| t01/drops_digits | stop | repair | "For ASCII text, the slug is the lowercase alphanumeric runs joined by one separator, with no separator at either end." | repair | "For ASCII text, the slug is the lowercased alphanumeric runs joined by exactly one sep." |
| t01/forgets_sep | stop | repair | "A custom separator is used in place of '-', with the same collapsing and stripping." | repair | same rule as above, and "The sep parameter keeps working" |
| t03/generator_consumed | stop | repair | "Holidays may be given as any iterable: list, tuple, set, frozenset or generator." | repair | "Holidays may be any iterable of dates: … or a generator." |
| t03/subtracts_all_holidays | stop | repair | "Holidays on weekends or outside the range change nothing, and a repeated holiday is removed only once." (also a counting property) | repair | "Holidays on weekends or outside [start, end) do not change the count." |
| t04/cancels_shipped | stop | repair | "Cancelling a shipped order raises OrderError and leaves the order as it was." (also the state machine) | repair | "Cancelling a shipped order raises OrderError and leaves the order completely unchanged." (from Q3) |
| t04/drops_pay_history | stop | repair | "Paying then shipping still works …" and the state machine | repair | "Cancelling a paid order sets … history ['paid', 'cancelled']." (from Q2), and others |
| t04/wrong_exception | stop | repair | "Cancelling a shipped order raises OrderError …" | repair | same as cancels_shipped (from Q3) |
| t07/cap_only | stop | repair | "A negative number of attempts raises ValueError instead of returning []." | repair | "A negative number of attempts raises ValueError, with or without max_delay." |
| t09/no_padding | stop | repair | "Missing components count as 0." (also a generated-versions property) | repair | "Missing components count as 0." |
| t10/sorts_in_place | stop | repair | "median does not modify the list it is given." | repair | "median does not modify the list it is given." (also the wrong rule below) |

**A catches 10 of 10. B catches 10 of 10.** Most of these come straight from a
sentence in the request, or from "keep what the baseline does": digits,
custom separators, "any iterable", "returns 3 → 2.5" with the list left
alone. The hand-written laws mostly checked the one example in the request.
The drafts also checked the other cases the request names.
`tables.md`, Table 2, lists every failing rule per candidate.

### Correct candidates blocked, and wrong rules

- **A: 0 wrong rules.** It blocks one correct candidate, the t07 old-test
  approval described above, which every condition blocks.
- **B: 1 wrong rule**, in `laws/drafted_questions/t10_median/test_median_laws.py`:

  ```python
  # The median of [1, 2, 3, 4] is 2.5, the mean of the two middle values.
  # Source: "median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values."
  def test_request_example():
      ...
      assert median([5, 5, 7, 9]) == 5
  ```

  The sentence it came from is right; the Drafter's arithmetic is wrong. The
  rule blocks `t10/gold`, `t10/gold_notest` and `t10/gold_with_docstring`.
  EMI's repair message would send a correct agent off to make `median`
  return 5. The vacuity check also caught it (it fails on gold). A helper
  could therefore have caught it before the person approved, by running each
  drafted rule against the person's own reference answer, if they have one.

### B: what the questions did

29 questions were asked. 7 got a letter and 22 got "doesn't matter". **All 7
lettered answers led to a rule**, and no rule was written for a
"doesn't matter" answer.

| task | lettered answer | rule it led to | did that rule change a decision? |
|---|---|---|---|
| t01 | Q1 A: "!!! ???" gives "" | `test_nothing_alphanumeric_gives_empty_string` | no |
| t02 | Q1 A: round once, on the total | `test_rounding_happens_once_on_the_total`, `test_untaxed_total_is_exact_sum_rounded_half_up` | **yes: catches `rounds_each_line`, which A misses** |
| t02 | Q5 A: always two decimal places | `test_result_always_has_two_places` | no (others catch the same candidates) |
| t04 | Q1 A: history ['cancelled'] | `test_cancel_open_order` | no |
| t04 | Q2 A: history ['paid', 'cancelled'] | `test_cancel_paid_order` | catches `drops_pay_history`, which A also caught |
| t04 | Q3 A: a refused cancel leaves the order unchanged | `test_cancel_shipped_order_raises_and_changes_nothing` | in B it is the only rule catching `cancels_shipped` and `wrong_exception`; A caught both without questions |
| t07 | Q1 A: max_delay=0 gives [0, 0, 0] | `test_zero_cap_gives_zeros` | no (`falsy_cap` was caught anyway) |

Did a question touch what each slipped candidate gets wrong? (This is the
runner's judgment.)

| slipped candidate | question touching its case | answer |
|---|---|---|
| t01/drops_digits | none (no question about digits) | – |
| t01/forgets_sep | none (Q3 asks about `sep=''`, not stripping a custom separator) | – |
| t03/generator_consumed | none | – |
| t03/subtracts_all_holidays | Q2 (a holiday listed twice: this candidate removes it twice) | doesn't matter (the oracle does not test duplicates) |
| t04/cancels_shipped | Q3 | A |
| t04/drops_pay_history | Q2 | A |
| t04/wrong_exception | Q3, indirectly (it presupposes OrderError) | A |
| t07/cap_only | none (the request already settles it) | – |
| t09/no_padding | none (the request already settles it) | – |
| t10/sorts_in_place | none | – |

So questions touched 4 of the 10, and an answer led to the catching rule for
3 of them, all in t04. A caught those 3 without questions. The Drafter's
questions went mostly to cases the oracle does not care about: datetime
holidays, quoted keys, build metadata, Decimal medians. That is why 22
answers were "doesn't matter". In this suite, what the slipped candidates
get wrong is mostly already written in the request. The hand-written laws
checked less of it; the drafted laws checked it whether or not anyone
asked.

### Rules per task, vacuous rules, time

Each cell shows: rules / vacuous / not about the function under test at all.
A rule is **vacuous** if it still passes when a function it depends on is
replaced by one of EMI's four trivial bodies (return the first argument,
return `None`, return the annotation default, raise `NotImplementedError`).
The check runs on the gold tree (`scripts/vacuity.py`).

| task | hand-written | A | B |
|---|---|---|---|
| t01_slugify | 2 / 1 / 0 | 7 / 1 / 1 | 6 / 2 / 0 |
| t02_invoice_rounding | 2 / 0 / 0 | 6 / 0 / 0 | 7 / 0 / 0 |
| t03_business_days | 3 / 2 / 0 | 6 / 0 / 0 | 7 / 1 / 0 |
| t04_order_cancel | 1 / 0 / 0 | 7 / 1 / 1 | 6 / 0 / 0 |
| t05_kv_quotes | 2 / 0 / 0 | 8 / 0 / 0 | 8 / 0 / 0 |
| t06_lru_recency | 1 / 0 / 0 | 5 / 0 / 1 | 5 / 0 / 1 |
| t07_backoff_cap | 1 / 0 / 0 | 5 / 1 / 0 | 6 / 1 / 0 |
| t08_pricing_refactor | – | 4 / 0 / 0 | 4 / 0 / 0 |
| t09_semver | 2 / 1 / 0 | 5 / 0 / 0 | 7 / 0 / 0 |
| t10_median | 1 / 0 / 0 | 5 / 1 / 0 | 7 / 1 / 1, plus 1 failing on gold |
| **total** | **15 / 4 / 0** | **58 / 4 / 3** | **63 / 5 / 2** |

The vacuous rules are the expected kind. "`!!!` gives `''`" is satisfied by
`return ""`. "Zero attempts gives `[]`" is satisfied by `return []`. "Does
not modify its input" is satisfied by `return None`. They are true and
cheap, and each is useful only next to a stronger rule. The rules that are
not about the function under test protect other code (for example
`truncate` unchanged, pay/ship unchanged, the capacity check). The
hand-written laws have a similar share of vacuous rules (4 of 15).

**Time per check** (`emi done`, seconds). The main runs shared 4 cores, so
their times are inflated. The timing pass ran each task's gold candidate
alone, one at a time:

| condition | timing pass median | main run median |
|---|---|---|
| tests_only | 6.9 | 9.0 |
| laws | 9.5 | 15.1 |
| A | 9.8 | 25.6 |
| B | 10.3 | 18.9 |

Four times as many rules as the hand-written laws add well under a second
per check.

## Measurement 2: type checkers

mypy 2.4.1 and pyright 1.1.414, default settings, in a scratch environment
with pytest and hypothesis installed. Both ran on each baseline and each
candidate tree (product code and tests). An error counts as new when its
(checker, file, code, message) appears more often than at the baseline;
line numbers are ignored because they move. Only t06's baseline has errors
(2 mypy annotation hints).

| | correct flagged | incorrect flagged |
|---|---|---|
| mypy | 0/25 | 1/46 |
| pyright | 1/25 | 2/46 |
| either | **1/25** | **3/46** |

Incorrect candidates flagged:

- `t02/bankers_rounding` and `t02/rounds_each_line`, by pyright, in the
  candidate's *test* file: `Argument of type "Literal['0.2']" cannot be
  assigned to parameter "tax_rate" of type "int"`. The correct `t02/gold`
  gets the same error. The signature `tax_rate=0` makes pyright infer
  `int`, and the request says the rate may be a string. This is noise, not a
  defect signal.
- `t05/swallows_unterminated`, by mypy: `Need type annotation for "out"`.
  This is an annotation hint about where a variable is defined, not about
  swallowing the error.

None of the 10 slipped candidates is flagged. With default settings, type
checkers catch none of the defects in this suite.

## Other observations

- In this rerun the `restore_laws` gate with the hand-written laws caught
  30/42, two more than EMI (`t04/cancels_shipped`, `t04/wrong_exception`).
  On 2026-11-11 it caught 28. The gate runs Hypothesis with fresh random
  inputs, and this time the hand-written state machine happened to draw
  pay → ship → cancel. EMI's inputs are fixed and seeded, and they did not
  draw it. The extra catches are luck: the next run may not find them.
- With drafted laws, EMI and the `restore_laws` gate agree on every
  candidate. As on 2026-11-11, what decides the outcome is which laws exist,
  not EMI's extra machinery.

## Limits

- **The Answerer saw the oracle.** It answered exactly what the hidden
  checks require, and "doesn't matter" everywhere else. A real person
  answers from memory and intent; they may pick a wrong letter, or pick a
  letter where "doesn't matter" was true, and a rule written from that
  answer would block correct work. These answers are a best case.
- **One model played both sides.** The Drafter and the Answerer are the same
  model family, so they share assumptions. That family may also have
  written the tasks and the incorrect candidates; I could not confirm who
  did. If it did, the Drafter may be good at anticipating exactly the
  mistakes planted in this suite ("works only for the example", "forgets
  the generator"). That would make A and B look better here than they would
  against another agent's real mistakes.
- **One draft per condition.** Each set was drafted once. The two misses
  differ between A and B because two drafters made different choices, not
  because of the questions. A rerun could give different rules, more or
  fewer wrong rules, and different catches. B's arithmetic slip shows that
  a single bad line can decide the pass mark.
- **Small, known numbers.** 46 incorrect and 25 correct candidates, written
  together with the oracles. 45/46 does not mean drafted rules catch 98% of
  real incorrect work.
- **The drafts are larger.** 58–63 rules against 15 hand-written ones. The
  hand-written laws may be deliberately minimal. The comparison is between
  "a few rules a person wrote" and "many rules a helper drafted", not
  between equal efforts.
- **Some steps did not follow the plan exactly.** Two B Drafters edited
  their own files after writing them. One B Drafter put the state machine's
  comment above the `TestX = X.TestCase` line, not the class. A rule counts
  as one test function: a parametrized test and a state machine are one
  rule each. That is why the counts here differ a little from the agents'
  own counts.
- **The timing pass is one candidate per task.**

## Files

- `REPORT.md`: this report. `tables.md`: every table, made by `scripts/tables.py`.
- `roles/`: the role instructions and the rules format each subagent was given.
- `inputs/drafter/`, `inputs/answerer/`: exactly what each role saw
  (`scripts/make_packets.py`).
- `questions/`, `answers/`: every question and answer.
- `laws/drafted_no_questions/<task>/`, `laws/drafted_questions/<task>/`:
  the rule files, unedited by the runner.
- `raw/<condition>/results.jsonl`, `truth.jsonl`, `run.log`: EMI's
  decision with the full receipt, and the oracle truth with the gates, per
  candidate. `raw/tests_only_and_laws/` is the rerun on this build.
- `raw/vacuity.jsonl`, `raw/typecheck.jsonl`, `raw/timing/`.
- `scripts/`: `run_drafted.py` (the new conditions), `vacuity.py`,
  `typecheck.py`, `tables.py`, `make_packets.py`.

## Reproduce

From the repository root, with `emi` built from the sha above:

```bash
python -m emi_evals run --suite discrimination --emi $(which emi) --work /tmp/work/base --out results-2026-11-11-drafted/raw/tests_only_and_laws --conditions tests_only laws --fresh --jobs 4
```

```bash
python results-2026-11-11-drafted/scripts/run_drafted.py drafted_no_questions --emi $(which emi) --work /tmp/work/dnq --out results-2026-11-11-drafted/raw/drafted_no_questions
```

```bash
python results-2026-11-11-drafted/scripts/run_drafted.py drafted_questions --emi $(which emi) --work /tmp/work/dq --out results-2026-11-11-drafted/raw/drafted_questions
```

```bash
python results-2026-11-11-drafted/scripts/vacuity.py /tmp/work/base/venv/bin/python /tmp/work/vac > results-2026-11-11-drafted/raw/vacuity.jsonl
```

```bash
python results-2026-11-11-drafted/scripts/tables.py > results-2026-11-11-drafted/tables.md
```

The type checkers need mypy, pyright, pytest and hypothesis on `PATH` (see
the docstring in `scripts/typecheck.py`).
