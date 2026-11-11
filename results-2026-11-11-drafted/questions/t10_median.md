# t10_median

## Q1
Decimal inputs: median([Decimal('1'), Decimal('2')])?
- A) Decimal('1.5') (type preserved)
- B) a float 1.5 is fine
- C) either is fine as long as it equals 1.5

## Q2
Non-numeric values of even length: median(['a', 'b'])?
- A) raise TypeError
- B) return the lower middle value 'a'
- C) return the upper middle value 'b' (as today)

## Q3
Large integers: median([10**20, 10**20 + 2])?
- A) exactly 10**20 + 1 (no float rounding)
- B) a float approximation is fine
