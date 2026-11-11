# t02_invoice_rounding

## Q1
Where does rounding happen? For invoice_total([('0.005', 1), ('0.005', 1)]):
- A) only once, on the final total: Decimal('0.01')
- B) each line is rounded to cents first, then summed: Decimal('0.02')

## Q2
Is the subtotal rounded before tax is applied? For invoice_total([('0.045', 1)], tax_rate='0.1') (unrounded total 0.0495):
- A) no, round only the final amount: Decimal('0.05')
- B) yes, round the subtotal to 0.05 first, then apply tax and round: Decimal('0.06')

## Q3
What happens with float inputs, e.g. invoice_total([(0.1, 3)]) or tax_rate=0.2?
- A) accepted, converted via str() (so 0.1 means exactly 0.1): Decimal('0.30')
- B) raise TypeError
- C) accepted, converted with Decimal(float) directly (exact binary value)

## Q4
How do negative half cents round? invoice_total([('-1.005', 1)]):
- A) away from zero: Decimal('-1.01')
- B) toward positive infinity: Decimal('-1.00')

## Q5
Must the result always carry exactly two decimal places, e.g. str(invoice_total([(10, 2)])) == '20.00' and str(invoice_total([])) == '0.00'?
- A) yes, always quantized to two places
- B) no, only the numeric value matters (Decimal('20') is fine)
