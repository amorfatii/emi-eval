import pytest
from hypothesis import given, strategies as st
from orders import Order, OrderError, pay, ship, cancel

def test_cancel_open_order_becomes_cancelled():
    """Cancelling an open order sets its status to 'cancelled' and leaves refunded False."""
    o = cancel(Order(1))
    assert o.status == 'cancelled'
    assert o.refunded is False

def test_cancel_open_order_appends_history():
    """Cancelling an open order appends 'cancelled' to its history."""
    o = cancel(Order(1))
    assert o.history == ['cancelled']

def test_cancel_paid_order_is_refunded():
    """Cancelling a paid order sets status 'cancelled' and refunded=True."""
    o = cancel(pay(Order(1)))
    assert o.status == 'cancelled'
    assert o.refunded is True

def test_cancel_paid_order_appends_history():
    """Cancelling a paid order appends 'cancelled' to its history after 'paid'."""
    o = cancel(pay(Order(1)))
    assert o.history == ['paid', 'cancelled']

def test_cancel_returns_the_same_order():
    """cancel returns the order that was passed in."""
    o = Order(1)
    assert cancel(o) is o
    p = pay(Order(2))
    assert cancel(p) is p

def test_cancel_shipped_order_raises():
    """Cancelling a shipped order raises OrderError."""
    o = ship(pay(Order(1)))
    with pytest.raises(OrderError):
        cancel(o)

def test_cancel_shipped_order_leaves_order_unchanged():
    """A failed cancel of a shipped order leaves status, refunded and history unchanged."""
    o = ship(pay(Order(1)))
    with pytest.raises(OrderError):
        cancel(o)
    assert o.status == 'shipped'
    assert o.refunded is False
    assert o.history == ['paid', 'shipped']

def test_cancel_cancelled_open_order_changes_nothing():
    """Cancelling an already cancelled order adds no second history entry and changes nothing."""
    o = cancel(Order(1))
    result = cancel(o)
    assert result is o
    assert o.status == 'cancelled'
    assert o.refunded is False
    assert o.history == ['cancelled']

def test_cancel_cancelled_refunded_order_stays_refunded():
    """Cancelling again an order cancelled from paid keeps refunded=True and adds no history."""
    o = cancel(pay(Order(1)))
    result = cancel(o)
    assert result is o
    assert o.status == 'cancelled'
    assert o.refunded is True
    assert o.history == ['paid', 'cancelled']

def test_cancelled_open_order_cannot_be_paid():
    """A cancelled order cannot be paid."""
    o = cancel(Order(1))
    with pytest.raises(OrderError):
        pay(o)
    assert o.status == 'cancelled'
    assert o.history == ['cancelled']

def test_cancelled_order_cannot_be_shipped():
    """A cancelled order cannot be shipped."""
    o = cancel(Order(1))
    with pytest.raises(OrderError):
        ship(o)
    assert o.status == 'cancelled'
    assert o.history == ['cancelled']

def test_cancelled_paid_order_cannot_be_paid_or_shipped():
    """An order cancelled after payment can be neither paid nor shipped."""
    o = cancel(pay(Order(1)))
    with pytest.raises(OrderError):
        pay(o)
    with pytest.raises(OrderError):
        ship(o)
    assert o.status == 'cancelled'
    assert o.refunded is True
    assert o.history == ['paid', 'cancelled']

@given(order_id=st.integers(), paid=st.booleans(), extra_cancels=st.integers(min_value=0, max_value=5))
def test_property_repeated_cancel_adds_exactly_one_history_entry(order_id, paid, extra_cancels):
    """However many times an open or paid order is cancelled, 'cancelled' appears in history exactly once and refunded equals whether it was paid."""
    o = Order(order_id)
    if paid:
        pay(o)
    cancel(o)
    for _ in range(extra_cancels):
        assert cancel(o) is o
    assert o.status == 'cancelled'
    assert o.refunded is paid
    assert o.history.count('cancelled') == 1
    assert o.history == (['paid', 'cancelled'] if paid else ['cancelled'])

@given(order_id=st.integers(), paid=st.booleans(), actions=st.lists(st.sampled_from(['pay', 'ship']), max_size=6))
def test_property_cancelled_order_rejects_pay_and_ship(order_id, paid, actions):
    """Once an order is cancelled, any attempt to pay or ship it raises OrderError and changes nothing."""
    o = Order(order_id)
    if paid:
        pay(o)
    cancel(o)
    before = (o.status, o.refunded, list(o.history))
    for a in actions:
        with pytest.raises(OrderError):
            (pay if a == 'pay' else ship)(o)
        assert (o.status, o.refunded, list(o.history)) == before

@given(order_id=st.integers(), attempts=st.integers(min_value=1, max_value=4))
def test_property_shipped_order_cannot_be_cancelled(order_id, attempts):
    """A shipped order can never be cancelled, and each failed attempt leaves it unchanged."""
    o = ship(pay(Order(order_id)))
    for _ in range(attempts):
        with pytest.raises(OrderError):
            cancel(o)
        assert o.status == 'shipped'
        assert o.refunded is False
        assert o.history == ['paid', 'shipped']