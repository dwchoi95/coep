You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Write a function with the exact signature `def grade_stats(scores):` that computes summary statistics for a list of exam scores. The argument `scores` is guaranteed to be a non-empty list of numbers; each element may be an `int` or a `float`, and scores may be negative (for example, after a penalty adjustment). The function must return a list of exactly three values, in this order: `[minimum, maximum, mean]`.

Precise requirements: the minimum and maximum are the smallest and largest values in the list, returned with their original numeric type (do not convert an integer minimum to a float). The mean is the arithmetic average, `sum of scores divided by number of scores`, computed with true division and then rounded to exactly 2 decimal places using Python's built-in `round(value, 2)`. Do not truncate, do not use integer division, and do not round to a different precision. A single-element list is valid input: its minimum, maximum, and mean are all that one score. Do not assume the list is sorted, and do not modify the input list.

Worked examples:
- `grade_stats([70, 80, 90])` returns `[70, 90, 80.0]`.
- `grade_stats([1, 2, 4])` returns `[1, 4, 2.33]`, since 7 / 3 = 2.333... rounds to 2.33.
- `grade_stats([100])` returns `[100, 100, 100.0]`.

Your function will be tested with unsorted lists, all-negative lists, single-element lists, and means that require rounding.

The solution must be a Python function named `grade_stats`.

## Visible test suite (the repairer validates candidates against exactly these)
assert grade_stats([70, 80, 90]) == [70, 90, 80.0]
assert grade_stats([100]) == [100, 100, 100.0]
assert grade_stats([50.5, 60.5]) == [50.5, 60.5, 55.5]
assert grade_stats([-10, 0, 10]) == [-10, 10, 0.0]
assert grade_stats([1, 2]) == [1, 2, 1.5]
assert grade_stats([1, 2, 3]) == [1, 3, 2.0]
assert grade_stats([0, 0, 0]) == [0, 0, 0.0]
assert grade_stats([59.9, 60.1, 60.0]) == [59.9, 60.1, 60.0]
assert grade_stats([85, 92, 78, 95, 88]) == [78, 95, 87.6]
assert grade_stats([1, 2, 4]) == [1, 4, 2.33]
assert grade_stats([-5, -15, -10]) == [-15, -5, -10.0]
assert grade_stats([2.675, 2.675]) == [2.675, 2.675, 2.67]
assert grade_stats([0.1, 0.2, 0.3]) == [0.1, 0.3, 0.2]
assert grade_stats([10, 20, 30, 40]) == [10, 40, 25.0]

### Reference solution 1
```python
def grade_stats(scores):
    return [min(scores), max(scores), round(sum(scores) / len(scores), 2)]

```

### Reference solution 2
```python
def grade_stats(scores):
    lo = scores[0]
    hi = scores[0]
    total = 0
    for s in scores:
        if s < lo:
            lo = s
        if s > hi:
            hi = s
        total += s
    return [lo, hi, round(total / len(scores), 2)]

```

### Reference solution 3
```python
def grade_stats(scores):
    ordered = sorted(scores)
    total = 0.0
    count = 0
    for s in ordered:
        total = total + s
        count = count + 1
    return [ordered[0], ordered[-1], round(total / count, 2)]

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_02.py)
```python
def grade_stats(scores):
    lowest = min(scores)
    highest = max(scores)
    mean = sum(scores) / len(scores)
    return [lowest, highest, mean]

```
### Example buggy submission 2 (id: crafted_08.py)
```python
def grade_stats(scores):
    ordered = sorted(scores)
    mid = ordered[len(ordered) // 2]
    return [ordered[0], ordered[-1], round(mid, 2)]

```
### Example buggy submission 3 (id: mutant_03.py)
```python
def grade_stats(scores):
    ordered = sorted(scores)
    total = 0.0
    count = 0
    for s in ordered:
        total = total - s
        count = count + 1
    return [ordered[0], ordered[-1], round(total / count, 2)]

```
### Example buggy submission 4 (id: mutant_09.py)
```python
def grade_stats(scores):
    return [min(scores), max(scores), round(1, sum(scores) / len(scores))]

```
### Example buggy submission 5 (id: mutant_10.py)
```python
def grade_stats(scores):
    ordered = sorted(scores)
    total = 0.0
    count = 0
    for s in ordered:
        total = total + s
        count = count + 1
    return [ordered[0], ordered[-1 + 1], round(total / count, 2)]

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

`repair` takes a buggy submission (a string containing a definition of `grade_stats`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
