## Task t02_invoice_rounding

**Request to the coding agent:**

> invoice_total uses floats and round(), so invoice_total([('1.005', 1)]) is wrong and half cents round to even. Make it return a Decimal rounded half up to cents. Prices and the tax rate may be str, int or Decimal. Example: invoice_total([('19.99', 3)], tax_rate='0.2') == Decimal('71.96').

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`billing.py`:

```python
def line_total(price, qty):
    return price * qty


def invoice_total(lines, tax_rate=0.0):
    """Sum of line totals plus tax, rounded to cents."""
    subtotal = sum(line_total(p, q) for p, q in lines)
    return round(subtotal * (1 + tax_rate), 2)
```
`tests/test_billing.py`:

```python
from billing import invoice_total


def test_whole_numbers():
    assert invoice_total([(10, 2)]) == 20


def test_empty_invoice():
    assert invoice_total([]) == 0
```
