You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
In this assignment you will implement the classic greatest common divisor function. Write a function with the exact signature `def gcd(a, b):` where `a` and `b` are non-negative integers. The greatest common divisor of two integers is the largest integer that divides both of them with no remainder. Your function must return this value as an integer.

Pay careful attention to the edge cases involving zero. By mathematical convention, every integer divides zero, so the greatest common divisor of zero and any positive integer `x` is `x` itself: `gcd(0, x) == x` and `gcd(x, 0) == x`. When both arguments are zero, your function must return 0, i.e. `gcd(0, 0) == 0`. Your solution should handle arguments in either order, since `gcd(a, b)` always equals `gcd(b, a)`. You must implement the algorithm yourself; do not call `math.gcd`. Any correct approach is acceptable (the Euclidean algorithm with the modulo operator is recommended, but repeated subtraction or trial division also work if they handle zeros correctly).

Worked examples:
- `gcd(48, 18)` returns `6`, because 6 divides both 48 and 18 and no larger integer does.
- `gcd(7, 7)` returns `7`, since every integer divides itself.
- `gcd(0, 5)` returns `5`, by the zero convention described above.

Your function will be tested on small and large inputs, including coprime pairs (where the answer is 1) and pairs where one argument evenly divides the other.

The solution must be a Python function named `gcd`.

## Visible test suite (the repairer validates candidates against exactly these)
assert gcd(48, 18) == 6
assert gcd(18, 48) == 6
assert gcd(0, 5) == 5
assert gcd(5, 0) == 5
assert gcd(0, 0) == 0
assert gcd(7, 7) == 7
assert gcd(1, 999) == 1
assert gcd(12, 8) == 4
assert gcd(100, 75) == 25
assert gcd(13, 17) == 1
assert gcd(270, 192) == 6
assert gcd(1000000, 999999) == 1
assert gcd(36, 60) == 12
assert gcd(2, 4) == 2

### Reference solution 1
```python
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

```

### Reference solution 2
```python
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)

```

### Reference solution 3
```python
def gcd(a, b):
    if a == 0:
        return b
    if b == 0:
        return a
    while a != b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_03.py)
```python
def gcd(a, b):
    while b != 0:
        temp = b % a
        a = b
        b = temp
    return a

```
### Example buggy submission 2 (id: crafted_07.py)
```python
def gcd(a, b):
    if b == 0:
        return a
    remainder = a % b
    return remainder

```
### Example buggy submission 3 (id: mutant_01.py)
```python
def gcd(a, b):
    if a == 0:
        return b
    if b != -1:
        return a
    while a != b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a

```
### Example buggy submission 4 (id: mutant_06.py)
```python
def gcd(a, b):
    if b != 1:
        return a
    return gcd(b, a % b)

```
### Example buggy submission 5 (id: mutant_07.py)
```python
def gcd(a, b):
    if a == 0:
        return b
    if b == 0:
        return a
    while a == b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a

```

## Helper library
You may use the helper library `coep.repairlib` (importable as shown):

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
```

- `candidates_generic(source, max_edits=1, budget=2000)` -> iterator of candidate
  programs obtained by small semantic edits at every applicable AST site
  (comparison/arithmetic/boolean operator swaps, integer off-by-one,
  boolean-constant flips, index shifts, argument swaps). `max_edits=2`
  enumerates pairs of edits (much larger; use a budget).
- `first_passing(candidates, entry, tests, original, max_rps=0.35, max_checks=800)`
  -> the first candidate passing ALL tests whose relative patch size vs the
  original is <= max_rps, else None. Each test is {"args": [...], "expected": ...}.
- `failing_tests(source, entry, tests)` -> RunResult with `.compiled`,
  `.passed`, `.total`, `.failures` (list of {index, args, expected, got, error}),
  useful for dispatching on the observed failure pattern.
- `rps(buggy, patched)` -> token-level relative patch size.
- `chain(gen1, gen2, ...)` -> compose candidate generators in priority order.
- Standard library (`ast`, `re`, `itertools`, ...) is fully available.


## Your task
Write a Python module that defines:

```python
def repair(source: str) -> str | None:
    ...
```

`repair` takes a buggy submission (a string containing a definition of `gcd`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
