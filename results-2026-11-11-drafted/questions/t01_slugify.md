# t01_slugify

## Q1
What should slugify('!!! ???') return, where nothing alphanumeric remains?
- A) the empty string ''
- B) raise ValueError

## Q2
Characters that ASCII folding drops entirely (for example slugify('a日b'), a CJK character between two letters): what should the result be?
- A) 'ab' (the dropped character leaves nothing behind, as today)
- B) 'a-b' (the dropped character counts as a separator)

## Q3
What should slugify('Hello World', sep='') return?
- A) 'helloworld' (empty separator is allowed)
- B) raise ValueError
