# t07_backoff_cap

## Q1
What should backoff_delays(3, max_delay=0) do?
- A) return [0, 0, 0]
- B) raise ValueError

## Q2
What should backoff_delays(3, max_delay=-1) do?
- A) raise ValueError
- B) return [-1, -1, -1]
