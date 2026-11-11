# t05_kv_quotes

## Q1
Are keys allowed to be quoted too? parse('"a;b"=1'):
- A) yes: {'a;b': '1'}
- B) no, quotes only apply to values (the key is split at ';' as today)
- C) raise ValueError

## Q2
What about text after the closing quote, parse('a="x"y; b=2')?
- A) raise ValueError
- B) concatenate: {'a': 'xy', 'b': '2'}
- C) ignore it: {'a': 'x', 'b': '2'}

## Q3
Other backslash escapes inside quotes, e.g. parse(r'a="x\ny"') (backslash followed by n):
- A) kept literally: {'a': 'x\\ny'} (backslash and n both kept)
- B) backslash dropped: {'a': 'xny'}
- C) raise ValueError

## Q4
A quote that does not start the value, parse('a=x"y;z"'):
- A) not special, parsed as today: {'a': 'x"y', 'z"': ''}
- B) it opens a quoted section: {'a': 'xy;z'}
- C) raise ValueError
