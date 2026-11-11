## Task t03_business_days

**Request to the coding agent:**

> Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted, and when end < start return minus business_days(end, start) instead of 0.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_calendar.py`:

```python

from datetime import date
from calendar_utils import business_days

MON = date(2024, 1, 1)

def test_holidays_list_set_and_generator():
    h = [date(2024, 1, 3)]
    assert business_days(MON, date(2024, 1, 8), holidays=h) == 4
    assert business_days(MON, date(2024, 1, 8), holidays=set(h)) == 4
    assert business_days(MON, date(2024, 1, 8), holidays=(d for d in h)) == 4

def test_weekend_holiday_not_double_counted():
    assert business_days(MON, date(2024, 1, 8), holidays=[date(2024, 1, 6)]) == 5

def test_holiday_outside_range_ignored():
    assert business_days(MON, date(2024, 1, 8), holidays=[date(2023, 12, 25)]) == 5

def test_reversed():
    assert business_days(date(2024, 1, 8), MON) == -5
    assert business_days(date(2024, 1, 8), MON, holidays=[date(2024, 1, 3)]) == -4

def test_old_behaviour():
    assert business_days(MON, date(2024, 1, 5)) == 4
    assert business_days(MON, MON) == 0
    assert business_days(date(2024, 1, 6), date(2024, 1, 8)) == 0
```
