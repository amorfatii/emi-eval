from datetime import date, timedelta

from hypothesis import given, strategies as st

from calendar_utils import business_days

BASE = date(2024, 1, 1)


def reference(start, end, holidays=()):
    hs = set(holidays)
    n = 0
    d = start
    while d < end:
        if d.weekday() < 5 and d not in hs:
            n += 1
        d += timedelta(days=1)
    return n


dates = st.integers(min_value=0, max_value=60).map(lambda k: BASE + timedelta(days=k))


# A holiday on a weekday inside the range is not counted.
# Source: "Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted"
def test_weekday_holiday_not_counted():
    assert business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 1)]) == 4
    assert business_days(
        date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 2), date(2024, 1, 5)]
    ) == 3


# Holidays on weekends or outside the range change nothing, and a repeated holiday is removed only once.
# Source: "whose days are not counted"
def test_weekend_outside_and_duplicate_holidays():
    start, end = date(2024, 1, 1), date(2024, 1, 8)
    assert business_days(start, end, holidays=[date(2024, 1, 6), date(2024, 1, 7)]) == 5
    assert business_days(start, end, holidays=[date(2023, 12, 29), date(2024, 1, 8)]) == 5
    assert business_days(start, end, holidays=[date(2024, 1, 3), date(2024, 1, 3)]) == 4


# Holidays may be given as any iterable: list, tuple, set, frozenset or generator.
# Source: "(any iterable of dates)"
def test_any_iterable_of_holidays():
    start, end = date(2024, 1, 1), date(2024, 1, 15)
    hs = [date(2024, 1, 2), date(2024, 1, 10)]
    assert business_days(start, end, holidays=list(hs)) == 8
    assert business_days(start, end, holidays=tuple(hs)) == 8
    assert business_days(start, end, holidays=set(hs)) == 8
    assert business_days(start, end, holidays=frozenset(hs)) == 8
    assert business_days(start, end, holidays=(h for h in hs)) == 8


# When end is before start the result is minus the count the other way round.
# Source: "when end < start return minus business_days(end, start) instead of 0"
def test_reversed_range_is_negative():
    assert business_days(date(2024, 1, 8), date(2024, 1, 1)) == -5
    assert business_days(date(2024, 1, 8), date(2024, 1, 1), holidays=[date(2024, 1, 3)]) == -4


# For any start <= end and holidays, the result counts weekdays in [start, end) not in holidays; swapping the dates negates it.
# Source: "whose days are not counted, and when end < start return minus business_days(end, start) instead of 0"
@given(dates, dates, st.lists(dates, max_size=8))
def test_counts_and_antisymmetry(a, b, holidays):
    start, end = min(a, b), max(a, b)
    expected = reference(start, end, holidays)
    assert business_days(start, end, holidays=list(holidays)) == expected
    if start != end:
        assert business_days(end, start, holidays=list(holidays)) == -expected
    else:
        assert business_days(end, start, holidays=list(holidays)) == 0


# Without holidays, forward ranges count weekdays in [start, end) as before.
# Source: baseline behaviour, not asked to change: business_days(start, end) counts weekdays in [start, end)
@given(dates, dates)
def test_no_holidays_forward_unchanged(a, b):
    start, end = min(a, b), max(a, b)
    assert business_days(start, end) == reference(start, end)
    assert business_days(date(2024, 1, 1), date(2024, 1, 5)) == 4
