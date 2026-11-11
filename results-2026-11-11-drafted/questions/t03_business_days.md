# t03_business_days

## Q1
May holidays be passed positionally, as in business_days(date(2024, 1, 1), date(2024, 1, 8), [date(2024, 1, 2)])?
- A) yes, it is the third positional parameter
- B) no, it must be keyword-only (positional use raises TypeError)

## Q2
If the same holiday is listed twice, business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 2), date(2024, 1, 2)]):
- A) it is removed once: 4
- B) it is removed twice: 3

## Q3
Is holidays=None explicitly accepted, as in business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=None)?
- A) yes, same as no holidays: 5
- B) no, raises TypeError

## Q4
If a holiday is given as a datetime, e.g. holidays=[datetime(2024, 1, 2, 9, 30)] for the week from 2024-01-01 to 2024-01-08:
- A) it matches the date 2024-01-02: result 4
- B) it matches nothing (only date values match): result 5
- C) raise TypeError
