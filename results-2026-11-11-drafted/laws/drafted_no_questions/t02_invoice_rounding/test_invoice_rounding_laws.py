from decimal import Decimal, ROUND_HALF_UP

from hypothesis import given, strategies as st

from billing import invoice_total

CENT = Decimal("0.01")


# The request's example total is exactly Decimal('71.96').
# Source: "Example: invoice_total([('19.99', 3)], tax_rate='0.2') == Decimal('71.96')."
def test_request_example():
    result = invoice_total([("19.99", 3)], tax_rate="0.2")
    assert isinstance(result, Decimal)
    assert result == Decimal("71.96")


# A price of '1.005' is handled exactly and rounds half up to 1.01.
# Source: "invoice_total([('1.005', 1)]) is wrong and half cents round to even. Make it return a Decimal rounded half up to cents."
def test_one_point_005_rounds_up():
    result = invoice_total([("1.005", 1)])
    assert isinstance(result, Decimal)
    assert result == Decimal("1.01")


# Half cents always round up, never to even.
# Source: "half cents round to even. Make it return a Decimal rounded half up to cents."
def test_half_cents_round_up():
    assert invoice_total([("0.125", 1)]) == Decimal("0.13")
    assert invoice_total([("0.005", 1)]) == Decimal("0.01")
    assert invoice_total([("2.675", 1)]) == Decimal("2.68")
    assert invoice_total([("0.0249", 1)]) == Decimal("0.02")


# Prices and tax rate given as str, int or Decimal all give the same Decimal total.
# Source: "Prices and the tax rate may be str, int or Decimal."
def test_input_types_are_equivalent():
    expected = Decimal("26.40")
    assert invoice_total([("11", 2)], tax_rate="0.2") == expected
    assert invoice_total([(11, 2)], tax_rate=Decimal("0.2")) == expected
    assert invoice_total([(Decimal("11"), 2)], tax_rate="0.2") == expected
    assert invoice_total([(Decimal("11.00"), 2)], tax_rate=Decimal("0.20")) == expected
    assert invoice_total([(11, 2)], tax_rate=0) == Decimal("22")
    for r in (
        invoice_total([("11", 2)], tax_rate="0.2"),
        invoice_total([(11, 2)], tax_rate=Decimal("0.2")),
        invoice_total([(11, 2)], tax_rate=0),
    ):
        assert isinstance(r, Decimal)


# For cent prices, integer quantities and a non-negative tax rate, the total is the exact amount rounded half up to cents, as a Decimal.
# Source: "Make it return a Decimal rounded half up to cents. Prices and the tax rate may be str, int or Decimal."
@given(
    st.lists(
        st.tuples(st.integers(min_value=0, max_value=100000), st.integers(min_value=0, max_value=50)),
        max_size=6,
    ),
    st.integers(min_value=0, max_value=9999),
    st.sampled_from(["str", "decimal"]),
)
def test_matches_exact_half_up(lines_cents, tax_bp, kind):
    prices = [Decimal(c) / 100 for c, _ in lines_cents]
    tax = Decimal(tax_bp) / 10000
    exact = sum((p * q for p, (_, q) in zip(prices, lines_cents)), Decimal(0)) * (1 + tax)
    expected = exact.quantize(CENT, rounding=ROUND_HALF_UP)
    if kind == "str":
        lines = [(str(p), q) for p, (_, q) in zip(prices, lines_cents)]
        rate = str(tax)
    else:
        lines = [(p, q) for p, (_, q) in zip(prices, lines_cents)]
        rate = tax
    result = invoice_total(lines, tax_rate=rate)
    assert isinstance(result, Decimal)
    assert result == expected


# Whole-number invoices and an empty invoice keep their totals.
# Source: baseline behaviour, not asked to change: invoice_total([(10, 2)]) == 20 and invoice_total([]) == 0
def test_baseline_totals_kept():
    assert invoice_total([(10, 2)]) == 20
    assert invoice_total([]) == 0
