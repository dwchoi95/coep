You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Implement a function `search_insert(lst, x)` that determines where a value would be inserted into a sorted list.

The parameter `lst` is a list of integers sorted in ascending order; it may be empty and it may contain duplicate values. The parameter `x` is an integer. Your function must return the leftmost index at which `x` could be inserted so that `lst` would remain sorted in ascending order. Equivalently, the answer is the number of elements of `lst` that are strictly smaller than `x` (this matches the behaviour of `bisect.bisect_left` from the standard library).

Precise semantics:
- If `lst` is empty, return `0`.
- If `x` is smaller than or equal to every element, return `0`.
- If `x` is larger than every element, return `len(lst)`.
- If `x` already occurs in `lst`, return the index of its first occurrence, not any later one.

Worked examples:
- `search_insert([1, 3, 5, 7], 5)` returns `2` because 5 is already at index 2.
- `search_insert([1, 3, 5, 7], 4)` returns `2` because inserting 4 at index 2 keeps the list sorted.
- `search_insert([2, 2, 2, 2], 2)` returns `0`, the leftmost valid position.

Do not modify `lst`; just return the index. Any correct strategy (linear scan, binary search, counting) is acceptable.

The solution must be a Python function named `search_insert`.

## Visible test suite (the repairer validates candidates against exactly these)
assert search_insert([1, 3, 5, 7], 5) == 2
assert search_insert([1, 3, 5, 7], 4) == 2
assert search_insert([1, 3, 5, 7], 0) == 0
assert search_insert([1, 3, 5, 7], 8) == 4
assert search_insert([], 4) == 0
assert search_insert([2, 2, 2, 2], 2) == 0
assert search_insert([1, 2, 2, 3], 2) == 1
assert search_insert([10], 10) == 0
assert search_insert([10], 5) == 0
assert search_insert([10], 15) == 1
assert search_insert([1, 1, 2, 3, 3, 3, 4], 3) == 3
assert search_insert([-5, -2, 0, 3], -2) == 1
assert search_insert([1, 3, 5, 7], 1) == 0
assert search_insert([1, 3, 5, 7], 7) == 3

### Reference solution 1
```python
def search_insert(lst, x):
    for i, v in enumerate(lst):
        if v >= x:
            return i
    return len(lst)

```

### Reference solution 2
```python
def search_insert(lst, x):
    lo, hi = 0, len(lst)
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```

### Reference solution 3
```python
def search_insert(lst, x):
    return sum(1 for v in lst if v < x)

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_02.py)
```python
def search_insert(lst, x):
    lo, hi = 0, len(lst)
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```
### Example buggy submission 2 (id: crafted_10.py)
```python
def search_insert(lst, x):
    count = 0
    for v in lst:
        if v <= x:
            count += 1
    return count

```
### Example buggy submission 3 (id: mutant_05.py)
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid + 1] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```
### Example buggy submission 4 (id: mutant_10.py)
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 1
        if lst[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```
### Example buggy submission 5 (id: mutant_12.py)
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 1
        if lst[mid] < x:
            lo = mid - 1
        else:
            hi = mid
    return lo

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

`repair` takes a buggy submission (a string containing a definition of `search_insert`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
