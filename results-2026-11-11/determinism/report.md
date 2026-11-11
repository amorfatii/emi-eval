# EMI evaluation report


## Determinism and receipt honesty

- repeat: 10/10 pass
- warm_cold: 10/10 pass
- replay: 10/10 pass
- host: 110/110 pass
- noop_tree: 20/20 pass
- flaky: 1/2 pass
- memory: 3/3 pass
- every_input: 5/5 pass

Failures:

- [flaky] flaky baseline test, unrelated clean change: stop, quarantined=0
