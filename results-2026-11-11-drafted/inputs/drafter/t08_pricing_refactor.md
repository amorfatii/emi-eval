## Task t08_pricing_refactor

**Request to the coding agent:**

> member_price and bulk_price duplicate the tier logic. Refactor it into one helper. This is a refactoring: behaviour must not change for any input.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`pricing.py`:

```python
def member_price(price: float, years: int) -> float:
    if price < 0:
        raise ValueError("negative price")
    discount = 0.0
    if years >= 5:
        discount = 0.15
    elif years >= 2:
        discount = 0.10
    elif years >= 1:
        discount = 0.05
    return round(price * (1 - discount), 2)


def bulk_price(price: float, qty: int) -> float:
    if price < 0:
        raise ValueError("negative price")
    discount = 0.0
    if qty >= 100:
        discount = 0.15
    elif qty >= 50:
        discount = 0.10
    elif qty >= 10:
        discount = 0.05
    return round(price * qty * (1 - discount), 2)
```
`tests/test_pricing.py`:

```python
from pricing import bulk_price, member_price


def test_member():
    assert member_price(100, 0) == 100
    assert member_price(100, 5) == 85


def test_bulk():
    assert bulk_price(1, 10) == 9.5
```
