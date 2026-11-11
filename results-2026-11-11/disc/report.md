# EMI evaluation report

## Discrimination: does `stop` mean the work is right?

| condition | catch rate (incorrect → not stop) | accept rate (correct → stop) | stop precision | feedback names the defect | median s |
|---|---|---|---|---|---|
| tests_only | 20% (9/46; 11–33) | 96% (24/25; 80–99) | 39% (24/61; 28–52) | 100% (7/7; 65–100) | 6.7 |
| strict | 41% (19/46; 28–56) | 44% (11/25; 27–63) | 29% (11/38; 17–45) | 100% (10/10; 72–100) | 6.4 |
| laws | 67% (28/42; 52–79) | 96% (22/23; 79–99) | 61% (22/36; 45–75) | 100% (9/9; 70–100) | 8.1 |
| laws_adequacy | 76% (32/42; 61–87) | 70% (16/23; 49–84) | 62% (16/26; 43–78) | 100% (9/9; 70–100) | 10.3 |
| preserve | 100% (4/4; 51–100) | 100% (2/2; 34–100) | 100% (2/2; 34–100) | 100% (4/4; 51–100) | 4.5 |

Comparison gates on the same candidates:

| condition set | gate | catch | accept |
|---|---|---|---|
| tests_only | naive_ci | 15% (7/46; 8–28) | 100% (25/25; 87–100) |
| tests_only | restore | 20% (9/46; 11–33) | 96% (24/25; 80–99) |
| tests_only | restore_laws | 67% (28/42; 52–79) | 96% (22/23; 79–99) |
| strict | naive_ci | 15% (7/46; 8–28) | 100% (25/25; 87–100) |
| strict | restore | 20% (9/46; 11–33) | 96% (24/25; 80–99) |
| strict | restore_laws | 67% (28/42; 52–79) | 96% (22/23; 79–99) |
| laws | naive_ci | 14% (6/42; 7–28) | 100% (23/23; 86–100) |
| laws | restore | 19% (8/42; 10–33) | 96% (22/23; 79–99) |
| laws | restore_laws | 67% (28/42; 52–79) | 96% (22/23; 79–99) |
| laws_adequacy | naive_ci | 14% (6/42; 7–28) | 100% (23/23; 86–100) |
| laws_adequacy | restore | 19% (8/42; 10–33) | 96% (22/23; 79–99) |
| laws_adequacy | restore_laws | 67% (28/42; 52–79) | 96% (22/23; 79–99) |
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
| partial | careless | 11/12 | 11/12 | 5/12 | 5/12 | – | 12/12 |
| regress_covered | careless | 0/5 | 0/5 | 0/5 | 0/5 | – | 0/5 |
| regress_silent | careless | 6/6 | 4/6 | 5/6 | 2/6 | – | 6/6 |
| stale_test | careless | 0/1 | 0/1 | 0/1 | 0/1 | – | 0/1 |
| swallow | careless | 1/1 | 1/1 | 1/1 | 0/1 | – | 1/1 |
| wrong_test | careless | 5/5 | 5/5 | 2/5 | 2/5 | – | 5/5 |
| gold | correct | 8/8 | 8/8 | 8/8 | 6/8 | – | 8/8 |
| gold_appended | correct | 3/3 | 2/3 | 3/3 | 2/3 | – | 3/3 |
| gold_comment | correct | 1/1 | 1/1 | 1/1 | 1/1 | – | 1/1 |
| gold_edits_test | correct | 0/1 | 0/1 | 0/1 | 0/1 | – | 1/1 |
| gold_notest | correct | 7/7 | 0/7 | 7/7 | 5/7 | – | 7/7 |
| gold_redundant | correct | 3/3 | 0/3 | 3/3 | 2/3 | – | 3/3 |
| gold_refactor | correct | 2/2 | 0/2 | – | – | 2/2 | 2/2 |

### Incorrect work that still gets `stop` under the strongest condition

- **t01_slugify/forgets_sep** (partial, laws_adequacy): check_slug.py::test_custom_separator: failed: AssertionError:  @ check_slug.py:26
- **t01_slugify/drops_digits** (wrong_test, laws_adequacy): check_slug.py::test_digits_kept: failed: AssertionError:  @ check_slug.py:29
- **t03_business_days/generator_consumed** (partial, laws_adequacy): check_calendar.py::test_holidays_list_set_and_generator: failed: AssertionError:  @ check_calendar.py:11
- **t03_business_days/subtracts_all_holidays** (partial, laws_adequacy): check_calendar.py::test_weekend_holiday_not_double_counted: failed: AssertionError:  @ check_calendar.py:14
- **t04_order_cancel/cancels_shipped** (partial, laws_adequacy): check_orders.py::test_cancel_shipped_raises: failed: AssertionError: did not raise OrderError @ check_orders.py:9
- **t04_order_cancel/wrong_exception** (wrong_test, laws_adequacy): check_orders.py::test_cancel_shipped_raises: failed: AssertionError: raised ValueError, expected OrderError @ check_orders.py:8
- **t04_order_cancel/drops_pay_history** (regress_silent, laws_adequacy): check_orders.py::test_cancel_paid: failed: AssertionError:  @ check_orders.py:19; check_orders.py::test_history_of_old_operations: failed: AssertionError:  @ check_orders.py:35
- **t07_backoff_cap/cap_only** (partial, laws_adequacy): check_retry.py::test_negative_raises: failed: AssertionError: did not raise ValueError @ check_retry.py:9
- **t09_semver/no_padding** (boundary, laws_adequacy): check_semver.py::test_missing_components: failed: AssertionError:  @ check_semver.py:11
- **t10_median/sorts_in_place** (regress_silent, laws_adequacy): check_stats.py::test_does_not_mutate: failed: AssertionError:  @ check_stats.py:24; check_stats.py::test_tuple_input: failed: AttributeError: 'tuple' object has no attribute 'sort' @ stats.py:10

### Correct work EMI did not let finish

- t01_slugify/gold_notest (gold_notest, strict) → **repair**: No proving test runs textutil.py:slugify (line 5); add a test that fails without your change.
- t01_slugify/gold_redundant (gold_redundant, strict) → **repair**: tests/test_slug_new.py::test_lower passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_notest (gold_notest, strict) → **repair**: No proving test runs billing.py:_dec (line 6); add a test that fails without your change.
- t02_invoice_rounding/gold_redundant (gold_redundant, strict) → **repair**: tests/test_billing_more.py::test_two_lines passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t02_invoice_rounding/gold_notest (gold_notest, laws_adequacy) → **repair**: billing.py:17 in invoice_total: changing `*` to `/` breaks no proving test or law; add a test that fails when that line goes wrong.
- t02_invoice_rounding/gold_redundant (gold_redundant, laws_adequacy) → **repair**: billing.py:17 in invoice_total: changing `*` to `/` breaks no proving test or law; add a test that fails when that line goes wrong.
- t03_business_days/gold_notest (gold_notest, strict) → **repair**: No proving test runs calendar_utils.py:business_days (line 4); add a test that fails without your change.
- t04_order_cancel/gold_notest (gold_notest, strict) → **repair**: No proving test runs orders.py:cancel (line 32); add a test that fails without your change.
- t05_kv_quotes/gold_notest (gold_notest, strict) → **repair**: No proving test runs kvparse.py:_segments (line 1); add a test that fails without your change.
- t05_kv_quotes/gold (gold, laws_adequacy) → **repair**: kvparse.py:31 in _strip: changing `==` to `!=` breaks no proving test or law; add a test that fails when that line goes wrong.
- t06_lru_recency/gold_redundant (gold_redundant, strict) → **repair**: tests/test_lru_more.py::test_len passes without your change, so it does not show the change works; make it fail on the old code, or remove it.
- t05_kv_quotes/gold_notest (gold_notest, laws_adequacy) → **repair**: kvparse.py:31 in _strip: changing `==` to `!=` breaks no proving test or law; add a test that fails when that line goes wrong.
- t06_lru_recency/gold_notest (gold_notest, strict) → **repair**: No proving test runs lru.py:get (line 9); add a test that fails without your change.
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, tests_only) → **ask_person**: waits for approval: old-test:tests/test_retry.py
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, strict) → **ask_person**: waits for approval: old-test:tests/test_retry.py
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, laws) → **ask_person**: waits for approval: old-test:tests/test_retry.py
- t07_backoff_cap/gold_updates_old_test (gold_edits_test, laws_adequacy) → **ask_person**: waits for approval: old-test:tests/test_retry.py
- t08_pricing_refactor/gold (gold_refactor, strict) → **repair**: No proving test runs pricing.py:_tier_discount (line 1); add a test that fails without your change.
- t08_pricing_refactor/gold_with_types_and_docs (gold_refactor, strict) → **repair**: No proving test runs pricing.py:_tier_discount (line 3); add a test that fails without your change.
- t09_semver/gold_appended (gold_appended, strict) → **repair**: No proving test runs versions.py:_ident (line 1); add a test that fails without your change.
- t09_semver/gold (gold, laws_adequacy) → **repair**: versions.py:8 in parse_version: changing `-` to `+` breaks no proving test or law; add a test that fails when that line goes wrong.
- t09_semver/gold_appended (gold_appended, laws_adequacy) → **repair**: versions.py:8 in parse_version: changing `-` to `+` breaks no proving test or law; add a test that fails when that line goes wrong.
- t10_median/gold_notest (gold_notest, strict) → **repair**: No proving test runs stats.py:median (line 7); add a test that fails without your change.
