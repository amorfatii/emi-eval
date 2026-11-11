# Trial C: eight real projects

86 checks (full_suite 8, spec_laws 39, visible 39).

## Environments

| Task | Usable | Why not |
| --- | --- | --- |
| Melevir__cognitive_complexity-15 | yes |  |
| andialbrecht__sqlparse-231 | yes |  |
| benmoran56__esper-81 | yes |  |
| johnsyweb__python_sparse_list-17 | yes |  |
| konradhalas__dacite-216 | yes |  |
| package-url__packageurl-python-29 | yes |  |
| serge-sans-paille__gast-50 | yes |  |
| tehmaze__ansi-34 | yes |  |

## 1. Works on real projects (pass: a real answer on at least 6 of 8)

- Real answer on the developers' fix (visible): **7 of 8** projects (8 usable environments).
- Real answer over every check (both conditions): 68/78 (87%).
- Verdict: **pass**.

## 2. Fast enough (pass: a check at most 3x the project's own run, and under 5 minutes)

| Task | Condition | Own run (s) | EMI warm-up (s) | EMI check, fix (s) | Ratio | Pass |
| --- | --- | --- | --- | --- | --- | --- |
| Melevir__cognitive_complexity-15 | full_suite | 0.78 | 2.8 | 4.4 | 5.6x | no |
| Melevir__cognitive_complexity-15 | spec_laws | 0.84 | 2.7 | 7.2 | 8.6x | no |
| Melevir__cognitive_complexity-15 | visible | 0.81 | 2.8 | 4.5 | 5.6x | no |
| andialbrecht__sqlparse-231 | full_suite | 1.92 | 3.9 | 4.3 | 2.2x | yes |
| andialbrecht__sqlparse-231 | spec_laws | 0.94 | 3.2 | 4.2 | 4.5x | no |
| andialbrecht__sqlparse-231 | visible | 0.9 | 2.9 | 4.0 | 4.4x | no |
| benmoran56__esper-81 | full_suite | 0.88 | 2.8 | 4.4 | 5.0x | no |
| benmoran56__esper-81 | spec_laws | 0.99 | 2.8 | 8.3 | 8.4x | no |
| benmoran56__esper-81 | visible | 0.81 | 2.9 | 4.5 | 5.6x | no |
| johnsyweb__python_sparse_list-17 | full_suite | 0.76 | 2.6 | 3.4 | 4.5x | no |
| johnsyweb__python_sparse_list-17 | spec_laws | 0.84 | 2.6 | 7.1 | 8.5x | no |
| johnsyweb__python_sparse_list-17 | visible | 0.81 | 2.5 | 3.4 | 4.2x | no |
| konradhalas__dacite-216 | full_suite | 6.2 | 14.5 | 10.0 | 1.6x | yes |
| konradhalas__dacite-216 | spec_laws | 0.94 | 3.4 | 8.3 | 8.8x | no |
| konradhalas__dacite-216 | visible | 0.96 | 3.2 | 4.5 | 4.7x | no |
| package-url__packageurl-python-29 | full_suite | 0.42 | 1.7 | 1.9 | 4.5x | no |
| package-url__packageurl-python-29 | spec_laws | 0.35 | 1.5 | 3.8 | 10.9x | no |
| package-url__packageurl-python-29 | visible | 0.36 | 1.4 | 1.9 | 5.3x | no |
| serge-sans-paille__gast-50 | full_suite | 1.01 | 3.4 | 5.6 | 5.5x | no |
| serge-sans-paille__gast-50 | spec_laws | 0.86 | 3.3 | 5.1 | 5.9x | no |
| serge-sans-paille__gast-50 | visible | 0.86 | 3.0 | 4.7 | 5.5x | no |
| tehmaze__ansi-34 | full_suite | 0.83 | 3.3 | 3.7 | 4.5x | no |
| tehmaze__ansi-34 | spec_laws | 0.87 | 3.3 | 7.8 | 9.0x | no |
| tehmaze__ansi-34 | visible | 0.9 | 2.8 | 3.5 | 3.9x | no |

- Visible condition: 0 of 8 projects within the mark. The ratio is the check alone; the warm-up is paid once per baseline.

## 3. Leaves honest work alone (pass: at least 90% of correct changes finish without a person)

Tasks whose correct fix fails the project's existing tests: Melevir__cognitive_complexity-15, benmoran56__esper-81, serge-sans-paille__gast-50. In those, a right fix must also change old tests, which EMI sends to a person; the agent patches here change no tests, so they fail the old ones. Rows marked *other tasks* leave them out.

| Condition | Tasks | Correct changes | EMI finishes | Script finishes |
| --- | --- | --- | --- | --- |
| visible | *other tasks* | 15 | 12/15 (80%) | 15/15 (100%) |
| spec_laws | *other tasks* | 15 | 12/15 (80%) | 15/15 (100%) |
| visible | all | 23 | 12/23 (52%) | 15/23 (65%) |
| spec_laws | all | 23 | 12/23 (52%) | 15/23 (65%) |

- Verdict (visible, EMI): **fail**.

## 4. Catches wrong fixes (reported; no pass mark, the sample is small)

| Condition | Wrong changes | EMI catches | EMI could not check | Script catches |
| --- | --- | --- | --- | --- |
| visible | 15 | 9/15 (60%) | 2 | 9/15 (60%) |
| spec_laws | 15 | 13/15 (87%) | 2 | 15/15 (100%) |

## Re-grading against the dataset's labels

- Agent patches whose re-graded result matches the dataset: 30/31 (97%).
  - Melevir__cognitive_complexity-15 agent0 (swe-agent-llama-70b): dataset resolved, here not applied

## Same input, same decision

- Developers' fix checked twice from fresh state: 16/16 (100%) identical.

## Where EMI and the script disagree

- andialbrecht__sqlparse-231 / spec_laws / agent0 (correct): EMI incomplete, script accept (tests exit 0, laws exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / spec_laws / agent1 (correct): EMI incomplete, script accept (tests exit 0, laws exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / spec_laws / gold (correct): EMI incomplete, script accept (tests exit 0, laws exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / visible / agent0 (correct): EMI incomplete, script accept (tests exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / visible / agent1 (correct): EMI incomplete, script accept (tests exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / visible / agent2 (wrong): EMI incomplete, script accept (tests exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / visible / agent3 (wrong): EMI incomplete, script accept (tests exit 0). EMI said: [""]
- andialbrecht__sqlparse-231 / visible / gold (correct): EMI incomplete, script accept (tests exit 0). EMI said: [""]

## Could not check

- andialbrecht__sqlparse-231 / visible / gold: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]
- andialbrecht__sqlparse-231 / visible / agent0: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]
- andialbrecht__sqlparse-231 / visible / agent1: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]
- andialbrecht__sqlparse-231 / visible / agent2: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]
- andialbrecht__sqlparse-231 / visible / agent3: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]
- andialbrecht__sqlparse-231 / spec_laws / gold: incomplete: [""]
- andialbrecht__sqlparse-231 / spec_laws / agent0: incomplete: [""]
- andialbrecht__sqlparse-231 / spec_laws / agent1: incomplete: [""]
- andialbrecht__sqlparse-231 / spec_laws / agent2: incomplete: [""]
- andialbrecht__sqlparse-231 / spec_laws / agent3: incomplete: [""]
- andialbrecht__sqlparse-231 / full_suite / gold: incomplete: ["No laws: what the change should do is shown only by the proposer's own tests. Laws the person writes in .emi/laws hold every change to them."]

