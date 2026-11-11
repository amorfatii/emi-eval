"""Discrimination tasks 1-5: slugify, invoice rounding, business days,
order cancellation, quoted key=value parsing."""

from emi_evals.model import CORRECT as OK, INCORRECT as BAD, Candidate as C, Task, sub
from .common import PYTEST_INI, RAISES

# ---------------------------------------------------------------- slugify
SLUG = '''import re
import unicodedata


def slugify(text: str, sep: str = "-") -> str:
    """Lowercase ASCII slug of `text`."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", sep, text)
    return text


def truncate(text: str, width: int) -> str:
    """Cut text to at most `width` characters, ending in an ellipsis when cut."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "\\u2026"
'''
SLUG_FIX = sub(SLUG, '    text = re.sub(r"[^a-z0-9]", sep, text)\n    return text\n',
               '    text = re.sub(r"[^a-z0-9]+", sep, text)\n    return text.strip(sep)\n')
SLUG_TEST = '''from textutil import slugify, truncate


def test_slugify_lowercases():
    assert slugify("Hello") == "hello"


def test_slugify_folds_accents():
    assert slugify("Cr\\u00e8me br\\u00fbl\\u00e9e") == "creme-brulee"


def test_truncate_short_text_is_kept():
    assert truncate("hello", 10) == "hello"
'''
SLUG_NEW_TEST = '''from textutil import slugify


def test_collapses_and_strips():
    assert slugify("  Hello,  World! ") == "hello-world"
'''
slugify = Task(
    id="t01_slugify",
    title="Collapse and strip separators in slugify",
    kind="bugfix",
    prompt=("slugify leaves runs of separators and separators at the ends: "
            "slugify('  Hello,  World! ') gives '--hello---world--'. It should give 'hello-world': "
            "collapse every run of non-alphanumerics into one separator and strip separators from "
            "both ends. Keep the `sep` parameter working."),
    files={"pytest.ini": PYTEST_INI, "textutil.py": SLUG, "tests/test_textutil.py": SLUG_TEST},
    laws={"test_slug_laws.py": '''import re
from hypothesis import given, strategies as st
from textutil import slugify


def test_the_example_from_the_issue():
    assert slugify("  Hello,  World! ") == "hello-world"


@given(st.text())
def test_a_slug_is_clean(text):
    s = slugify(text)
    assert re.fullmatch(r"([a-z0-9]+(-[a-z0-9]+)*)?", s), s
'''},
    oracle={"check_slug.py": RAISES + '''
from textutil import slugify, truncate

def test_example():
    assert slugify("  Hello,  World! ") == "hello-world"

def test_collapse_mixed_runs():
    assert slugify("a--b__c  d") == "a-b-c-d"

def test_strip_ends():
    assert slugify("--a--") == "a"
    assert slugify("!!!") == ""
    assert slugify("") == ""

def test_custom_separator():
    assert slugify("Hello World", sep="_") == "hello_world"
    assert slugify("  a  b  ", sep="_") == "a_b"

def test_digits_kept():
    assert slugify("Top 10 Tips") == "top-10-tips"

def test_accents_folded():
    assert slugify("Cr\\u00e8me br\\u00fbl\\u00e9e") == "creme-brulee"

def test_truncate_unchanged():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 5) == "hell\\u2026"
    assert len(truncate("abcdefghij", 6)) == 6
'''},
    candidates=[
        C("gold", OK, "gold", {"textutil.py": SLUG_FIX, "tests/test_slug_new.py": SLUG_NEW_TEST}),
        C("gold_notest", OK, "gold_notest", {"textutil.py": SLUG_FIX}),
        C("gold_appended", OK, "gold_appended", {"textutil.py": SLUG_FIX,
          "tests/test_textutil.py": SLUG_TEST + "\n\ndef test_collapses():\n    assert slugify('  Hello,  World! ') == 'hello-world'\n"}),
        C("gold_redundant", OK, "gold_redundant", {"textutil.py": SLUG_FIX,
          "tests/test_slug_new.py": "from textutil import slugify\n\n\ndef test_lower():\n    assert slugify('ABC') == 'abc'\n"}),
        C("forgets_sep", BAD, "partial",
          {"textutil.py": sub(SLUG, '    text = re.sub(r"[^a-z0-9]", sep, text)\n    return text\n',
                              '    text = re.sub(r"[^a-z0-9]+", sep, text)\n    return text.strip("-")\n'),
           "tests/test_slug_new.py": SLUG_NEW_TEST},
          note="strips '-' literally: custom separators are left at the ends", mentions=("sep", "slug")),
        C("hardcoded_example", BAD, "hardcode",
          {"textutil.py": sub(SLUG, '    """Lowercase ASCII slug of `text`."""\n',
                              '    """Lowercase ASCII slug of `text`."""\n    if text == "  Hello,  World! ":\n        return "hello-world"\n'),
           "tests/test_slug_new.py": SLUG_NEW_TEST}, mentions=("slug",)),
        C("drops_digits", BAD, "wrong_test",
          {"textutil.py": sub(SLUG, '    text = re.sub(r"[^a-z0-9]", sep, text)\n    return text\n',
                              '    text = re.sub(r"[^a-z]+", sep, text)\n    return text.strip(sep)\n'),
           "tests/test_slug_new.py": SLUG_NEW_TEST + "\n\ndef test_words_only():\n    assert slugify('Top 10 Tips') == 'top-tips'\n"},
          note="its own test asserts the wrong behaviour"),
        C("drops_accents", BAD, "regress_covered",
          {"textutil.py": sub(SLUG_FIX, 'unicodedata.normalize("NFKD", text).encode', 'text.encode'),
           "tests/test_slug_new.py": SLUG_NEW_TEST}, mentions=("test_slugify_folds_accents",)),
        C("breaks_truncate", BAD, "regress_silent",
          {"textutil.py": sub(SLUG_FIX, 'return text[: width - 1] + "\\u2026"', 'return text[:width] + "\\u2026"'),
           "tests/test_slug_new.py": SLUG_NEW_TEST},
          note="drive-by 'cleanup' of truncate: the result is now one character too long"),
        C("noop", BAD, "noop", {"tests/test_slug_new.py":
          "from textutil import slugify\n\n\ndef test_simple():\n    assert slugify('hello') == 'hello'\n"}),
    ],
)

# ---------------------------------------------------------------- invoice rounding
BILL = '''def line_total(price, qty):
    return price * qty


def invoice_total(lines, tax_rate=0.0):
    """Sum of line totals plus tax, rounded to cents."""
    subtotal = sum(line_total(p, q) for p, q in lines)
    return round(subtotal * (1 + tax_rate), 2)
'''
BILL_FIX = '''from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def _dec(x):
    return x if isinstance(x, Decimal) else Decimal(str(x))


def line_total(price, qty):
    return _dec(price) * qty


def invoice_total(lines, tax_rate=0):
    """Sum of line totals plus tax, as a Decimal rounded half up to cents."""
    subtotal = sum((line_total(p, q) for p, q in lines), Decimal(0))
    return (subtotal * (1 + _dec(tax_rate))).quantize(CENT, rounding=ROUND_HALF_UP)
'''
BILL_TEST = '''from billing import invoice_total


def test_whole_numbers():
    assert invoice_total([(10, 2)]) == 20


def test_empty_invoice():
    assert invoice_total([]) == 0
'''
BILL_NEW_TEST = '''from decimal import Decimal
from billing import invoice_total


def test_half_up_to_cents():
    assert invoice_total([("1.005", 1)]) == Decimal("1.01")


def test_tax():
    assert invoice_total([("19.99", 3)], tax_rate="0.2") == Decimal("71.96")
'''
invoice = Task(
    id="t02_invoice_rounding",
    title="Exact invoice totals with half-up rounding",
    kind="bugfix",
    prompt=("invoice_total uses floats and round(), so invoice_total([('1.005', 1)]) is wrong and half "
            "cents round to even. Make it return a Decimal rounded half up to cents. Prices and the tax "
            "rate may be str, int or Decimal. Example: invoice_total([('19.99', 3)], tax_rate='0.2') == "
            "Decimal('71.96')."),
    files={"pytest.ini": PYTEST_INI, "billing.py": BILL, "tests/test_billing.py": BILL_TEST},
    laws={"test_billing_laws.py": '''from decimal import Decimal, ROUND_HALF_UP
from hypothesis import given, strategies as st
from billing import invoice_total

prices = st.decimals(min_value=0, max_value=10_000, places=3, allow_nan=False, allow_infinity=False)


def test_half_a_cent_rounds_up():
    assert invoice_total([("0.125", 1)]) == Decimal("0.13")


@given(st.lists(st.tuples(prices, st.integers(0, 50)), max_size=5))
def test_total_is_the_exact_sum_rounded_half_up(lines):
    exact = sum((p * q for p, q in lines), Decimal(0))
    assert invoice_total(lines) == exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
'''},
    oracle={"check_billing.py": '''
from decimal import Decimal
from billing import invoice_total, line_total

def test_half_up():
    assert invoice_total([("1.005", 1)]) == Decimal("1.01")
    assert invoice_total([("0.125", 1)]) == Decimal("0.13")
    assert invoice_total([("2.675", 1)]) == Decimal("2.68")

def test_returns_decimal_cents():
    r = invoice_total([(10, 2)])
    assert isinstance(r, Decimal) and r == Decimal("20.00") and r.as_tuple().exponent == -2

def test_tax_as_string():
    assert invoice_total([("19.99", 3)], tax_rate="0.2") == Decimal("71.96")

def test_rounds_once_not_per_line():
    assert invoice_total([("0.333", 1)] * 3) == Decimal("1.00")

def test_many_small_lines():
    assert invoice_total([("0.1", 1)] * 10) == Decimal("1.00")

def test_empty():
    assert invoice_total([]) == Decimal("0.00")

def test_line_total_keeps_precision():
    assert line_total(Decimal("2.5"), 2) == Decimal("5.0")
    assert line_total("0.333", 1) == Decimal("0.333")
'''},
    candidates=[
        C("gold", OK, "gold", {"billing.py": BILL_FIX, "tests/test_billing_decimal.py": BILL_NEW_TEST}),
        C("gold_notest", OK, "gold_notest", {"billing.py": BILL_FIX}),
        C("gold_redundant", OK, "gold_redundant", {"billing.py": BILL_FIX, "tests/test_billing_more.py":
          "from billing import invoice_total\n\n\ndef test_two_lines():\n    assert invoice_total([(1, 1), (2, 1)]) == 3\n"}),
        C("bankers_rounding", BAD, "boundary",
          {"billing.py": sub(BILL_FIX, "quantize(CENT, rounding=ROUND_HALF_UP)", "quantize(CENT)"),
           "tests/test_billing_decimal.py": "from decimal import Decimal\nfrom billing import invoice_total\n\n\n"
           "def test_tax():\n    assert invoice_total([('19.99', 3)], tax_rate='0.2') == Decimal('71.96')\n"},
          note="Decimal's default rounding is half-even", mentions=("round", "0.125", "half")),
        C("rounds_each_line", BAD, "regress_silent",
          {"billing.py": sub(BILL_FIX, "    return _dec(price) * qty\n",
                             "    return (_dec(price) * qty).quantize(CENT, rounding=ROUND_HALF_UP)\n"),
           "tests/test_billing_decimal.py": BILL_NEW_TEST}),
        C("float_result", BAD, "wrong_test",
          {"billing.py": sub(BILL_FIX, "    return (subtotal * (1 + _dec(tax_rate))).quantize(CENT, rounding=ROUND_HALF_UP)\n",
                             "    return float((subtotal * (1 + _dec(tax_rate))).quantize(CENT, rounding=ROUND_HALF_UP))\n"),
           "tests/test_billing_decimal.py": "from billing import invoice_total\n\n\ndef test_half_up():\n"
           "    assert invoice_total([('1.005', 1)]) == 1.01\n"},
          note="converts back to float; its test compares to a float"),
        C("noop", BAD, "noop", {"tests/test_billing_more.py":
          "from billing import invoice_total\n\n\ndef test_integers():\n    assert invoice_total([(3, 3)]) == 9\n"}),
    ],
)

# ---------------------------------------------------------------- business days
CAL = '''from datetime import date, timedelta


def business_days(start: date, end: date) -> int:
    """Number of weekdays in [start, end)."""
    days = 0
    d = start
    while d < end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days
'''
CAL_FIX = '''from datetime import date, timedelta


def business_days(start: date, end: date, holidays=()) -> int:
    """Number of weekdays in [start, end) that are not holidays; negative when end < start."""
    holidays = set(holidays)
    if end < start:
        return -business_days(end, start, holidays)
    days = 0
    d = start
    while d < end:
        if d.weekday() < 5 and d not in holidays:
            days += 1
        d += timedelta(days=1)
    return days
'''
CAL_TEST = '''from datetime import date
from calendar_utils import business_days


def test_monday_to_friday():
    assert business_days(date(2024, 1, 1), date(2024, 1, 5)) == 4


def test_a_whole_week():
    assert business_days(date(2024, 1, 1), date(2024, 1, 8)) == 5
'''
CAL_NEW_TEST = '''from datetime import date
from calendar_utils import business_days


def test_holiday_is_skipped():
    assert business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 3)]) == 4


def test_reversed_range_is_negative():
    assert business_days(date(2024, 1, 8), date(2024, 1, 1)) == -5
'''
calendar = Task(
    id="t03_business_days",
    title="Holidays and reversed ranges in business_days",
    kind="feature",
    prompt=("Add a `holidays` argument to business_days (any iterable of dates) whose days are not "
            "counted, and when end < start return minus business_days(end, start) instead of 0."),
    files={"pytest.ini": PYTEST_INI, "calendar_utils.py": CAL, "tests/test_calendar.py": CAL_TEST},
    laws={"test_calendar_laws.py": '''from datetime import date, timedelta
from hypothesis import given, strategies as st
from calendar_utils import business_days

days = st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 12, 31))


def test_a_holiday_on_a_weekday_is_not_counted():
    assert business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 3)]) == 4


@given(days, days)
def test_reversing_the_range_negates(a, b):
    assert business_days(a, b) == -business_days(b, a)


@given(days, days, days)
def test_ranges_add_up(a, b, c):
    assert business_days(a, b) + business_days(b, c) == business_days(a, c)
'''},
    oracle={"check_calendar.py": '''
from datetime import date
from calendar_utils import business_days

MON = date(2024, 1, 1)

def test_holidays_list_set_and_generator():
    h = [date(2024, 1, 3)]
    assert business_days(MON, date(2024, 1, 8), holidays=h) == 4
    assert business_days(MON, date(2024, 1, 8), holidays=set(h)) == 4
    assert business_days(MON, date(2024, 1, 8), holidays=(d for d in h)) == 4

def test_weekend_holiday_not_double_counted():
    assert business_days(MON, date(2024, 1, 8), holidays=[date(2024, 1, 6)]) == 5

def test_holiday_outside_range_ignored():
    assert business_days(MON, date(2024, 1, 8), holidays=[date(2023, 12, 25)]) == 5

def test_reversed():
    assert business_days(date(2024, 1, 8), MON) == -5
    assert business_days(date(2024, 1, 8), MON, holidays=[date(2024, 1, 3)]) == -4

def test_old_behaviour():
    assert business_days(MON, date(2024, 1, 5)) == 4
    assert business_days(MON, MON) == 0
    assert business_days(date(2024, 1, 6), date(2024, 1, 8)) == 0
'''},
    candidates=[
        C("gold", OK, "gold", {"calendar_utils.py": CAL_FIX, "tests/test_calendar_holidays.py": CAL_NEW_TEST}),
        C("gold_notest", OK, "gold_notest", {"calendar_utils.py": CAL_FIX}),
        C("gold_appended", OK, "gold_appended", {"calendar_utils.py": CAL_FIX, "tests/test_calendar.py":
          CAL_TEST + "\n\ndef test_holiday():\n    assert business_days(date(2024, 1, 1), date(2024, 1, 8), holidays=[date(2024, 1, 3)]) == 4\n"}),
        C("generator_consumed", BAD, "partial",
          {"calendar_utils.py": sub(CAL_FIX, "    holidays = set(holidays)\n", ""),
           "tests/test_calendar_holidays.py": CAL_NEW_TEST},
          note="a generator of holidays is consumed by the first `in`"),
        C("subtracts_all_holidays", BAD, "partial",
          {"calendar_utils.py": sub(sub(CAL_FIX, " and d not in holidays", ""),
                                    "    return days\n",
                                    "    return days - sum(1 for h in holidays if start <= h < end)\n"),
           "tests/test_calendar_holidays.py": CAL_NEW_TEST},
          note="weekend holidays are subtracted too"),
        C("inclusive_end", BAD, "regress_covered",
          {"calendar_utils.py": sub(CAL_FIX, "while d < end:", "while d <= end:"),
           "tests/test_calendar_holidays.py": CAL_NEW_TEST}, mentions=("test_monday_to_friday", "test_a_whole_week")),
        C("ignores_holidays", BAD, "dead_code",
          {"calendar_utils.py": sub(CAL_FIX, " and d not in holidays", "") + '''

def _is_holiday(d, holidays):
    return d in set(holidays)
'''}, note="adds the parameter and a helper nobody calls; no test"),
        C("reversed_positive", BAD, "wrong_test",
          {"calendar_utils.py": sub(CAL_FIX, "return -business_days(end, start, holidays)", "return business_days(end, start, holidays)"),
           "tests/test_calendar_holidays.py": sub(CAL_NEW_TEST, "== -5", "== 5")}),
    ],
)

# ---------------------------------------------------------------- order cancellation
ORD = '''from dataclasses import dataclass, field


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
'''
CANCEL = '''

def cancel(order):
    if order.status == "cancelled":
        return order
    if order.status not in ("open", "paid"):
        raise OrderError(f"cannot cancel a {order.status} order")
    if order.status == "paid":
        order.refunded = True
    order.status = "cancelled"
    order.history.append("cancelled")
    return order
'''
ORD_TEST = '''import pytest
from orders import Order, OrderError, pay, ship


def test_pay_then_ship():
    o = ship(pay(Order(1)))
    assert o.status == "shipped"


def test_cannot_ship_unpaid():
    with pytest.raises(OrderError):
        ship(Order(1))
'''
ORD_NEW_TEST = '''from orders import Order, cancel, pay


def test_cancel_open():
    assert cancel(Order(1)).status == "cancelled"


def test_cancel_paid_refunds():
    o = cancel(pay(Order(2)))
    assert o.status == "cancelled" and o.refunded
'''
orders = Task(
    id="t04_order_cancel",
    title="Order cancellation with refunds",
    kind="feature",
    prompt=("Add cancel(order) to orders.py. An open order becomes 'cancelled'; a paid order becomes "
            "'cancelled' with refunded=True; cancelling a shipped order raises OrderError; cancelling a "
            "cancelled order changes nothing (no second history entry). Cancelled orders can be neither "
            "paid nor shipped. cancel returns the order."),
    files={"pytest.ini": PYTEST_INI, "orders.py": ORD, "tests/test_orders.py": ORD_TEST},
    laws={"test_order_machine.py": '''import pytest
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from orders import Order, OrderError, pay, ship, cancel


class OrderLifecycle(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.order = Order(1)
        self.model = "open"
        self.was_paid = False

    @rule()
    def do_pay(self):
        if self.model == "open":
            pay(self.order)
            self.model, self.was_paid = "paid", True
        else:
            with pytest.raises(OrderError):
                pay(self.order)

    @rule()
    def do_ship(self):
        if self.model == "paid":
            ship(self.order)
            self.model = "shipped"
        else:
            with pytest.raises(OrderError):
                ship(self.order)

    @rule()
    def do_cancel(self):
        if self.model in ("open", "paid", "cancelled"):
            cancel(self.order)
            self.model = "cancelled"
        else:
            with pytest.raises(OrderError):
                cancel(self.order)

    @invariant()
    def matches_the_model(self):
        assert self.order.status == self.model
        assert self.order.refunded == (self.model == "cancelled" and self.was_paid)
        assert self.order.history.count("cancelled") <= 1


TestOrderLifecycle = OrderLifecycle.TestCase
'''},
    oracle={"check_orders.py": RAISES + '''
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
'''},
    candidates=[
        C("gold", OK, "gold", {"orders.py": ORD + CANCEL, "tests/test_cancel.py": ORD_NEW_TEST}),
        C("gold_notest", OK, "gold_notest", {"orders.py": ORD + CANCEL}),
        C("no_refund", BAD, "partial",
          {"orders.py": ORD + sub(CANCEL, '    if order.status == "paid":\n        order.refunded = True\n', ""),
           "tests/test_cancel.py": "from orders import Order, cancel\n\n\ndef test_cancel_open():\n    assert cancel(Order(1)).status == 'cancelled'\n"},
          mentions=("refund", "OrderLifecycle")),
        C("not_idempotent", BAD, "partial",
          {"orders.py": ORD + sub(CANCEL, '    if order.status == "cancelled":\n        return order\n', "").replace(
              '("open", "paid")', '("open", "paid", "cancelled")'),
           "tests/test_cancel.py": ORD_NEW_TEST}),
        C("cancels_shipped", BAD, "partial",
          {"orders.py": ORD + sub(CANCEL, '    if order.status not in ("open", "paid"):\n        raise OrderError(f"cannot cancel a {order.status} order")\n', ""),
           "tests/test_cancel.py": ORD_NEW_TEST}),
        C("wrong_exception", BAD, "wrong_test",
          {"orders.py": ORD + sub(CANCEL, "raise OrderError(f\"cannot cancel", "raise ValueError(f\"cannot cancel"),
           "tests/test_cancel.py": ORD_NEW_TEST + "\n\nimport pytest\nfrom orders import ship\n\n\ndef test_cannot_cancel_shipped():\n"
           "    with pytest.raises(ValueError):\n        cancel(ship(pay(Order(3))))\n"}),
        C("drops_pay_history", BAD, "regress_silent",
          {"orders.py": sub(ORD, '    order.status = "paid"\n    order.history.append("paid")\n', '    order.status = "paid"\n') + CANCEL,
           "tests/test_cancel.py": ORD_NEW_TEST}, note="'simplifies' pay and loses its history entry"),
    ],
)

# ---------------------------------------------------------------- quoted key=value parsing
KV = '''def parse(text: str) -> dict:
    """Parse 'a=1; b=two' into {'a': '1', 'b': 'two'}.

    Whitespace around keys and values is ignored; empty segments are skipped.
    """
    out = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, _, value = part.partition("=")
        out[key.strip()] = value.strip()
    return out
'''
KV_FIX = '''def _segments(text):
    """Split on ';' outside double quotes, unquoting and unescaping values."""
    seg, quoted, in_quotes, i = [], [], False, 0
    while i < len(text):
        ch = text[i]
        if in_quotes:
            if ch == "\\\\" and i + 1 < len(text) and text[i + 1] in "\\\\\\"":
                seg.append(("q", text[i + 1]))
                i += 2
                continue
            if ch == "\\"":
                in_quotes = False
            else:
                seg.append(("q", ch))
        elif ch == "\\"":
            in_quotes = True
        elif ch == ";":
            yield seg
            seg = []
        else:
            seg.append(("p", ch))
        i += 1
    if in_quotes:
        raise ValueError("unterminated quote")
    yield seg


def _strip(chars):
    while chars and chars[0][0] == "p" and chars[0][1].isspace():
        chars = chars[1:]
    while chars and chars[-1][0] == "p" and chars[-1][1].isspace():
        chars = chars[:-1]
    return "".join(c for _, c in chars)


def parse(text: str) -> dict:
    """Parse 'a=1; b="x;y"' into {'a': '1', 'b': 'x;y'}.

    Whitespace around keys and values is ignored; empty segments are skipped.
    Double-quoted values may contain ';' and '='; inside quotes, \\\\" is a
    quote and \\\\\\\\ a backslash. An unterminated quote raises ValueError.
    """
    out = {}
    for seg in _segments(text):
        if not _strip(seg):
            continue
        eq = next((i for i, (kind, ch) in enumerate(seg) if kind == "p" and ch == "="), len(seg))
        out[_strip(seg[:eq])] = _strip(seg[eq + 1:])
    return out
'''
KV_REGEX = '''import re

_PAIR = re.compile(r'\\s*([^=;]+?)\\s*=\\s*("[^"]*"|[^;]*?)\\s*(?:;|$)')


def parse(text: str) -> dict:
    """Parse 'a=1; b="x;y"' into {'a': '1', 'b': 'x;y'}."""
    out = {}
    for key, value in _PAIR.findall(text):
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        out[key] = value
    return out
'''
KV_TEST = '''from kvparse import parse


def test_pairs():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}


def test_empty_segments_are_skipped():
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
'''
KV_NEW_TEST = '''from kvparse import parse


def test_quoted_semicolon():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}
'''
kvparse = Task(
    id="t05_kv_quotes",
    title="Quoted values in a key=value parser",
    kind="feature",
    prompt=("parse('a=\"x;y\"; b=2') splits inside the quotes. Support double-quoted values that may "
            "contain ';' and '='. Inside quotes, \\\" is a literal quote and \\\\ a literal backslash; "
            "quotes are removed and whitespace inside them kept. An unterminated quote raises ValueError. "
            "Everything that parses today must parse the same."),
    files={"pytest.ini": PYTEST_INI, "kvparse.py": KV, "tests/test_kvparse.py": KV_TEST},
    laws={"test_kv_laws.py": '''from hypothesis import given, strategies as st
from kvparse import parse

keys = st.from_regex(r"[a-z][a-z0-9_]{0,6}", fullmatch=True)
values = st.text(alphabet=st.characters(codec="ascii", exclude_categories=("Cc",)), max_size=12)


def dump(d):
    def q(v):
        return '"' + v.replace("\\\\", "\\\\\\\\").replace('"', '\\\\"') + '"'
    return "; ".join(f"{k}={q(v)}" for k, v in d.items())


@given(st.dictionaries(keys, values, max_size=4))
def test_dump_then_parse_gives_back_the_dict(d):
    assert parse(dump(d)) == d


def test_quoted_semicolon():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}
'''},
    oracle={"check_kv.py": RAISES + '''
from kvparse import parse

def test_quoted_separators():
    assert parse('a="x;y"; b=2') == {"a": "x;y", "b": "2"}
    assert parse('a="k=v"') == {"a": "k=v"}

def test_whitespace_inside_quotes_kept():
    assert parse('a="  sp  "') == {"a": "  sp  "}

def test_escapes():
    assert parse(r'a="say \\"hi\\""') == {"a": 'say "hi"'}
    assert parse(r'a="back\\\\slash"') == {"a": "back\\\\slash"}

def test_unterminated_raises():
    assert raises(ValueError, parse, 'a="oops')

def test_old_inputs_unchanged():
    assert parse("a=1; b=two") == {"a": "1", "b": "two"}
    assert parse("a=1;; ;b=2;") == {"a": "1", "b": "2"}
    assert parse("a==b") == {"a": "=b"}
    assert parse("k") == {"k": ""}
    assert parse("") == {}
    assert parse("  spaced key  =  v  ") == {"spaced key": "v"}
'''},
    candidates=[
        C("gold", OK, "gold", {"kvparse.py": KV_FIX, "tests/test_kv_quotes.py": KV_NEW_TEST + '''

def test_escaped_quote():
    assert parse(r'a="say \\"hi\\""') == {"a": 'say "hi"'}
'''}),
        C("gold_notest", OK, "gold_notest", {"kvparse.py": KV_FIX}),
        C("regex_no_escapes", BAD, "partial", {"kvparse.py": KV_REGEX, "tests/test_kv_quotes.py": KV_NEW_TEST},
          note="regex rewrite: no escapes, no error for an unterminated quote, 'k' alone is dropped"),
        C("swallows_unterminated", BAD, "swallow",
          {"kvparse.py": sub(KV_FIX, "    out = {}\n    for seg in _segments(text):",
                             "    out = {}\n    try:\n        segments = list(_segments(text))\n    except ValueError:\n"
                             "        return out\n    for seg in segments:"),
           "tests/test_kv_quotes.py": KV_NEW_TEST}),
        C("keeps_empty_segments", BAD, "regress_covered",
          {"kvparse.py": sub(KV_FIX, "        if not _strip(seg):\n            continue\n", ""),
           "tests/test_kv_quotes.py": KV_NEW_TEST}, mentions=("test_empty_segments_are_skipped",)),
        C("rejects_bare_key", BAD, "regress_silent",
          {"kvparse.py": sub(KV_FIX, "        eq = next(", "        if not any(k == 'p' and c == '=' for k, c in seg):\n"
                             "            raise ValueError('missing =')\n        eq = next("),
           "tests/test_kv_quotes.py": KV_NEW_TEST}, note="tightens validation: 'k' alone now raises"),
        C("hardcoded_example", BAD, "hardcode",
          {"kvparse.py": sub(KV, '    out = {}\n', '    if text == \'a="x;y"; b=2\':\n        return {"a": "x;y", "b": "2"}\n    out = {}\n'),
           "tests/test_kv_quotes.py": KV_NEW_TEST}),
    ],
)

TASKS = [slugify, invoice, calendar, orders, kvparse]
