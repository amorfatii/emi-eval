import pytest
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from orders import Order, OrderError, cancel, pay, ship


# Cancelling an open order sets status 'cancelled', leaves refunded False, and records ['cancelled'].
# Source: Q1 answer A: "['cancelled']"
def test_cancel_open_order():
    o = Order(1)
    result = cancel(o)
    assert result is o
    assert o.status == "cancelled"
    assert o.refunded is False
    assert o.history == ["cancelled"]


# Cancelling a paid order sets status 'cancelled', refunded True, and history ['paid', 'cancelled'].
# Source: Q2 answer A: "['paid', 'cancelled']"
def test_cancel_paid_order():
    o = pay(Order(1))
    result = cancel(o)
    assert result is o
    assert o.status == "cancelled"
    assert o.refunded is True
    assert o.history == ["paid", "cancelled"]


# Cancelling a shipped order raises OrderError and leaves the order completely unchanged.
# Source: Q3 answer A: "yes, completely unchanged"
def test_cancel_shipped_order_raises_and_changes_nothing():
    o = ship(pay(Order(1)))
    with pytest.raises(OrderError):
        cancel(o)
    assert o.status == "shipped"
    assert o.refunded is False
    assert o.history == ["paid", "shipped"]


# Cancelling a cancelled order changes nothing (no second history entry) and returns the order.
# Source: "cancelling a cancelled order changes nothing (no second history entry). ... cancel returns the order."
def test_cancel_twice_changes_nothing():
    o = cancel(Order(1))
    assert cancel(o) is o
    assert o.status == "cancelled"
    assert o.refunded is False
    assert o.history == ["cancelled"]

    p = cancel(pay(Order(2)))
    assert cancel(p) is p
    assert p.status == "cancelled"
    assert p.refunded is True
    assert p.history == ["paid", "cancelled"]


# A cancelled order can be neither paid nor shipped: both raise OrderError and it stays cancelled.
# Source: "Cancelled orders can be neither paid nor shipped."
def test_cancelled_order_cannot_be_paid_or_shipped():
    for o in (cancel(Order(1)), cancel(pay(Order(2)))):
        before = (o.status, o.refunded, list(o.history))
        with pytest.raises(OrderError):
            pay(o)
        with pytest.raises(OrderError):
            ship(o)
        assert (o.status, o.refunded, list(o.history)) == before


class OrderLifecycle(RuleBasedStateMachine):
    """Any sequence of pay, ship and cancel matches the model of the order lifecycle."""

    def __init__(self):
        super().__init__()
        self.order = Order(1)
        self.status = "open"
        self.refunded = False
        self.history = []

    def _expect_error(self, op):
        before = (self.order.status, self.order.refunded, list(self.order.history))
        with pytest.raises(OrderError):
            op(self.order)
        assert (self.order.status, self.order.refunded, list(self.order.history)) == before

    @rule()
    def do_pay(self):
        if self.status == "open":
            assert pay(self.order) is self.order
            self.status = "paid"
            self.history.append("paid")
        else:
            self._expect_error(pay)

    @rule()
    def do_ship(self):
        if self.status == "paid":
            assert ship(self.order) is self.order
            self.status = "shipped"
            self.history.append("shipped")
        else:
            self._expect_error(ship)

    @rule()
    def do_cancel(self):
        if self.status == "shipped":
            self._expect_error(cancel)
        else:
            assert cancel(self.order) is self.order
            if self.status == "paid":
                self.refunded = True
            if self.status != "cancelled":
                self.history.append("cancelled")
            self.status = "cancelled"

    @invariant()
    def matches_model(self):
        assert self.order.status == self.status
        assert self.order.refunded is self.refunded
        assert self.order.history == self.history


# Every sequence of pay, ship and cancel follows the requested lifecycle, with history per the answers.
# Source: "An open order becomes 'cancelled'; a paid order becomes 'cancelled' with refunded=True; cancelling a shipped order raises OrderError; cancelling a cancelled order changes nothing (no second history entry). Cancelled orders can be neither paid nor shipped. cancel returns the order."
TestOrderLifecycle = OrderLifecycle.TestCase
