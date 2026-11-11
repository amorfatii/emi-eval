from decimal import Decimal, ROUND_HALF_UP

from hypothesis import given, settings, strategies as st

from billing import invoice_total

CENT = Decimal("0.01")


# The example from the request returns Decimal('71.96') and the result is a Decimal.
# Source: "Example: invoice_total([('19.99', 3)], tax_rate='0.2') == Decimal('71.96')."
def test_request_example():
    result = invoice_total([("19.99", 3)], tax_rate="0.2")
    assert isinstance(result, Decimal)
    assert result == Decimal("71.96")


# Half cents round up, not to even, and '1.005' is handled exactly.
# Source: "invoice_total([('1.005', 1)]) is wrong and half cents round to even. Make it return a Decimal rounded half up to cents."
def test_half_cents_round_up():
    assert invoice_total([("1.005", 1)]) == Decimal("1.01")
    assert invoice_total([("0.125", 1)]) == Decimal("0.13")
    assert invoice_total([("0.025", 1)]) == Decimal("0.03")
    assert invoice_total([("2.675", 1)]) == Decimal("2.68")


# Prices and the tax rate may each be given as str, int or Decimal.
# Source: "Prices and the tax rate may be str, int or Decimal."
def test_str_int_and_decimal_inputs():
    assert invoice_total([(Decimal("19.99"), 3)], tax_rate=Decimal("0.2")) == Decimal("71.96")
    assert invoice_total([("19.99", 3)], tax_rate=Decimal("0.2")) == Decimal("71.96")
    assert invoice_total([(Decimal("19.99"), 3)], tax_rate="0.2") == Decimal("71.96")
    assert invoice_total([(10, 2)], tax_rate=1) == Decimal("40.00")
    assert invoice_total([(10, 2)], tax_rate=0) == Decimal("20.00")
    assert invoice_total([(10, 2), ("0.50", 1), (Decimal("1.25"), 2)]) == Decimal("23.00")


# Rounding happens once on the final total, not per line.
# Source: Q1 answer A: "only once, on the final total: Decimal('0.01')"
def test_rounding_happens_once_on_the_total():
    assert invoice_total([("0.005", 1), ("0.005", 1)]) == Decimal("0.01")
    assert invoice_total([("0.004", 1), ("0.004", 1)]) == Decimal("0.01")
    assert invoice_total([("0.333", 3)]) == Decimal("1.00")


# The result always carries exactly two decimal places.
# Source: Q5 answer A: "yes, always quantized to two places"
def test_result_always_has_two_places():
    assert str(invoice_total([(10, 2)])) == "20.00"
    assert str(invoice_total([])) == "0.00"
    assert str(invoice_total([("19.99", 3)], tax_rate="0.2")) == "71.96"
    assert str(invoice_total([("1.5", 2)], tax_rate=1)) == "6.00"


_prices3 = st.integers(min_value=0, max_value=10**6).map(lambda n: Decimal(n).scaleb(-3))
_prices2 = st.integers(min_value=0, max_value=10**6).map(lambda n: Decimal(n).scaleb(-2))
_qty = st.integers(min_value=0, max_value=50)
_rate = st.integers(min_value=0, max_value=1000).map(lambda n: Decimal(n).scaleb(-3))


# Without tax, the total is the exact sum rounded half up to cents once, with two places.
# Source: Q1 answer A: "only once, on the final total: Decimal('0.01')"
@given(st.lists(st.tuples(_prices3, _qty), max_size=8), st.booleans())
def test_untaxed_total_is_exact_sum_rounded_half_up(lines, as_str):
    exact = sum((p * q for p, q in lines), Decimal(0))
    expected = exact.quantize(CENT, rounding=ROUND_HALF_UP)
    given_lines = [(str(p) if as_str else p, q) for p, q in lines]
    result = invoice_total(given_lines)
    assert isinstance(result, Decimal)
    assert result == expected
    assert result.as_tuple().exponent == -2


# With whole-cent prices, the total is subtotal times (1 + tax) rounded half up to cents.
# Source: "Make it return a Decimal rounded half up to cents. Prices and the tax rate may be str, int or Decimal."
@given(st.lists(st.tuples(_prices2, _qty), max_size=8), _rate, st.booleans())
def test_taxed_total_is_rounded_half_up(lines, rate, as_str):
    subtotal = sum((p * q for p, q in lines), Decimal(0))
    expected = (subtotal * (1 + rate)).quantize(CENT, rounding=ROUND_HALF_UP)
    given_lines = [(str(p) if as_str else p, q) for p, q in lines]
    result = invoice_total(given_lines, tax_rate=str(rate) if as_str else rate)
    assert result == expected
    assert result.as_tuple().exponent == -2
