You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
In this assignment you will implement a function that selects the largest values from a list.

Write a function with the signature `top_k(lst, k)`. The parameter `lst` is a list of integers (possibly empty, possibly containing duplicates and negative numbers) and `k` is a non-negative integer. The function must return a new list containing the `k` largest elements of `lst`, arranged in descending order (largest first).

Precise semantics you must follow:
- If `k` is 0, return the empty list `[]`.
- If `k` is greater than or equal to `len(lst)`, return all of the elements of `lst` sorted in descending order.
- Duplicate values count separately: each occurrence in `lst` is an element in its own right, so duplicates may appear in the result.
- The returned list must be sorted from largest to smallest, even when `lst` itself is unsorted.

Worked examples:
- `top_k([3, 1, 2], 2)` returns `[3, 2]`.
- `top_k([5, 5, 1], 2)` returns `[5, 5]` (the duplicate 5 is kept).
- `top_k([1, 2], 5)` returns `[2, 1]` because `k` exceeds the length of the list.

You may use any approach you like (sorting, repeated selection, a heap, and so on). Do not print anything; return the list.

The solution must be a Python function named `top_k`.

## Visible test suite (the repairer validates candidates against exactly these)
assert top_k([5, 5, 1], 2) == [5, 5]
assert top_k([3, 1, 2], 2) == [3, 2]
assert top_k([1, 2, 3, 4, 5], 3) == [5, 4, 3]
assert top_k([], 0) == []
assert top_k([], 3) == []
assert top_k([7], 1) == [7]
assert top_k([4, 2], 0) == []
assert top_k([1, 2], 5) == [2, 1]
assert top_k([-1, -5, -3], 2) == [-1, -3]
assert top_k([10, 10, 10], 2) == [10, 10]
assert top_k([0, -1, 1], 3) == [1, 0, -1]
assert top_k([2, 8, 6, 4, 9, 1], 4) == [9, 8, 6, 4]
assert top_k([5, 3, 5, 3, 5], 3) == [5, 5, 5]
assert top_k([100], 0) == []

### Reference solution 1
```python
def top_k(lst, k):
    return sorted(lst, reverse=True)[:k]

```

### Reference solution 2
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) < k:
        m = temp[0]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```

### Reference solution 3
```python
import heapq

def top_k(lst, k):
    return heapq.nlargest(k, lst)

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_04.py)
```python
def top_k(lst, k):
    return sorted(lst, reverse=True)[:k - 1]

```
### Example buggy submission 2 (id: crafted_10.py)
```python
import heapq

def top_k(lst, k):
    return heapq.nsmallest(k, lst)

```
### Example buggy submission 3 (id: mutant_02.py)
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[0]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```
### Example buggy submission 4 (id: mutant_03.py)
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[-1]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```
### Example buggy submission 5 (id: mutant_06.py)
```python
def top_k(lst, k):
    return sorted(lst, reverse=False)[:k]

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

`repair` takes a buggy submission (a string containing a definition of `top_k`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
