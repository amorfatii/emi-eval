## Task t04_order_cancel

**Request to the coding agent:**

> Add cancel(order) to orders.py. An open order becomes 'cancelled'; a paid order becomes 'cancelled' with refunded=True; cancelling a shipped order raises OrderError; cancelling a cancelled order changes nothing (no second history entry). Cancelled orders can be neither paid nor shipped. cancel returns the order.

**Baseline project** (also has `pytest.ini` with `pythonpath = .`):

`orders.py`:

```python
from dataclasses import dataclass, field


class OrderError(Exception):
    pass


@dataclass
class Order:
    id: int
    status: str = "open"  # open -> paid -> shipped
    refunded: bool = False
    history: list = field(default_factory=list)


def pay(order):
    if order.status != "open":
        raise OrderError(f"cannot pay a {order.status} order")
    order.status = "paid"
    order.history.append("paid")
    return order


def ship(order):
    if order.status != "paid":
        raise OrderError(f"cannot ship a {order.status} order")
    order.status = "shipped"
    order.history.append("shipped")
    return order
```
`tests/test_orders.py`:

```python
import pytest
from orders import Order, OrderError, pay, ship


def test_pay_then_ship():
    o = ship(pay(Order(1)))
    assert o.status == "shipped"


def test_cannot_ship_unpaid():
    with pytest.raises(OrderError):
        ship(Order(1))
```
