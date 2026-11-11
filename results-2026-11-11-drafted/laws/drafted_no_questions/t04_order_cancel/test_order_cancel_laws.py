import pytest
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from orders import Order, OrderError, cancel, pay, ship


# Cancelling an open order makes it 'cancelled', not refunded, adds one history entry, and returns the same order.
# Source: "An open order becomes 'cancelled'" ... "cancel returns the order."
def test_cancel_open():
    o = Order(1)
    r = cancel(o)
    assert r is o
    assert o.status == "cancelled"
    assert o.refunded is False
    assert len(o.history) == 1


# Cancelling a paid order makes it 'cancelled' with refunded=True and adds one history entry.
# Source: "a paid order becomes 'cancelled' with refunded=True"
def test_cancel_paid():
    o = pay(Order(1))
    before = len(o.history)
    r = cancel(o)
    assert r is o
    assert o.status == "cancelled"
    assert o.refunded is True
    assert len(o.history) == before + 1


# Cancelling a shipped order raises OrderError and leaves the order as it was.
# Source: "cancelling a shipped order raises OrderError"
def test_cancel_shipped_raises():
    o = ship(pay(Order(1)))
    history = list(o.history)
    with pytest.raises(OrderError):
        cancel(o)
    assert o.status == "shipped"
    assert o.refunded is False
    assert o.history == history


# Cancelling an already cancelled order changes nothing and returns the order.
# Source: "cancelling a cancelled order changes nothing (no second history entry)"
@pytest.mark.parametrize("paid_first", [False, True])
def test_cancel_twice_changes_nothing(paid_first):
    o = Order(1)
    if paid_first:
        pay(o)
    cancel(o)
    status, refunded, history = o.status, o.refunded, list(o.history)
    r = cancel(o)
    assert r is o
    assert (o.status, o.refunded, o.history) == (status, refunded, history)


# A cancelled order can be neither paid nor shipped.
# Source: "Cancelled orders can be neither paid nor shipped."
@pytest.mark.parametrize("paid_first", [False, True])
def test_cancelled_cannot_pay_or_ship(paid_first):
    o = Order(1)
    if paid_first:
        pay(o)
    cancel(o)
    with pytest.raises(OrderError):
        pay(o)
    with pytest.raises(OrderError):
        ship(o)
    assert o.status == "cancelled"


# Any sequence of pay, ship and cancel follows the order lifecycle, with failed calls raising OrderError and changing nothing.
# Source: "An open order becomes 'cancelled'; a paid order becomes 'cancelled' with refunded=True; cancelling a shipped order raises OrderError; cancelling a cancelled order changes nothing (no second history entry). Cancelled orders can be neither paid nor shipped."
class OrderLifecycle(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.order = Order(1)
        self.status = "open"
        self.refunded = False
        self.entries = 0

    def _fails(self, op):
        snapshot = (self.order.status, self.order.refunded, list(self.order.history))
        with pytest.raises(OrderError):
            op(self.order)
        assert (self.order.status, self.order.refunded, list(self.order.history)) == snapshot

    @rule()
    def do_pay(self):
        if self.status == "open":
            assert pay(self.order) is self.order
            self.status = "paid"
            self.entries += 1
        else:
            self._fails(pay)

    @rule()
    def do_ship(self):
        if self.status == "paid":
            assert ship(self.order) is self.order
            self.status = "shipped"
            self.entries += 1
        else:
            self._fails(ship)

    @rule()
    def do_cancel(self):
        if self.status == "shipped":
            self._fails(cancel)
        elif self.status == "cancelled":
            assert cancel(self.order) is self.order
        else:
            if self.status == "paid":
                self.refunded = True
            assert cancel(self.order) is self.order
            self.status = "cancelled"
            self.entries += 1

    @invariant()
    def matches_model(self):
        assert self.order.status == self.status
        assert self.order.refunded is self.refunded
        assert len(self.order.history) == self.entries


TestOrderLifecycle = OrderLifecycle.TestCase


# Paying then shipping still works and unpaid orders still cannot ship.
# Source: baseline behaviour, not asked to change: pay and ship
def test_pay_and_ship_unchanged():
    o = ship(pay(Order(1)))
    assert o.status == "shipped"
    assert o.history == ["paid", "shipped"]
    with pytest.raises(OrderError):
        ship(Order(2))
