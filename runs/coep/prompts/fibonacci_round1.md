You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
The Fibonacci sequence is defined by two starting values and a simple recurrence: each later term is the sum of the two terms before it.

Write a function with the exact signature `fibonacci(n)` that returns the nth Fibonacci number as an `int`. Use zero-based indexing with these exact base cases: `fibonacci(0)` returns `0` and `fibonacci(1)` returns `1`. For every `n >= 2`, the value is `fibonacci(n - 1) + fibonacci(n - 2)`, so the sequence begins 0, 1, 1, 2, 3, 5, 8, 13, 21, ...

The argument `n` is guaranteed to be an integer with `0 <= n <= 24`, so any correct approach is fast enough: a simple loop that keeps the last two values, a list built bottom-up, plain recursion, or recursion with memoization. Do not print anything and do not read input; just return the value.

Be very careful with the indexing convention. Some textbooks start the sequence at 1, 1; that is NOT the convention here. Off-by-one errors (returning the (n+1)th term, or running the update loop one time too many or too few) are the most common way to fail this assignment, so check the small cases by hand before you submit.

Worked examples:
- `fibonacci(0)` returns `0`.
- `fibonacci(6)` returns `8`, since the sequence runs 0, 1, 1, 2, 3, 5, 8.
- `fibonacci(10)` returns `55`.

If you use a loop with two variables, make sure both are updated simultaneously (for example with tuple assignment), not one after the other.

The solution must be a Python function named `fibonacci`.

## Visible test suite (the repairer validates candidates against exactly these)
assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(2) == 1
assert fibonacci(3) == 2
assert fibonacci(4) == 3
assert fibonacci(5) == 5
assert fibonacci(6) == 8
assert fibonacci(7) == 13
assert fibonacci(8) == 21
assert fibonacci(10) == 55
assert fibonacci(12) == 144
assert fibonacci(15) == 610
assert fibonacci(20) == 6765
assert fibonacci(24) == 46368

### Reference solution 1
```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

```

### Reference solution 2
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

```

### Reference solution 3
```python
def fibonacci(n):
    seq = [0, 1]
    while len(seq) <= n:
        seq.append(seq[-1] + seq[-2])
    return seq[n]

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_02.py)
```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b

```
### Example buggy submission 2 (id: crafted_09.py)
```python
def fibonacci(n):
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[-1]

```
### Example buggy submission 3 (id: mutant_02.py)
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 0) + fibonacci(n - 2)

```
### Example buggy submission 4 (id: mutant_06.py)
```python
def fibonacci(n):
    seq = [-1, 1]
    while len(seq) <= n:
        seq.append(seq[-1 + 1] + seq[-2])
    return seq[n]

```
### Example buggy submission 5 (id: mutant_14.py)
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 3)

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

`repair` takes a buggy submission (a string containing a definition of `fibonacci`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
