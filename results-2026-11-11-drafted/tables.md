## Table 1. Catch and accept counts

Catch = incorrect candidates EMI did not let finish (anything but `stop`). Accept = correct candidates EMI let finish (`stop`). `restore_laws` = restore the baseline's tests, run them and the same laws with pytest; accept if both pass.

| condition | tasks | EMI catch | EMI accept | restore_laws catch | restore_laws accept | restore (no laws) catch | restore accept |
|---|---|---|---|---|---|---|---|
| tests_only | all 10 | 9/46 | 24/25 | – | – | 9/46 | 24/25 |
| tests_only | 9 with hand-written laws | 8/42 | 22/23 | – | – | 8/42 | 22/23 |
| laws (hand-written) | 9 with hand-written laws | 28/42 | 22/23 | 30/42 | 22/23 | 8/42 | 22/23 |
| A drafted_no_questions | all 10 | 45/46 | 24/25 | 45/46 | 24/25 | 9/46 | 24/25 |
| A drafted_no_questions | 9 with hand-written laws | 41/42 | 22/23 | 41/42 | 22/23 | 8/42 | 22/23 |
| B drafted_questions | all 10 | 45/46 | 21/25 | 45/46 | 21/25 | 9/46 | 24/25 |
| B drafted_questions | 9 with hand-written laws | 41/42 | 19/23 | 41/42 | 19/23 | 8/42 | 22/23 |

## Table 2. The 10 incorrect candidates that slipped under the strongest condition on 2026-11-11

| candidate | laws (this build) | A | rules in A that fail on it | B | rules in B that fail on it |
|---|---|---|---|---|---|
| t01_slugify/drops_digits | stop | **repair** | `test_ascii_runs_collapse_and_ends_are_stripped`: For ASCII text, the slug is the lowercase alphanumeric runs joined by one separator, with no separator at either end.<br>`test_custom_sep_collapses_and_strips`: A custom separator is used in place of '-', with the same collapsing and stripping. | **repair** | `test_ascii_text_is_runs_joined_by_one_sep`: For ASCII text, the slug is the lowercased alphanumeric runs joined by exactly one sep. |
| t01_slugify/forgets_sep | stop | **repair** | `test_custom_sep_collapses_and_strips`: A custom separator is used in place of '-', with the same collapsing and stripping.<br>`test_custom_sep_on_example`: A custom separator works on the request example. | **repair** | `test_ascii_text_is_runs_joined_by_one_sep`: For ASCII text, the slug is the lowercased alphanumeric runs joined by exactly one sep.<br>`test_sep_parameter_is_used`: The sep parameter keeps working: the collapsed separator is the given sep. |
| t03_business_days/generator_consumed | stop | **repair** | `test_any_iterable_of_holidays`: Holidays may be given as any iterable: list, tuple, set, frozenset or generator. | **repair** | `test_holidays_accepts_any_iterable`: Holidays may be any iterable of dates: list, tuple, set, frozenset or a generator. |
| t03_business_days/subtracts_all_holidays | stop | **repair** | `test_counts_and_antisymmetry`: For any start <= end and holidays, the result counts weekdays in [start, end) not in holidays; swapping the dates negates it.<br>`test_weekend_outside_and_duplicate_holidays`: Holidays on weekends or outside the range change nothing, and a repeated holiday is removed only once. | **repair** | `test_count_is_weekdays_minus_holidays`: For start <= end, the count is the weekdays in [start, end) that are not holidays.<br>`test_weekend_and_out_of_range_holidays_have_no_effect`: Holidays on weekends or outside [start, end) do not change the count. |
| t04_order_cancel/cancels_shipped | stop | **repair** | `TestOrderLifecycle`: Any sequence of pay, ship and cancel follows the order lifecycle, with failed calls raising OrderError and changing nothing.<br>`test_cancel_shipped_raises`: Cancelling a shipped order raises OrderError and leaves the order as it was. | **repair** | `test_cancel_shipped_order_raises_and_changes_nothing`: Cancelling a shipped order raises OrderError and leaves the order completely unchanged. |
| t04_order_cancel/drops_pay_history | stop | **repair** | `TestOrderLifecycle`: Any sequence of pay, ship and cancel follows the order lifecycle, with failed calls raising OrderError and changing nothing.<br>`test_pay_and_ship_unchanged`: Paying then shipping still works and unpaid orders still cannot ship. | **repair** | `TestOrderLifecycle`: Every sequence of pay, ship and cancel follows the requested lifecycle, with history per the answers.<br>`test_cancel_paid_order`: Cancelling a paid order sets status 'cancelled', refunded True, and history ['paid', 'cancelled'].<br>`test_cancel_shipped_order_raises_and_changes_nothing`: Cancelling a shipped order raises OrderError and leaves the order completely unchanged.<br>`test_cancel_twice_changes_nothing`: Cancelling a cancelled order changes nothing (no second history entry) and returns the order. |
| t04_order_cancel/wrong_exception | stop | **repair** | `TestOrderLifecycle`: Any sequence of pay, ship and cancel follows the order lifecycle, with failed calls raising OrderError and changing nothing.<br>`test_cancel_shipped_raises`: Cancelling a shipped order raises OrderError and leaves the order as it was. | **repair** | `test_cancel_shipped_order_raises_and_changes_nothing`: Cancelling a shipped order raises OrderError and leaves the order completely unchanged. |
| t07_backoff_cap/cap_only | stop | **repair** | `test_negative_attempts_raise`: A negative number of attempts raises ValueError instead of returning []. | **repair** | `test_negative_attempts_raise`: A negative number of attempts raises ValueError, with or without max_delay. |
| t09_semver/no_padding | stop | **repair** | `test_compare_matches_semver`: For generated versions, compare() agrees with semver precedence and returns only -1, 0 or 1, antisymmetrically.<br>`test_missing_components_are_zero`: Missing components count as 0. | **repair** | `test_compare_matches_precedence`: For any two well-formed versions, compare returns -1, 0 or 1 according to semver precedence.<br>`test_missing_components_are_zero`: Missing components count as 0. |
| t10_median/sorts_in_place | stop | **repair** | `test_median_does_not_mutate`: median does not modify the list it is given. | **repair** | `test_input_not_mutated`: median does not modify the list it is given.<br>`test_request_example`: The median of [1, 2, 3, 4] is 2.5, the mean of the two middle values. |

Caught out of 10: A drafted_no_questions 10, B drafted_questions 10.

## Table 3. Correct candidates not allowed to finish, and wrong rules

**laws (hand-written)**: 1 blocked.

- t07_backoff_cap/gold_updates_old_test → **ask_person**; failing rules: none; EMI says: 
- restore_laws gate rejects 1 correct: t07_backoff_cap/gold_updates_old_test (exit 1: 1 failed, 2 passed in 1.25s)

**A drafted_no_questions**: 1 blocked.

- t07_backoff_cap/gold_updates_old_test → **ask_person**; failing rules: none; EMI says: 
- restore_laws gate rejects 1 correct: t07_backoff_cap/gold_updates_old_test (exit 1: 1 failed, 2 passed in 1.11s)

**B drafted_questions**: 4 blocked.

- t07_backoff_cap/gold_updates_old_test → **ask_person**; failing rules: none; EMI says: 
- t10_median/gold → **repair**; failing rules: `test_median_laws.py::test_request_example`; EMI says: .emi/laws/test_median_laws.py::test_request_example is a law that does not hold yet; make the code satisfy it. It says: assert 6.0 == 5
 +  where 6.0 = median([5, 5, 7, 9])
- t10_median/gold_notest → **repair**; failing rules: `test_median_laws.py::test_request_example`; EMI says: .emi/laws/test_median_laws.py::test_request_example is a law that does not hold yet; make the code satisfy it. It says: assert 6.0 == 5
 +  where 6.0 = median([5, 5, 7, 9])
- t10_median/gold_with_docstring → **repair**; failing rules: `test_median_laws.py::test_request_example`; EMI says: .emi/laws/test_median_laws.py::test_request_example is a law that does not hold yet; make the code satisfy it. It says: assert 6.0 == 5
 +  where 6.0 = median([5, 5, 7, 9])
- restore_laws gate rejects 4 correct: t07_backoff_cap/gold_updates_old_test (exit 1: 1 failed, 2 passed in 0.50s); t10_median/gold (exit 1: 1 failed, 6 passed in 1.04s); t10_median/gold_notest (exit 1: 1 failed, 6 passed in 0.84s); t10_median/gold_with_docstring (exit 1: 1 failed, 6 passed in 1.06s)

**Wrong rules in A drafted_no_questions: 0**


**Wrong rules in B drafted_questions: 1**

- `t10_median/test_median_laws.py::test_request_example` (fails on gold, gold_notest, gold_with_docstring). Says: "The median of [1, 2, 3, 4] is 2.5, the mean of the two middle values." Came from: "median([1, 2, 3, 4]) returns 3. The median of an even number of values is the mean of the two middle values."

## Table 4. B: did a question touch the case each slipped candidate gets wrong?

| candidate | question that touches it | answer | caught by B? |
|---|---|---|---|
| t01_slugify/drops_digits | no question about digits | – | yes (repair) |
| t01_slugify/forgets_sep | Q3 asks about sep='' only, not whether a custom separator is stripped from the ends | – | yes (repair) |
| t03_business_days/generator_consumed | no question about holidays given as a generator | – | yes (repair) |
| t03_business_days/subtracts_all_holidays | Q2 (a holiday listed twice) separates it: this candidate counts the duplicate twice; answered "doesn't matter" | Q2: doesn't matter | yes (repair) |
| t04_order_cancel/cancels_shipped | Q3 asks what a refused cancel of a shipped order leaves behind | Q3: A | yes (repair) |
| t04_order_cancel/drops_pay_history | Q2 asks for the history after cancel(pay(order)): ['paid', 'cancelled'] | Q2: A | yes (repair) |
| t04_order_cancel/wrong_exception | Q3 presupposes OrderError on a shipped order; only indirectly | Q3: A | yes (repair) |
| t07_backoff_cap/cap_only | no question about negative attempts (the request already settles it) | – | yes (repair) |
| t09_semver/no_padding | Q4 is about extra components; padding is settled by the request | – | yes (repair) |
| t10_median/sorts_in_place | no question about changing the caller's list or tuple input | – | yes (repair) |

### Did each answer lead to a rule?

| task | question | answer | rules citing it |
|---|---|---|---|
| t01_slugify | Q1 | A | `test_nothing_alphanumeric_gives_empty_string` |
| t01_slugify | Q2 | doesn't matter | – |
| t01_slugify | Q3 | doesn't matter | – |
| t02_invoice_rounding | Q1 | A | `test_rounding_happens_once_on_the_total`, `test_untaxed_total_is_exact_sum_rounded_half_up` |
| t02_invoice_rounding | Q2 | doesn't matter | – |
| t02_invoice_rounding | Q3 | doesn't matter | – |
| t02_invoice_rounding | Q4 | doesn't matter | – |
| t02_invoice_rounding | Q5 | A | `test_result_always_has_two_places` |
| t03_business_days | Q1 | doesn't matter | – |
| t03_business_days | Q2 | doesn't matter | – |
| t03_business_days | Q3 | doesn't matter | – |
| t03_business_days | Q4 | doesn't matter | – |
| t04_order_cancel | Q1 | A | `test_cancel_open_order` |
| t04_order_cancel | Q2 | A | `test_cancel_paid_order` |
| t04_order_cancel | Q3 | A | `test_cancel_shipped_order_raises_and_changes_nothing` |
| t05_kv_quotes | Q1 | doesn't matter | – |
| t05_kv_quotes | Q2 | doesn't matter | – |
| t05_kv_quotes | Q3 | doesn't matter | – |
| t05_kv_quotes | Q4 | doesn't matter | – |
| t07_backoff_cap | Q1 | A | `test_zero_cap_gives_zeros` |
| t07_backoff_cap | Q2 | doesn't matter | – |
| t09_semver | Q1 | doesn't matter | – |
| t09_semver | Q2 | doesn't matter | – |
| t09_semver | Q3 | doesn't matter | – |
| t09_semver | Q4 | doesn't matter | – |
| t09_semver | Q5 | doesn't matter | – |
| t10_median | Q1 | doesn't matter | – |
| t10_median | Q2 | doesn't matter | – |
| t10_median | Q3 | doesn't matter | – |

29 questions; 7 answered with a letter, 22 "doesn't matter"; 7 led to a rule.

## Table 5. Rules per task, vacuous rules, check time

Cells: rules / vacuous / not depending on the function under test at all. Vacuous = still passes when a function it depends on is given a trivial body (EMI's four stand-ins).

| task | hand-written laws | A | B |
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
| t10_median | 1 / 0 / 0 | 5 / 1 / 0 | 7 / 1 / 1 (1 fail on gold) |
| **total** | **15 / 4 / 0** | **58 / 4 / 3** | **63 / 5 / 2** |

Vacuous rules, one by one:

- drafted_no_questions t01_slugify `test_slugify_laws.py::test_only_punctuation_gives_empty` passes under: slugify:returns_annotation_default
- drafted_questions t01_slugify `test_slugify_laws.py::test_any_text_has_no_separator_runs_or_ends` passes under: slugify:returns_annotation_default
- drafted_questions t01_slugify `test_slugify_laws.py::test_nothing_alphanumeric_gives_empty_string` passes under: slugify:returns_annotation_default
- laws t01_slugify `test_slug_laws.py::test_a_slug_is_clean` passes under: slugify:returns_annotation_default
- drafted_questions t03_business_days `test_business_days_laws.py::test_swapping_negates` passes under: business_days:returns_annotation_default
- laws t03_business_days `test_calendar_laws.py::test_ranges_add_up` passes under: business_days:returns_annotation_default
- laws t03_business_days `test_calendar_laws.py::test_reversing_the_range_negates` passes under: business_days:returns_annotation_default
- drafted_no_questions t04_order_cancel `test_order_cancel_laws.py::test_cancel_twice_changes_nothing` passes under: cancel:returns_first_argument
- drafted_no_questions t07_backoff_cap `test_backoff_cap_laws.py::test_zero_attempts_empty` passes under: backoff_delays:returns_annotation_default
- drafted_questions t07_backoff_cap `test_backoff_cap_laws.py::test_zero_attempts_empty` passes under: backoff_delays:returns_annotation_default
- laws t09_semver `test_semver_laws.py::test_antisymmetric` passes under: compare:returns_annotation_default
- drafted_no_questions t10_median `test_median_laws.py::test_median_does_not_mutate` passes under: median:returns_first_argument, median:returns_none
- drafted_questions t10_median `test_median_laws.py::test_input_not_mutated` passes under: median:returns_first_argument, median:returns_none

### How long a check takes

Seconds per `emi done`, median and 90th percentile. The main runs shared 4 cores with other runs (timings inflated). The timing pass ran each gold candidate alone, one at a time.

| condition | main run median | main run p90 | timing pass median (10 gold candidates, one at a time) |
|---|---|---|---|
| tests_only | 9.0 | 18.1 | 6.9 (n=10) |
| laws (hand-written) | 15.1 | 31.6 | 9.5 (n=9) |
| A drafted_no_questions | 25.6 | 35.0 | 9.8 (n=10) |
| B drafted_questions | 18.9 | 32.1 | 10.3 (n=10) |

## Table 6. Type checkers (mypy and pyright, default settings)

Baselines with errors: t06_lru_recency (2).

| checker | correct candidates flagged | incorrect candidates flagged |
|---|---|---|
| mypy | 0/25 | 1/46 |
| pyright | 1/25 | 2/46 |
| either | 1/25 | 3/46 |

Every flagged candidate and the new message:

- correct t02_invoice_rounding/gold: pyright `tests/test_billing_decimal.py:10` [reportArgumentType] Argument of type "Literal['0.2']" cannot be assigned to parameter "tax_rate" of type "int" in function "invoice_total"
  "Literal['0.2']" is not assignable to "int"
- incorrect t02_invoice_rounding/bankers_rounding: pyright `tests/test_billing_decimal.py:6` [reportArgumentType] Argument of type "Literal['0.2']" cannot be assigned to parameter "tax_rate" of type "int" in function "invoice_total"
  "Literal['0.2']" is not assignable to "int"
- incorrect t02_invoice_rounding/rounds_each_line: pyright `tests/test_billing_decimal.py:10` [reportArgumentType] Argument of type "Literal['0.2']" cannot be assigned to parameter "tax_rate" of type "int" in function "invoice_total"
  "Literal['0.2']" is not assignable to "int"
- incorrect t05_kv_quotes/swallows_unterminated: mypy `kvparse.py:43` [var-annotated] Need type annotation for "out" (hint: "out: dict[<type>, <type>] = ...")

Of the 10 slipped candidates, type checkers flag: none.
