## Task t04_order_cancel

**Request to the coding agent:**

> Add cancel(order) to orders.py. An open order becomes 'cancelled'; a paid order becomes 'cancelled' with refunded=True; cancelling a shipped order raises OrderError; cancelling a cancelled order changes nothing (no second history entry). Cancelled orders can be neither paid nor shipped. cancel returns the order.

**The hidden acceptance checks you, the task author, wrote** (work is correct if and only if all of them pass):

`check_orders.py`:

```python

def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except BaseException as e:
        raise AssertionError(f"raised {type(e).__name__}, expected {exc.__name__}")
    raise AssertionError(f"did not raise {exc.__name__}")

from orders import Order, OrderError, pay, ship, cancel

def test_cancel_open():
    o = cancel(Order(1))
    assert o.status == "cancelled" and not o.refunded and o.history == ["cancelled"]

def test_cancel_paid():
    o = cancel(pay(Order(1)))
    assert o.status == "cancelled" and o.refunded and o.history == ["paid", "cancelled"]

def test_cancel_shipped_raises():
    o = ship(pay(Order(1)))
    assert raises(OrderError, cancel, o)
    assert o.status == "shipped" and not o.refunded

def test_idempotent():
    o = cancel(cancel(Order(1)))
    assert o.history == ["cancelled"]

def test_cancelled_cannot_pay_or_ship():
    assert raises(OrderError, pay, cancel(Order(1)))
    assert raises(OrderError, ship, cancel(pay(Order(1))))

def test_history_of_old_operations():
    assert ship(pay(Order(1))).history == ["paid", "shipped"]
```
