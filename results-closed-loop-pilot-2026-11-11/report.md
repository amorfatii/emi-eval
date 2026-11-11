# Trial E: a real agent, four ways

12 runs over 3 tasks; model(s): claude-sonnet-5-5.

| Setup | Runs | Wrong "done" accepted | Ended correct | Sent back (mean) | Useful / wrong send-backs | Tokens (median) | Cost (mean) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| none | 3 | 0/3 (0%) | 3/3 (100%) | 0.0 | 0 / 0 | 34,390 | $0.04 |
| script | 3 | 0/3 (0%) | 3/3 (100%) | 0.0 | 0 / 0 | 34,585 | $0.04 |
| emi | 3 | 0/3 (0%) | 3/3 (100%) | 0.0 | 0 / 0 | 43,096 | $0.03 |
| emi_rules | 3 | 0/3 (0%) | 3/3 (100%) | 0.0 | 0 / 0 | 41,687 | $0.04 |

## Comparisons

- **emi vs script** (3 paired runs): wrong "done" 0 vs 0; ended correct 3 vs 3; median tokens 43,096 vs 34,585 (+25%).

  Pass mark: wrong "done" at least a third less often than the script, ended correct no less often, at most 30% more tokens.

- **emi_rules vs emi** (3 paired runs): wrong "done" 0 vs 0; ended correct 3 vs 3; median tokens 41,687 vs 43,096 (-3%).

- **script vs none** (3 paired runs): wrong "done" 0 vs 0; ended correct 3 vs 3; median tokens 34,585 vs 34,390 (+1%).

## Runs to look at

- none
