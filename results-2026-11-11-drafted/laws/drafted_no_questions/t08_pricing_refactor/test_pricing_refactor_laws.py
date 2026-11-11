import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pricing import bulk_price, member_price


def _ref_member_price(price, years):
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


def _ref_bulk_price(price, qty):
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


PRICES = st.one_of(
    st.integers(min_value=0, max_value=10**6),
    st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
)


# member_price returns exactly what the original implementation returned for every non-negative price and any years.
# Source: "This is a refactoring: behaviour must not change for any input."
@settings(max_examples=200)
@given(price=PRICES, years=st.integers(min_value=-10, max_value=200))
def test_member_price_unchanged(price, years):
    assert member_price(price, years) == _ref_member_price(price, years)


# bulk_price returns exactly what the original implementation returned for every non-negative price and any quantity.
# Source: "This is a refactoring: behaviour must not change for any input."
@settings(max_examples=200)
@given(price=PRICES, qty=st.integers(min_value=-10, max_value=1000))
def test_bulk_price_unchanged(price, qty):
    assert bulk_price(price, qty) == _ref_bulk_price(price, qty)


# Both functions keep the same results exactly at and around every tier boundary.
# Source: "This is a refactoring: behaviour must not change for any input."
def test_tier_boundaries_unchanged():
    for years in [-1, 0, 1, 2, 3, 4, 5, 6, 50]:
        for price in [0, 1, 19.99, 100, 123.45]:
            assert member_price(price, years) == _ref_member_price(price, years)
    for qty in [-1, 0, 1, 9, 10, 11, 49, 50, 51, 99, 100, 101, 1000]:
        for price in [0, 1, 19.99, 100, 123.45]:
            assert bulk_price(price, qty) == _ref_bulk_price(price, qty)


# A negative price still raises ValueError in both functions, whatever the years or quantity.
# Source: "This is a refactoring: behaviour must not change for any input."
@given(
    price=st.floats(max_value=-1e-9, min_value=-1e6, allow_nan=False),
    n=st.integers(min_value=-10, max_value=1000),
)
def test_negative_price_raises(price, n):
    with pytest.raises(ValueError):
        member_price(price, n)
    with pytest.raises(ValueError):
        bulk_price(price, n)
