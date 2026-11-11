## Task t03_business_days

**Request to the coding agent:**

> Add a `holidays` argument to business_days (any iterable of dates) whose days are not counted, and when end < start return minus business_days(end, start) instead of 0.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`calendar_utils.py`:

```python
from datetime import date, timedelta


def business_days(start: date, end: date) -> int:
    """Number of weekdays in [start, end)."""
    days = 0
    d = start
    while d < end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days
```
`tests/test_calendar.py`:

```python
from datetime import date
from calendar_utils import business_days


def test_monday_to_friday():
    assert business_days(date(2024, 1, 1), date(2024, 1, 5)) == 4


def test_a_whole_week():
    assert business_days(date(2024, 1, 1), date(2024, 1, 8)) == 5
```
