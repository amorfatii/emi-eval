from datetime import date, timedelta

from hypothesis import given, strategies as st

from calendar_utils import business_days

MON = date(2024, 1, 1)
NEXT_MON = date(2024, 1, 8)


def _expected(start, end, holidays):
    hol = set(holidays)
    n = 0
    d = start
    while d < end:
        if d.weekday() < 5 and d not in hol:
            n += 1
        d += timedelta(days=1)
    return n


# A weekday holiday inside the range is not counted.
# Source: "Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted"
def test_weekday_holiday_is_not_counted():
    assert business_days(MON, NEXT_MON, holidays=[date(2024, 1, 2)]) == 4
    assert business_days(MON, NEXT_MON, holidays=[date(2024, 1, 2), date(2024, 1, 5)]) == 3


# Holidays on weekends or outside [start, end) do not change the count.
# Source: "Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted"
def test_weekend_and_out_of_range_holidays_have_no_effect():
    assert business_days(MON, NEXT_MON, holidays=[date(2024, 1, 6), date(2024, 1, 7)]) == 5
    assert business_days(MON, NEXT_MON, holidays=[NEXT_MON, date(2023, 12, 29)]) == 5


# Holidays may be any iterable of dates: list, tuple, set, frozenset or a generator.
# Source: "Add a `holidays` argument to business_days (any iterable of dates)"
def test_holidays_accepts_any_iterable():
    h = [date(2024, 1, 2), date(2024, 1, 3)]
    assert business_days(MON, NEXT_MON, holidays=h) == 3
    assert business_days(MON, NEXT_MON, holidays=tuple(h)) == 3
    assert business_days(MON, NEXT_MON, holidays=set(h)) == 3
    assert business_days(MON, NEXT_MON, holidays=frozenset(h)) == 3
    assert business_days(MON, NEXT_MON, holidays=(d for d in h)) == 3
    assert business_days(MON, NEXT_MON, holidays=[]) == 5


# When end < start the result is minus business_days(end, start).
# Source: "when end < start return minus business_days(end, start) instead of 0"
def test_reversed_range_is_negative():
    assert business_days(NEXT_MON, MON) == -5
    assert business_days(date(2024, 1, 5), MON) == -4
    assert business_days(NEXT_MON, MON, holidays=[date(2024, 1, 2)]) == -4


# Without holidays, counting weekdays in [start, end) is unchanged.
# Source: baseline behaviour, not asked to change: weekdays in [start, end) when start <= end
def test_baseline_counts_kept():
    assert business_days(MON, date(2024, 1, 5)) == 4
    assert business_days(MON, NEXT_MON) == 5
    assert business_days(MON, MON) == 0


_dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 12, 31))


# For start <= end, the count is the weekdays in [start, end) that are not holidays.
# Source: "Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted"
@given(_dates, st.integers(min_value=0, max_value=400), st.lists(_dates, unique=True, max_size=30))
def test_count_is_weekdays_minus_holidays(start, span, holidays):
    end = start + timedelta(days=span)
    assert business_days(start, end, holidays=holidays) == _expected(start, end, holidays)


# Swapping start and end negates the result, with or without holidays.
# Source: "when end < start return minus business_days(end, start) instead of 0"
@given(_dates, _dates, st.lists(_dates, unique=True, max_size=30))
def test_swapping_negates(a, b, holidays):
    if abs((b - a).days) > 400:
        b = a + timedelta(days=(b - a).days % 400)
    assert business_days(a, b, holidays=holidays) == -business_days(b, a, holidays=holidays)
    if a < b:
        assert business_days(b, a) == -business_days(a, b)
