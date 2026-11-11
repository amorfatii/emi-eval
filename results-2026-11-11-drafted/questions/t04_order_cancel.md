# t04_order_cancel

## Q1
What is the history after cancel(Order(1)) on an open order?
- A) ['cancelled']
- B) history is unspecified apart from exactly one new entry

## Q2
What is the history after cancel(pay(Order(1))) on a paid order?
- A) ['paid', 'cancelled']
- B) ['paid', 'cancelled', 'refunded']
- C) ['paid', 'refunded']

## Q3
When cancel raises OrderError on a shipped order, must the order be left exactly as it was (status 'shipped', refunded False, history ['paid', 'shipped'])?
- A) yes, completely unchanged
- B) doesn't need to be checked beyond the raise
