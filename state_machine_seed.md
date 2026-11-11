# Probe: one pinned seed vs a state-machine bug (t04_order_cancel / cancels_shipped)

EMI (derandomized Hypothesis) reports the law `TestOrderLifecycle` as `now_holds`
after 100 walks in which every rule ran (do_cancel 65, do_pay 61, do_ship 51),
yet no walk did pay -> ship -> cancel.

Same tree, plain pytest, Hypothesis settings varied:

| setting                  | result          |
|--------------------------|-----------------|
| derandomize=True         | missed          |
| --hypothesis-seed=0..39  | 34/40 found it  |

So a single pinned seed misses this bug with probability ~15%, and once missed
it is missed on every later check (no counterexample is ever remembered).
