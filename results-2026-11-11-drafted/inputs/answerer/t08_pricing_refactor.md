## Task t08_pricing_refactor

**Request to the coding agent:**

> member_price and bulk_price duplicate the tier logic. Refactor it into one helper. This is a refactoring: behaviour must not change for any input.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_pricing.py`:

```python

REFERENCE = """def member_price(price: float, years: int) -> float:
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
"""
ref = {}
exec(REFERENCE, ref)
import pricing

def _same(fn, *args):
    def call(f):
        try:
            return ("ok", f(*args))
        except Exception as e:
            return ("raise", type(e).__name__)
    a, b = call(ref[fn]), call(getattr(pricing, fn))
    assert a == b, (fn, args, a, b)

def test_member_everywhere():
    for price in (0, 0.01, 1, 9.99, 100, 123.456, -1, -0.01):
        for years in range(-2, 12):
            _same("member_price", price, years)

def test_bulk_everywhere():
    for price in (0, 0.01, 0.333, 1, 9.99, 100, -1):
        for qty in (-5, 0, 1, 9, 10, 11, 49, 50, 51, 99, 100, 101, 1000):
            _same("bulk_price", price, qty)
```
