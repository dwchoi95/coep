You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
In this assignment you will practice extracting digits from an integer.

Write a function with the exact signature `sum_digits(n)`. The argument `n` is guaranteed to be a non-negative integer (`n >= 0`); it will never be negative, a float, or a string. Your function must return a single `int`: the sum of the decimal (base-10) digits of `n`.

Edge cases you must handle precisely: when `n` is `0`, the answer is `0`, because the number zero is written with the single digit 0. When `n` is any one-digit number, the answer is simply `n` itself. Your function must return its result, not print it, and it must not depend on any global state.

You may solve this arithmetically (repeatedly taking `n % 10` to read the last digit and `n // 10` to drop it) or by converting the number to a string and adding up `int(ch)` for every character. Both approaches are acceptable, as is a recursive solution.

Worked examples:
- `sum_digits(123)` returns `6`, because 1 + 2 + 3 = 6.
- `sum_digits(0)` returns `0`.
- `sum_digits(999)` returns `27`, because 9 + 9 + 9 = 27.

A common mistake is a loop that stops one step too early and forgets the last remaining digit, or one that accidentally counts the digits instead of adding them. Make sure every digit contributes its own value exactly once to the total.

The solution must be a Python function named `sum_digits`.

## Visible test suite (the repairer validates candidates against exactly these)
assert sum_digits(0) == 0
assert sum_digits(5) == 5
assert sum_digits(9) == 9
assert sum_digits(10) == 1
assert sum_digits(99) == 18
assert sum_digits(100) == 1
assert sum_digits(123) == 6
assert sum_digits(1000) == 1
assert sum_digits(4444) == 16
assert sum_digits(7) == 7
assert sum_digits(10001) == 2
assert sum_digits(55555) == 25
assert sum_digits(987654321) == 45
assert sum_digits(999999999) == 81

### Reference solution 1
```python
def sum_digits(n):
    total = 0
    while n > 0:
        total += n % 10
        n //= 10
    return total

```

### Reference solution 2
```python
def sum_digits(n):
    if n == 0:
        return 0
    return n % 10 + sum_digits(n // 10)

```

### Reference solution 3
```python
def sum_digits(n):
    return sum(int(ch) for ch in str(n))

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_06.py)
```python
def sum_digits(n):
    total = ""
    for d in str(n):
        total = total + d
    return total

```
### Example buggy submission 2 (id: crafted_09.py)
```python
def sum_digits(n):
    total = 0
    while n > 9:
        total += n % 10
        n = n // 10
    return total

```
### Example buggy submission 3 (id: mutant_03.py)
```python
def sum_digits(n):
    total = 0
    while n > 0:
        total -= n % 9
        n //= 10
    return total

```
### Example buggy submission 4 (id: mutant_12.py)
```python
def sum_digits(n):
    total = 0
    while n > 0:
        total -= n % 10
        n //= 10
    return total

```
### Example buggy submission 5 (id: mutant_13.py)
```python
def sum_digits(n):
    total = 0
    while n > 0:
        total -= n % 10
        n //= 9
    return total

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

`repair` takes a buggy submission (a string containing a definition of `sum_digits`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
