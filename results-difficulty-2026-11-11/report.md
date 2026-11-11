# Trial E: a real agent, four ways

14 runs over 14 tasks; model(s): claude-sonnet-5-5.

| Setup | Runs | Wrong "done" accepted | Ended correct | Sent back (mean) | Useful / wrong send-backs | Tokens (median) | Cost (mean) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| none | 14 | 5/14 (36%) | 8/14 (57%) | 0.0 | 0 / 0 | 117,961 | $0.15 |

## Comparisons

- emi vs script: no paired runs.

  Pass mark: wrong "done" at least a third less often than the script, ended correct no less often, at most 30% more tokens.

- emi_rules vs emi: no paired runs.

- script vs none: no paired runs.

## Runs to look at

- none
