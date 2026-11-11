# EMI evaluation report

## Discrimination: does `stop` mean the work is right?

| condition | catch rate (incorrect → not stop) | accept rate (correct → stop) | stop precision | feedback names the defect | median s |
|---|---|---|---|---|---|
| tests_only | 20% (9/46; 11–33) | 84% (21/25; 65–94) | 36% (21/58; 25–49) | 100% (7/7; 65–100) | 6.0 |
| strict | 41% (19/46; 28–56) | 40% (10/25; 23–59) | 27% (10/37; 15–43) | 100% (10/10; 72–100) | 6.1 |
| laws | 67% (28/42; 52–79) | 83% (19/23; 63–93) | 58% (19/33; 41–73) | 100% (9/9; 70–100) | 11.0 |
| laws_adequacy | 83% (35/42; 69–92) | 52% (12/23; 33–71) | 63% (12/19; 41–81) | 100% (9/9; 70–100) | 15.4 |
| preserve | 100% (4/4; 51–100) | 100% (2/2; 34–100) | 100% (2/2; 34–100) | 100% (4/4; 51–100) | 4.9 |

Comparison gates on the same candidates:

| condition set | gate | catch | accept |
|---|---|---|---|
| tests_only | naive_ci | 15% (7/46; 8–28) | 100% (25/25; 87–100) |
| tests_only | restore | 20% (9/46; 11–33) | 96% (24/25; 80–99) |
| tests_only | restore_laws | 71% (30/42; 56–83) | 96% (22/23; 79–99) |
| strict | naive_ci | 15% (7/46; 8–28) | 100% (25/25; 87–100) |
| strict | restore | 20% (9/46; 11–33) | 96% (24/25; 80–99) |
| strict | restore_laws | 71% (30/42; 56–83) | 96% (22/23; 79–99) |
| laws | naive_ci | 14% (6/42; 7–28) | 100% (23/23; 86–100) |
| laws | restore | 19% (8/42; 10–33) | 96% (22/23; 79–99) |
| laws | restore_laws | 71% (30/42; 56–83) | 96% (22/23; 79–99) |
| laws_adequacy | naive_ci | 14% (6/42; 7–28) | 100% (23/23; 86–100) |
| laws_adequacy | restore | 19% (8/42; 10–33) | 96% (22/23; 79–99) |
| laws_adequacy | restore_laws | 71% (30/42; 56–83) | 96% (22/23; 79–99) |
| preserve | naive_ci | 25% (1/4; 5–70) | 100% (2/2; 34–100) |
| preserve | restore | 25% (1/4; 5–70) | 100% (2/2; 34–100) |

### Slip rate by failure mode (stop / candidates)

| mode | family | tests_only | strict | laws | laws_adequacy | preserve | naive CI accepts |
|---|---|---|---|---|---|---|---|
| behaviour_drift | careless | 3/4 | 0/4 | – | – | 0/4 | 3/4 |
| boundary | careless | 3/4 | 3/4 | 1/4 | 1/4 | – | 4/4 |
| dead_code | careless | 1/1 | 0/1 | 0/1 | 0/1 | – | 1/1 |
| hardcode | careless | 3/3 | 3/3 | 0/3 | 0/3 | – | 3/3 |
| noop | careless | 4/4 | 0/4 | 0/4 | 0/4 | – | 4/4 |
| partial | careless | 11/12 | 11/12 | 5/12 | 4/12 | – | 12/12 |
| regress_covered | careless | 0/5 | 0/5 | 0/5 | 0/5 | – | 0/5 |
| regress_silent | careless | 6/6 | 4/6 | 5/6 | 1/6 | – | 6/6 |
| stale_test | careless | 0/1 | 0/1 | 0/1 | 0/1 | – | 0/1 |
| swallow | careless | 1/1 | 1/1 | 1/1 | 0/1 | – | 1/1 |
| wrong_test | careless | 5/5 | 5/5 | 2/5 | 1/5 | – | 5/5 |
| gold | correct | 8/8 | 8/8 | 8/8 | 4/8 | – | 8/8 |
| gold_appended | correct | 3/3 | 2/3 | 3/3 | 2/3 | – | 3/3 |
| gold_comment | correct | 1/1 | 0/1 | 1/1 | 1/1 | – | 1/1 |
| gold_edits_test | correct | 0/1 | 0/1 | 0/1 | 0/1 | – | 1/1 |
| gold_notest | correct | 7/7 | 0/7 | 7/7 | 5/7 | – | 7/7 |
| gold_redundant | correct | 0/3 | 0/3 | 0/3 | 0/3 | – | 3/3 |
| gold_refactor | correct | 2/2 | 0/2 | – | – | 2/2 | 2/2 |

### Incorrect work that still gets `stop` under the strongest condition

- **t01_slugify/forgets_sep** (partial, laws_adequacy): check_slug.py::test_custom_separator: failed: AssertionError:  @ check_slug.py:26
- **t01_slugify/drops_digits** (wrong_test, laws_adequacy): check_slug.py::test_digits_kept: failed: AssertionError:  @ check_slug.py:29
- **t03_business_days/generator_consumed** (partial, laws_adequacy): check_calendar.py::test_holidays_list_set_and_generator: failed: AssertionError:  @ check_calendar.py:11
- **t03_business_days/subtracts_all_holidays** (partial, laws_adequacy): check_calendar.py::test_weekend_holiday_not_double_counted: failed: AssertionError:  @ check_calendar.py:14
- **t07_backoff_cap/cap_only** (partial, laws_adequacy): check_retry.py::test_negative_raises: failed: AssertionError: did not raise ValueError @ check_retry.py:9
- **t09_semver/no_padding** (boundary, laws_adequacy): check_semver.py::test_missing_components: failed: AssertionError:  @ check_semver.py:11
- **t10_median/sorts_in_place** (regress_silent, laws_adequacy): check_stats.py::test_does_not_mutate: failed: AssertionError:  @ check_stats.py:24; check_stats.py::test_tuple_input: failed: AttributeError: 'tuple' object has no attribute 'sort' @ stats.py:10

### Correct work EMI did not let finish

- t01_slugify/gold_redundant (gold_redundant, tests_only) → **repair**: tests/test_slug_new.py::test_lower passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t01_slugify/gold_notest (gold_notest, strict) → **repair**: No proving test runs textutil.py:slugify (line 5); add a test that fails without your change.
- t01_slugify/gold_redundant (gold_redundant, strict) → **repair**: tests/test_slug_new.py::test_lower passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t01_slugify/gold_redundant (gold_redundant, laws) → **repair**: tests/test_slug_new.py::test_lower passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t01_slugify/gold_redundant (gold_redundant, laws_adequacy) → **repair**: tests/test_slug_new.py::test_lower passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_redundant (gold_redundant, tests_only) → **repair**: tests/test_billing_more.py::test_two_lines passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_notest (gold_notest, strict) → **repair**: No proving test runs billing.py:_dec (line 6); add a test that fails without your change.
- t02_invoice_rounding/gold_redundant (gold_redundant, strict) → **repair**: tests/test_billing_more.py::test_two_lines passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_redundant (gold_redundant, laws) → **repair**: tests/test_billing_more.py::test_two_lines passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_notest (gold_notest, laws_adequacy) → **repair**: billing.py:17 in invoice_total: changing `*` to `/` breaks no proving test or law; add a test that fails when that line goes wrong.
- t02_invoice_rounding/gold_redundant (gold_redundant, laws_adequacy) → **repair**: tests/test_billing_more.py::test_two_lines passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t03_business_days/gold_notest (gold_notest, strict) → **repair**: No proving test runs calendar_utils.py:business_days (line 4); add a test that fails without your change.
- t04_order_cancel/gold_notest (gold_notest, strict) → **repair**: No proving test runs orders.py:cancel (line 32); add a test that fails without your change.
- t04_order_cancel/gold (gold, laws_adequacy) → **repair**: tests/test_cancel.py:10 in test_cancel_paid_refunds: changing `and` to `or` breaks no proving test or law; add a test that fails when that line goes wrong.
- t05_kv_quotes/gold_notest (gold_notest, strict) → **repair**: No proving test runs kvparse.py:_segments (line 1); add a test that fails without your change.
- t05_kv_quotes/gold (gold, laws_adequacy) → **repair**: kvparse.py:31 in _strip: changing `==` to `!=` breaks no proving test or law; add a test that fails when that line goes wrong.
- t05_kv_quotes/gold_notest (gold_notest, laws_adequacy) → **repair**: kvparse.py:31 in _strip: changing `==` to `!=` breaks no proving test or law; add a test that fails when that line goes wrong.
- t06_lru_recency/gold_redundant (gold_redundant, tests_only) → **repair**: tests/test_lru_more.py::test_len passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t06_lru_recency/gold_redundant (gold_redundant, strict) → **repair**: tests/test_lru_more.py::test_len passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t06_lru_recency/gold_notest (gold_notest, strict) → **repair**: No proving test runs lru.py:get (line 9); add a test that fails without your change.
- t06_lru_recency/gold_redundant (gold_redundant, laws) → **repair**: tests/test_lru_more.py::test_len passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t06_lru_recency/gold (gold, laws_adequacy) → **repair**: tests/test_lru_recency.py:9 in test_get_refreshes: changing `and` to `or` breaks no proving test or law; add a test that fails when that line goes wrong.
- t06_lru_recency/gold_redundant (gold_redundant, laws_adequacy) → **repair**: tests/test_lru_more.py::test_len passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, tests_only) → **ask_person**: No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them.
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, strict) → **ask_person**: No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them.
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, laws) → **ask_person**: 1 law(s) hold on sampled inputs, not on every input: no counterexample among them is evidence, not a proof: .emi/laws/test_retry_laws.py::test_never_above_the_cap_and_never_shrinking (100 sampled inputs).
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, laws_adequacy) → **ask_person**: 1 law(s) hold on sampled inputs, not on every input: no counterexample among them is evidence, not a proof: .emi/laws/test_retry_laws.py::test_never_above_the_cap_and_never_shrinking (100 sampled inputs).
- t08_pricing_refactor/gold (gold_refactor, strict) → **repair**: No proving test runs pricing.py:_tier_discount (line 1); add a test that fails without your change.
- t08_pricing_refactor/gold_with_types_and_docs (gold_refactor, strict) → **repair**: No proving test runs pricing.py:_tier_discount (line 3); add a test that fails without your change.
- t09_semver/gold_appended (gold_appended, strict) → **repair**: No proving test runs versions.py:_ident (line 1); add a test that fails without your change.
- t09_semver/gold (gold, laws_adequacy) → **repair**: versions.py:8 in parse_version: changing `-` to `+` breaks no proving test or law; add a test that fails when that line goes wrong.
- t09_semver/gold_appended (gold_appended, laws_adequacy) → **repair**: versions.py:8 in parse_version: changing `-` to `+` breaks no proving test or law; add a test that fails when that line goes wrong.
- t10_median/gold_notest (gold_notest, strict) → **repair**: No proving test runs stats.py:median (line 7); add a test that fails without your change.
- t10_median/gold_with_docstring (gold_comment, strict) → **repair**: No proving test runs stats.py:mean (line 1); add a test that fails without your change.

### `every_input: true` reported on failing laws

- t01_slugify/hardcoded_example/laws: test_a_slug_is_clean
- t01_slugify/noop/laws: test_a_slug_is_clean
- t01_slugify/hardcoded_example/laws_adequacy: test_a_slug_is_clean
- t01_slugify/noop/laws_adequacy: test_a_slug_is_clean
- t02_invoice_rounding/bankers_rounding/laws: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/rounds_each_line/laws: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/float_result/laws: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/noop/laws: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/bankers_rounding/laws_adequacy: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/rounds_each_line/laws_adequacy: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/float_result/laws_adequacy: test_total_is_the_exact_sum_rounded_half_up
- t02_invoice_rounding/noop/laws_adequacy: test_total_is_the_exact_sum_rounded_half_up
- t03_business_days/inclusive_end/laws: test_ranges_add_up
- t03_business_days/inclusive_end/laws: test_reversing_the_range_negates
- t03_business_days/reversed_positive/laws: test_ranges_add_up
- t03_business_days/reversed_positive/laws: test_reversing_the_range_negates
- t03_business_days/inclusive_end/laws_adequacy: test_ranges_add_up
- t03_business_days/inclusive_end/laws_adequacy: test_reversing_the_range_negates
- t03_business_days/reversed_positive/laws_adequacy: test_ranges_add_up
- t03_business_days/reversed_positive/laws_adequacy: test_reversing_the_range_negates
- t04_order_cancel/no_refund/laws: runTest
- t04_order_cancel/not_idempotent/laws: runTest
- t04_order_cancel/no_refund/laws_adequacy: runTest
- t04_order_cancel/not_idempotent/laws_adequacy: runTest
- t05_kv_quotes/regex_no_escapes/laws: test_dump_then_parse_gives_back_the_dict
- t05_kv_quotes/keeps_empty_segments/laws: test_dump_then_parse_gives_back_the_dict
- t05_kv_quotes/hardcoded_example/laws: test_dump_then_parse_gives_back_the_dict
- t05_kv_quotes/regex_no_escapes/laws_adequacy: test_dump_then_parse_gives_back_the_dict
- t05_kv_quotes/keeps_empty_segments/laws_adequacy: test_dump_then_parse_gives_back_the_dict
- t05_kv_quotes/hardcoded_example/laws_adequacy: test_dump_then_parse_gives_back_the_dict
- t06_lru_recency/get_only/laws: runTest
- t06_lru_recency/miss_corrupts_order/laws: runTest
- t06_lru_recency/evicts_newest/laws: runTest
- t06_lru_recency/noop/laws: runTest
- t06_lru_recency/get_only/laws_adequacy: runTest
- t06_lru_recency/miss_corrupts_order/laws_adequacy: runTest
- t06_lru_recency/evicts_newest/laws_adequacy: runTest
- t06_lru_recency/noop/laws_adequacy: runTest
- t07_backoff_cap/falsy_cap/laws: test_never_above_the_cap_and_never_shrinking
- t07_backoff_cap/cap_before_scaling/laws: test_never_above_the_cap_and_never_shrinking
- t07_backoff_cap/falsy_cap/laws_adequacy: test_never_above_the_cap_and_never_shrinking
- t07_backoff_cap/cap_before_scaling/laws_adequacy: test_never_above_the_cap_and_never_shrinking
- t10_median/always_two_middle/laws: test_agrees_with_the_standard_library
- t10_median/hardcoded_example/laws: test_agrees_with_the_standard_library
- t10_median/floor_division/laws: test_agrees_with_the_standard_library
- t10_median/always_two_middle/laws_adequacy: test_agrees_with_the_standard_library
- t10_median/noop/laws: test_agrees_with_the_standard_library
- t10_median/hardcoded_example/laws_adequacy: test_agrees_with_the_standard_library
- t10_median/floor_division/laws_adequacy: test_agrees_with_the_standard_library
- t10_median/noop/laws_adequacy: test_agrees_with_the_standard_library
