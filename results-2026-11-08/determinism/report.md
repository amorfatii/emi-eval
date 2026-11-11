# EMI evaluation report


## Determinism and receipt honesty

- repeat: 10/10 pass
- warm_cold: 10/10 pass
- replay: 10/10 pass
- host: 110/110 pass
- noop_tree: 20/20 pass
- flaky: 2/2 pass
- memory: 3/3 pass
- every_input: 4/5 pass

Failures:

- [every_input] failing law over st.integers(): every_input=True, status=broken
