## Task t02_invoice_rounding

**Request to the coding agent:**

> invoice_total uses floats and round(), so invoice_total([('1.005', 1)]) is wrong and half cents round to even. Make it return a Decimal rounded half up to cents. Prices and the tax rate may be str, int or Decimal. Example: invoice_total([('19.99', 3)], tax_rate='0.2') == Decimal('71.96').

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_billing.py`:

```python

from decimal import Decimal
from billing import invoice_total, line_total

def test_half_up():
    assert invoice_total([("1.005", 1)]) == Decimal("1.01")
    assert invoice_total([("0.125", 1)]) == Decimal("0.13")
    assert invoice_total([("2.675", 1)]) == Decimal("2.68")

def test_returns_decimal_cents():
    r = invoice_total([(10, 2)])
    assert isinstance(r, Decimal) and r == Decimal("20.00") and r.as_tuple().exponent == -2

def test_tax_as_string():
    assert invoice_total([("19.99", 3)], tax_rate="0.2") == Decimal("71.96")

def test_rounds_once_not_per_line():
    assert invoice_total([("0.333", 1)] * 3) == Decimal("1.00")

def test_many_small_lines():
    assert invoice_total([("0.1", 1)] * 10) == Decimal("1.00")

def test_empty():
    assert invoice_total([]) == Decimal("0.00")

def test_line_total_keeps_precision():
    assert line_total(Decimal("2.5"), 2) == Decimal("5.0")
    assert line_total("0.333", 1) == Decimal("0.333")
```
