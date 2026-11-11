# t09_semver

## Q1
Build metadata: compare('1.0.0+build.1', '1.0.0')?
- A) 0 (build metadata is ignored)
- B) raise ValueError
- C) 1 (metadata makes it greater)

## Q2
Invalid input: compare('1.x.0', '1.0.0')?
- A) raise ValueError
- B) fall back to string comparison for that component

## Q3
A leading 'v': compare('v1.2.0', '1.2.0')?
- A) 0 (the 'v' is ignored)
- B) raise ValueError

## Q4
More than three numeric components: compare('1.2.3.4', '1.2.3')?
- A) 1 (extra components compared too, missing ones are 0)
- B) raise ValueError

## Q5
Leading zeros in a numeric component: compare('1.02.0', '1.2.0')?
- A) 0 (compared as numbers)
- B) raise ValueError
