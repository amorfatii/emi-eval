# Trial E: a real agent, four ways

152 runs over 13 tasks; model(s): claude-sonnet-5-5.

| Setup | Runs | Wrong "done" accepted | Wrong, not caught | Ended correct | Correct, not accepted | Could not check | Sent to person | Sent back (mean) | Useful / wrong send-backs | Tokens (median) | Cost (mean) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 38 | 18/38 (47%) | 18/38 (47%) | 17/38 (45%) | 0 | 0 | 0 | 0.0 | 0 / 0 | 108,846 | $0.13 |
| script | 38 | 15/38 (39%) | 15/38 (39%) | 18/38 (47%) | 6 | 0 | 0 | 0.7 | 17 / 9 | 130,241 | $0.14 |
| emi | 38 | 7/38 (18%) | 13/38 (34%) | 18/38 (47%) | 7 | 12 | 2 | 0.1 | 3 / 0 | 111,726 | $0.12 |
| emi_rules | 38 | 9/38 (24%) | 15/38 (39%) | 16/38 (42%) | 6 | 12 | 5 | 0.1 | 3 / 0 | 104,031 | $0.11 |

## Comparisons

- **emi vs script** (37 paired runs): wrong "done" accepted 7 vs 15; wrong and not caught 13 vs 15; ended correct 18 vs 17; median tokens 106,725 vs 120,370 (-11%).

  Pass mark: wrong "done" at least a third less often than the script, ended correct no less often, at most 30% more tokens.

- **emi_rules vs emi** (37 paired runs): wrong "done" accepted 9 vs 7; wrong and not caught 15 vs 13; ended correct 16 vs 17; median tokens 103,768 vs 106,725 (-3%).

- **script vs none** (37 paired runs): wrong "done" accepted 15 vs 17; wrong and not caught 15 vs 17; ended correct 18 vs 17; median tokens 120,370 vs 107,578 (+12%).

## Runs to look at

- none
