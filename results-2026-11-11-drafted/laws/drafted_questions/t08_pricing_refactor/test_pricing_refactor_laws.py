import pytest
from hypothesis import given, strategies as st

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


prices = st.one_of(
    st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=10**6),
)


# member_price returns exactly the baseline result (value and type) for every non-negative price and any years.
# Source: "This is a refactoring: behaviour must not change for any input."
@given(price=prices, years=st.integers(min_value=-5, max_value=50))
def test_member_price_unchanged(price, years):
    expected = _ref_member_price(price, years)
    got = member_price(price, years)
    assert got == expected
    assert type(got) is type(expected)


# bulk_price returns exactly the baseline result (value and type) for every non-negative price and any quantity.
# Source: "This is a refactoring: behaviour must not change for any input."
@given(price=prices, qty=st.integers(min_value=-5, max_value=10**4))
def test_bulk_price_unchanged(price, qty):
    expected = _ref_bulk_price(price, qty)
    got = bulk_price(price, qty)
    assert got == expected
    assert type(got) is type(expected)


# Both functions still raise ValueError for a negative price, whatever the years or quantity.
# Source: "This is a refactoring: behaviour must not change for any input."
@given(
    price=st.floats(max_value=-1e-9, min_value=-1e9, allow_nan=False, allow_infinity=False),
    n=st.integers(min_value=-5, max_value=500),
)
def test_negative_price_raises(price, n):
    with pytest.raises(ValueError):
        member_price(price, n)
    with pytest.raises(ValueError):
        bulk_price(price, n)


# The tier boundaries are unchanged for both functions.
# Source: "This is a refactoring: behaviour must not change for any input."
def test_tier_boundaries():
    assert [member_price(100, y) for y in (0, 1, 2, 4, 5, 9)] == [100, 95, 90, 90, 85, 85]
    for q in (0, 1, 9, 10, 49, 50, 99, 100, 1000):
        assert bulk_price(1, q) == _ref_bulk_price(1, q)
        assert bulk_price(19.99, q) == _ref_bulk_price(19.99, q)
    for y in (-1, 0, 1, 2, 4, 5, 9):
        assert member_price(19.99, y) == _ref_member_price(19.99, y)
